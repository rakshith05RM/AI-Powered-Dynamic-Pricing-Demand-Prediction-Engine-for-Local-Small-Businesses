import json
import joblib
import numpy as np
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from businesses.models import Business
from products.models import Product
from sales.models import SalesRecord
from forecasting.models import ModelMetadata
from forecasting.services.features import build_training_frame, FEATURE_COLUMNS

MIN_RECORDS_REQUIRED = 30


class Command(BaseCommand):
    help = "Train (or retrain) the RandomForest demand-prediction model for one or all businesses."

    def add_arguments(self, parser):
        parser.add_argument("--business-id", type=int, default=None,
                             help="Train only this business. Default: train for every business with data.")

    def handle(self, *args, **options):
        business_id = options.get("business_id")
        businesses = Business.objects.filter(id=business_id) if business_id else Business.objects.all()

        if not businesses.exists():
            raise CommandError("No matching business found.")

        for business in businesses:
            self.train_for_business(business)

    def train_for_business(self, business):
        self.stdout.write(f"Training demand model for: {business.business_name}")

        sales_qs = SalesRecord.objects.filter(business=business)
        record_count = sales_qs.count()

        if record_count < MIN_RECORDS_REQUIRED:
            self.stdout.write(self.style.WARNING(
                f"  Skipped: only {record_count} sales records found "
                f"(minimum {MIN_RECORDS_REQUIRED} required to train a meaningful model)."
            ))
            return

        products = Product.objects.filter(business=business)
        category_map = {p.id: p.category for p in products}
        stock_map = {p.id: p.stock_quantity for p in products}

        df, cat_to_code = build_training_frame(sales_qs, category_map, stock_map)
        if df.empty or len(df) < MIN_RECORDS_REQUIRED:
            self.stdout.write(self.style.WARNING("  Skipped: not enough usable rows after feature engineering."))
            return

        X = df[FEATURE_COLUMNS]
        y = df["quantity_sold"].astype(float)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        mae = float(mean_absolute_error(y_test, preds))
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        r2 = float(r2_score(y_test, preds))

        model_version = datetime.now().strftime("v%Y%m%d%H%M%S")
        model_path = settings.ML_MODEL_DIR / f"business_{business.id}_{model_version}.joblib"
        joblib.dump({"model": model, "cat_to_code": cat_to_code, "feature_columns": FEATURE_COLUMNS}, model_path)

        # keep a stable "latest" pointer file so prediction code doesn't need to guess filenames
        latest_path = settings.ML_MODEL_DIR / f"business_{business.id}_latest.joblib"
        joblib.dump({"model": model, "cat_to_code": cat_to_code, "feature_columns": FEATURE_COLUMNS}, latest_path)

        ModelMetadata.objects.update_or_create(
            business=business,
            defaults=dict(
                model_version=model_version,
                algorithm="RandomForestRegressor",
                training_records=record_count,
                mae=round(mae, 3),
                rmse=round(rmse, 3),
                r2_score=round(r2, 4),
                features_used=FEATURE_COLUMNS,
            ),
        )

        self.stdout.write(self.style.SUCCESS(
            f"  Trained on {record_count} records | MAE={mae:.2f} RMSE={rmse:.2f} R2={r2:.3f} "
            f"| saved as {model_version}"
        ))

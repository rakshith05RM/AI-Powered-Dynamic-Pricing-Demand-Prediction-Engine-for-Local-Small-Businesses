"""
forecasting/services/demand_predictor.py

Responsibilities:
- Load the trained model for a business (cached in-process so we don't hit disk every call).
- Prepare features for a specific product + target date.
- Generate a prediction.
- Estimate a confidence score.
- Handle missing model / missing data gracefully.
"""
import joblib
import pandas as pd
from django.conf import settings

from sales.models import SalesRecord
from forecasting.models import ModelMetadata
from .features import build_prediction_row

_MODEL_CACHE = {}


class PredictionUnavailable(Exception):
    """Raised when there is no trained model or not enough data to predict."""


def _load_model(business_id):
    cache_key = business_id
    path = settings.ML_MODEL_DIR / f"business_{business_id}_latest.joblib"
    if not path.exists():
        raise PredictionUnavailable(
            "No trained model found for this business yet. Import sales data and run model training first."
        )

    mtime = path.stat().st_mtime
    cached = _MODEL_CACHE.get(cache_key)
    if cached and cached["mtime"] == mtime:
        return cached["bundle"]

    bundle = joblib.load(path)
    _MODEL_CACHE[cache_key] = {"mtime": mtime, "bundle": bundle}
    return bundle


class DemandPredictor:
    def __init__(self, business):
        self.business = business
        self.bundle = _load_model(business.id)
        self.model = self.bundle["model"]
        self.cat_to_code = self.bundle["cat_to_code"]

        try:
            self.metadata = ModelMetadata.objects.get(business=business)
        except ModelMetadata.DoesNotExist:
            self.metadata = None

    def _recent_sales(self, product, before_date=None):
        qs = SalesRecord.objects.filter(product=product).order_by("sale_date")
        if before_date is not None:
            qs = qs.filter(sale_date__lt=before_date)
        rows = list(qs.values("sale_date", "quantity_sold", "discount_percentage"))
        if not rows:
            return pd.DataFrame(columns=["sale_date", "quantity_sold", "discount_percentage"])
        return pd.DataFrame(rows)

    def predict(self, product, target_date, price_override=None):
        """Returns (predicted_quantity: float, confidence_score: float 0-100).

        price_override lets callers (e.g. the price simulator) ask "what would
        demand look like at this price instead of the product's current price?"
        by feeding a different selling_price into the same trained model.
        """
        recent_df = self._recent_sales(product, before_date=target_date)
        feature_row = build_prediction_row(product, target_date, self.cat_to_code, recent_df)
        if price_override is not None:
            feature_row["selling_price"] = float(price_override)

        prediction = float(self.model.predict(feature_row)[0])
        prediction = max(prediction, 0.0)

        confidence = self._estimate_confidence(recent_df, prediction)
        return round(prediction, 1), round(confidence, 1)

    def _estimate_confidence(self, recent_df, prediction):
        """
        Heuristic confidence estimate (0-100), not a formal prediction interval.
        Combines the model's overall R^2 (how well it explains variance in general)
        with how much recent sales for this specific product have fluctuated
        relative to the prediction (more volatile history -> lower confidence).
        """
        base = 60.0
        if self.metadata is not None:
            # R2 can be negative for a poor model; clamp into a usable 0-1 range.
            r2_component = max(0.0, min(self.metadata.r2_score, 1.0))
            base = 50 + r2_component * 40  # 50-90 range from model quality

        if len(recent_df) >= 3:
            recent = recent_df["quantity_sold"].tail(14)
            mean = recent.mean() if recent.mean() else 1.0
            volatility = (recent.std(ddof=0) or 0) / max(mean, 1.0)
            volatility_penalty = min(volatility * 25, 20)
        else:
            volatility_penalty = 10  # not much history -> reduce confidence a bit

        confidence = base - volatility_penalty
        return max(35.0, min(confidence, 97.0))

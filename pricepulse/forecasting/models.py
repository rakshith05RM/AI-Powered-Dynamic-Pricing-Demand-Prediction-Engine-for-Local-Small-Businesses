from django.db import models
from products.models import Product


class DemandPrediction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="demand_predictions")
    prediction_date = models.DateField()
    predicted_quantity = models.FloatField()
    confidence_score = models.FloatField(help_text="0-100 heuristic confidence estimate")
    model_version = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["prediction_date"]
        indexes = [models.Index(fields=["product", "prediction_date"])]
        unique_together = ("product", "prediction_date", "model_version")

    def __str__(self):
        return f"{self.product.product_name} -> {self.prediction_date}: {self.predicted_quantity:.1f}"


class ModelMetadata(models.Model):
    """Stores metrics/info about the last trained ML model for a business."""
    business = models.OneToOneField("businesses.Business", on_delete=models.CASCADE, related_name="model_metadata")
    model_version = models.CharField(max_length=40)
    algorithm = models.CharField(max_length=60, default="RandomForestRegressor")
    training_records = models.PositiveIntegerField()
    mae = models.FloatField()
    rmse = models.FloatField()
    r2_score = models.FloatField()
    features_used = models.JSONField(default=list)
    trained_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Model {self.model_version} for {self.business}"

from django.contrib import admin
from .models import DemandPrediction, ModelMetadata

@admin.register(DemandPrediction)
class DemandPredictionAdmin(admin.ModelAdmin):
    list_display = ("product", "prediction_date", "predicted_quantity", "confidence_score")

@admin.register(ModelMetadata)
class ModelMetadataAdmin(admin.ModelAdmin):
    list_display = ("business", "model_version", "training_records", "mae", "rmse", "r2_score", "trained_at")

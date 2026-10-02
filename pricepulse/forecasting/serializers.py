from rest_framework import serializers
from .models import DemandPrediction, ModelMetadata


class DemandPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandPrediction
        fields = ["id", "product", "prediction_date", "predicted_quantity", "confidence_score", "model_version"]


class ModelMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelMetadata
        fields = ["model_version", "algorithm", "training_records", "mae", "rmse", "r2_score", "features_used", "trained_at"]

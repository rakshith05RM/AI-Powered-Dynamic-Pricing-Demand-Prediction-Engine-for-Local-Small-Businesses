from rest_framework import serializers
from .models import PriceRecommendation


class PriceRecommendationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True)

    class Meta:
        model = PriceRecommendation
        fields = [
            "id", "product", "product_name", "current_price", "recommended_price",
            "predicted_demand", "expected_revenue", "price_change_percentage",
            "reason", "is_applied", "created_at",
        ]
        read_only_fields = fields

from rest_framework import serializers
from .models import BusinessAlert


class BusinessAlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True, default=None)

    class Meta:
        model = BusinessAlert
        fields = ["id", "product", "product_name", "alert_type", "title", "message", "severity", "is_read", "created_at"]
        read_only_fields = fields

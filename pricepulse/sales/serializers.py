from rest_framework import serializers
from .models import SalesRecord
from products.models import Product


class SalesRecordSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True)

    class Meta:
        model = SalesRecord
        fields = [
            "id", "product", "product_name", "sale_date", "quantity_sold",
            "selling_price", "discount_percentage", "revenue", "created_at",
        ]
        read_only_fields = ["id", "revenue", "created_at"]

    def validate_quantity_sold(self, value):
        if value < 0:
            raise serializers.ValidationError("quantity_sold cannot be negative.")
        return value

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError("selling_price cannot be negative.")
        return value

    def validate_discount_percentage(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError("discount_percentage must be between 0 and 100.")
        return value

    def validate_product(self, product):
        request = self.context.get("request")
        if request and product.business_id != request.user.business.id:
            raise serializers.ValidationError("Invalid product for this business.")
        return product

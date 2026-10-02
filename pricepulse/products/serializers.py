from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "product_name", "category", "sku", "description",
            "cost_price", "current_price", "minimum_price", "maximum_price",
            "stock_quantity", "reorder_level", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        minimum = data.get("minimum_price", getattr(self.instance, "minimum_price", None))
        maximum = data.get("maximum_price", getattr(self.instance, "maximum_price", None))
        current = data.get("current_price", getattr(self.instance, "current_price", None))
        cost = data.get("cost_price", getattr(self.instance, "cost_price", None))

        if minimum is not None and maximum is not None and minimum > maximum:
            raise serializers.ValidationError("minimum_price cannot be greater than maximum_price.")
        if current is not None and minimum is not None and maximum is not None:
            if not (minimum <= current <= maximum):
                raise serializers.ValidationError("current_price must be between minimum_price and maximum_price.")
        if cost is not None and cost < 0:
            raise serializers.ValidationError("cost_price cannot be negative.")
        return data

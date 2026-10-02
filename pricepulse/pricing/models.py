from django.db import models
from products.models import Product


class PriceRecommendation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_recommendations")
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    recommended_price = models.DecimalField(max_digits=10, decimal_places=2)
    predicted_demand = models.FloatField()
    expected_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    price_change_percentage = models.FloatField()
    reason = models.TextField()
    is_applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.product_name}: {self.current_price} -> {self.recommended_price}"

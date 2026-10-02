from django.db import models
from businesses.models import Business


class Product(models.Model):
    CATEGORY_CHOICES = [
        ("bakery", "Bakery"),
        ("beverages", "Beverages"),
        ("dairy", "Dairy"),
        ("grocery", "Grocery"),
        ("snacks", "Snacks"),
        ("clothing", "Clothing"),
        ("electronics", "Electronics"),
        ("pharmacy", "Pharmacy"),
        ("other", "Other"),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="products")
    product_name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="other")
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_price = models.DecimalField(max_digits=10, decimal_places=2)
    maximum_price = models.DecimalField(max_digits=10, decimal_places=2)

    stock_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_name"]
        indexes = [
            models.Index(fields=["business", "category"]),
        ]

    def __str__(self):
        return f"{self.product_name} ({self.business.business_name})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.minimum_price is not None and self.maximum_price is not None:
            if self.minimum_price > self.maximum_price:
                raise ValidationError("minimum_price cannot be greater than maximum_price.")
        if self.current_price is not None and self.minimum_price is not None and self.maximum_price is not None:
            if not (self.minimum_price <= self.current_price <= self.maximum_price):
                raise ValidationError("current_price must be between minimum_price and maximum_price.")

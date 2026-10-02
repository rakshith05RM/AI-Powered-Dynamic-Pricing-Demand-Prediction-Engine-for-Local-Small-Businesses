from django.db import models
from businesses.models import Business
from products.models import Product


class SalesRecord(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="sales_records")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales_records")
    sale_date = models.DateField()
    quantity_sold = models.PositiveIntegerField()
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sale_date"]
        indexes = [
            models.Index(fields=["product", "sale_date"]),
            models.Index(fields=["business", "sale_date"]),
        ]

    def save(self, *args, **kwargs):
        net_price = self.selling_price * (1 - (self.discount_percentage / 100))
        self.revenue = round(net_price * self.quantity_sold, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_name} - {self.sale_date} ({self.quantity_sold} units)"


class Promotion(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("scheduled", "Scheduled"), ("ended", "Ended")]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="promotions")
    promotion_name = models.CharField(max_length=150)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="scheduled")

    def __str__(self):
        return self.promotion_name


class CompetitorPrice(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="competitor_prices")
    competitor_name = models.CharField(max_length=150)
    competitor_price = models.DecimalField(max_digits=10, decimal_places=2)
    recorded_date = models.DateField()

    class Meta:
        ordering = ["-recorded_date"]

    def __str__(self):
        return f"{self.competitor_name} - {self.product.product_name}"

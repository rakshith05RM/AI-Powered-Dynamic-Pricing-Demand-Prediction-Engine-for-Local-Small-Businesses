from django.db import models
from businesses.models import Business
from products.models import Product


class BusinessAlert(models.Model):
    ALERT_TYPES = [
        ("high_demand", "High Demand Expected"),
        ("overstock", "Overstock Risk"),
        ("pricing_opportunity", "Pricing Opportunity"),
        ("stockout", "Stockout Risk"),
    ]
    SEVERITY_CHOICES = [("info", "Info"), ("warning", "Warning"), ("critical", "Critical")]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="alerts")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="alerts", null=True, blank=True)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    title = models.CharField(max_length=150)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="info")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

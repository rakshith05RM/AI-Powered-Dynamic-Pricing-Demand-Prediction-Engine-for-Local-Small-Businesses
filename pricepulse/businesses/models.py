from django.conf import settings
from django.db import models


class Business(models.Model):
    BUSINESS_TYPES = [
        ("grocery", "Grocery Store"),
        ("bakery", "Bakery"),
        ("restaurant", "Restaurant"),
        ("cafe", "Cafe"),
        ("clothing", "Clothing Store"),
        ("electronics", "Electronics Shop"),
        ("pharmacy", "Pharmacy"),
        ("retail", "Small Retail Store"),
        ("salon", "Salon"),
        ("service", "Local Service Business"),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business"
    )
    business_name = models.CharField(max_length=150)
    owner_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, default="retail")
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name

from django.contrib import admin
from .models import BusinessAlert

@admin.register(BusinessAlert)
class BusinessAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "business", "alert_type", "severity", "is_read", "created_at")
    list_filter = ("alert_type", "severity", "is_read")

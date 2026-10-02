from django.contrib import admin
from .models import Business

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("business_name", "owner_name", "business_type", "email", "created_at")
    search_fields = ("business_name", "owner_name", "email")

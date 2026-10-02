from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_name", "business", "category", "current_price", "stock_quantity")
    list_filter = ("category", "business")
    search_fields = ("product_name", "sku")

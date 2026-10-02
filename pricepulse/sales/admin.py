from django.contrib import admin
from .models import SalesRecord, Promotion, CompetitorPrice

@admin.register(SalesRecord)
class SalesRecordAdmin(admin.ModelAdmin):
    list_display = ("product", "sale_date", "quantity_sold", "selling_price", "revenue")
    list_filter = ("sale_date", "product")

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("promotion_name", "product", "discount_percentage", "status")

@admin.register(CompetitorPrice)
class CompetitorPriceAdmin(admin.ModelAdmin):
    list_display = ("competitor_name", "product", "competitor_price", "recorded_date")

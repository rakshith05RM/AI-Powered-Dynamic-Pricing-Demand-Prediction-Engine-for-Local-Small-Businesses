from django.contrib import admin
from .models import PriceRecommendation

@admin.register(PriceRecommendation)
class PriceRecommendationAdmin(admin.ModelAdmin):
    list_display = ("product", "current_price", "recommended_price", "price_change_percentage", "is_applied")

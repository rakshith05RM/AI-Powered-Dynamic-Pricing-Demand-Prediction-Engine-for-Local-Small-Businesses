from django.urls import path
from .views import PriceRecommendationsView, PriceSimulateView, PriceApplyView

urlpatterns = [
    path("pricing/recommendations/", PriceRecommendationsView.as_view(), name="pricing-recommendations"),
    path("pricing/simulate/", PriceSimulateView.as_view(), name="pricing-simulate"),
    path("pricing/apply/", PriceApplyView.as_view(), name="pricing-apply"),
]

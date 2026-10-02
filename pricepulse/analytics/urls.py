from django.urls import path
from .views import RevenueAnalyticsView

urlpatterns = [
    path("analytics/revenue/", RevenueAnalyticsView.as_view(), name="analytics-revenue"),
]

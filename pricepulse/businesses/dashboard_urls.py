from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_overview, name="dashboard_overview"),
    path("products/", views.dashboard_products, name="dashboard_products"),
    path("sales/", views.dashboard_sales, name="dashboard_sales"),
    path("forecast/", views.dashboard_forecast, name="dashboard_forecast"),
    path("pricing/", views.dashboard_pricing, name="dashboard_pricing"),
    path("inventory/", views.dashboard_inventory, name="dashboard_inventory"),
    path("alerts/", views.dashboard_alerts, name="dashboard_alerts"),
    path("analytics/", views.dashboard_analytics, name="dashboard_analytics"),
    path("model/", views.dashboard_model, name="dashboard_model"),
]

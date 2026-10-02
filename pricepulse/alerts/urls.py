from django.urls import path
from .views import BusinessAlertListView, BusinessAlertMarkReadView

urlpatterns = [
    path("alerts/", BusinessAlertListView.as_view(), name="alerts-list"),
    path("alerts/<int:pk>/read/", BusinessAlertMarkReadView.as_view(), name="alerts-read"),
]

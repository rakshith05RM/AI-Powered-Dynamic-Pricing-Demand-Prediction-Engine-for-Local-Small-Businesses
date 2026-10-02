from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import SalesRecordViewSet, SalesImportView

router = DefaultRouter()
router.register("sales", SalesRecordViewSet, basename="sales")

urlpatterns = [
    path("sales/import/", SalesImportView.as_view(), name="sales-import"),
] + router.urls

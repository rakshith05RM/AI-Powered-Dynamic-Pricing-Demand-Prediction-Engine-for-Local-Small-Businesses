from rest_framework import viewsets, permissions, filters
from .models import Product
from .serializers import ProductSerializer


class IsBusinessOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "business")


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsBusinessOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["product_name", "sku", "category"]
    ordering_fields = ["product_name", "current_price", "stock_quantity", "created_at"]

    def get_queryset(self):
        qs = Product.objects.filter(business=self.request.user.business)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs

    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)

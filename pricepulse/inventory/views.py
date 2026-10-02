from datetime import date, timedelta

from django.db.models import Avg
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from sales.models import SalesRecord


class IsBusinessOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "business")


def _status_for(days_remaining, stock, reorder_level):
    if stock == 0 or days_remaining <= 3:
        return "Critical"
    if days_remaining <= 7 or stock <= reorder_level:
        return "Low"
    if days_remaining >= 45:
        return "Overstocked"
    return "Healthy"


class InventoryView(APIView):
    """GET /api/inventory/ -> derived inventory intelligence per product."""
    permission_classes = [IsBusinessOwner]

    def get(self, request):
        business = request.user.business
        since = date.today() - timedelta(days=14)
        rows = []

        for product in Product.objects.filter(business=business):
            avg_daily = SalesRecord.objects.filter(
                product=product, sale_date__gte=since
            ).aggregate(avg=Avg("quantity_sold"))["avg"]
            daily_demand = round(float(avg_daily), 1) if avg_daily else 0.0

            days_remaining = round(product.stock_quantity / daily_demand, 1) if daily_demand > 0 else None
            status_label = _status_for(
                days_remaining if days_remaining is not None else 9999,
                product.stock_quantity,
                product.reorder_level,
            )

            if status_label == "Critical":
                shortfall = max((daily_demand * 14) - product.stock_quantity, daily_demand * 5)
                recommendation = f"Restock approximately {round(shortfall)} units."
            elif status_label == "Low":
                shortfall = max((daily_demand * 14) - product.stock_quantity, 0)
                recommendation = f"Consider restocking around {round(shortfall)} units soon."
            elif status_label == "Overstocked":
                recommendation = "Consider a promotion or price reduction to move excess stock."
            else:
                recommendation = "No action needed."

            rows.append({
                "product_id": product.id,
                "product_name": product.product_name,
                "stock": product.stock_quantity,
                "daily_demand": daily_demand,
                "days_remaining": days_remaining,
                "status": status_label,
                "recommendation": recommendation,
            })

        return Response(rows)

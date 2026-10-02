from datetime import date, timedelta

from django.db.models import Sum, Avg, Count
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import SalesRecord

RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}


class IsBusinessOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "business")


class RevenueAnalyticsView(APIView):
    """GET /api/analytics/revenue/?range=7d|30d|90d"""
    permission_classes = [IsBusinessOwner]

    def get(self, request):
        business = request.user.business
        range_key = request.query_params.get("range", "30d")
        days = RANGE_DAYS.get(range_key, 30)
        since = date.today() - timedelta(days=days)

        base_qs = SalesRecord.objects.filter(business=business, sale_date__gte=since)

        # sale_date is already a plain DateField (no time component), so we can
        # group directly on it without TruncDate (which has SQLite/timezone quirks).
        daily = (
            base_qs.values("sale_date")
            .annotate(revenue=Sum("revenue"), units=Sum("quantity_sold"))
            .order_by("sale_date")
        )

        totals = base_qs.aggregate(
            total_revenue=Sum("revenue"),
            total_units=Sum("quantity_sold"),
            avg_order_value=Avg("revenue"),
        )

        category_performance = (
            base_qs.values("product__category")
            .annotate(revenue=Sum("revenue"), units=Sum("quantity_sold"))
            .order_by("-revenue")
        )

        product_performance = (
            base_qs.values("product__id", "product__product_name")
            .annotate(revenue=Sum("revenue"), units=Sum("quantity_sold"), orders=Count("id"))
            .order_by("-revenue")[:10]
        )

        return Response({
            "range": range_key,
            "daily": [
                {"date": row["sale_date"].isoformat(), "revenue": float(row["revenue"] or 0), "units": row["units"] or 0}
                for row in daily
            ],
            "totals": {
                "revenue": float(totals["total_revenue"] or 0),
                "units": totals["total_units"] or 0,
                "avg_order_value": round(float(totals["avg_order_value"] or 0), 2),
            },
            "category_performance": [
                {
                    "category": row["product__category"],
                    "revenue": float(row["revenue"] or 0),
                    "units": row["units"] or 0,
                }
                for row in category_performance
            ],
            "top_products": [
                {
                    "product_id": row["product__id"],
                    "product_name": row["product__product_name"],
                    "revenue": float(row["revenue"] or 0),
                    "units": row["units"] or 0,
                    "orders": row["orders"],
                }
                for row in product_performance
            ],
        })

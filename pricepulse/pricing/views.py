from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from sales.models import SalesRecord, Promotion
from forecasting.models import ModelMetadata
from forecasting.services.demand_predictor import DemandPredictor, PredictionUnavailable
from .models import PriceRecommendation
from .serializers import PriceRecommendationSerializer
from .services.pricing_engine import PricingEngine


class IsBusinessOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "business")


def _recent_avg_daily_demand(product, days=30):
    since = date.today() - timedelta(days=days)
    avg = SalesRecord.objects.filter(product=product, sale_date__gte=since).aggregate(avg=Avg("quantity_sold"))["avg"]
    if avg is None:
        # fall back to all-time average if there isn't a full recent window yet
        avg = SalesRecord.objects.filter(product=product).aggregate(avg=Avg("quantity_sold"))["avg"]
    return float(avg) if avg else 0.0


def _active_promotion(product):
    today = date.today()
    return Promotion.objects.filter(product=product, status="active", start_date__lte=today, end_date__gte=today).first()


class PriceRecommendationsView(APIView):
    """GET /api/pricing/recommendations/ -> one recommendation per product with enough data."""
    permission_classes = [IsBusinessOwner]

    def get(self, request):
        business = request.user.business
        try:
            ModelMetadata.objects.get(business=business)
        except ModelMetadata.DoesNotExist:
            return Response({"detail": "No trained model yet. Import sales data and train the model first."},
                             status=status.HTTP_400_BAD_REQUEST)

        predictor = DemandPredictor(business)
        engine = PricingEngine()
        tomorrow = date.today() + timedelta(days=1)

        recommendations = []
        for product in Product.objects.filter(business=business):
            recent_avg = _recent_avg_daily_demand(product)
            if recent_avg == 0:
                continue  # not enough sales history for this product yet
            try:
                predicted_demand, _confidence = predictor.predict(product, tomorrow)
            except PredictionUnavailable:
                continue

            promo = _active_promotion(product)
            result = engine.recommend(product, predicted_demand, recent_avg, active_promotion=promo)

            rec = PriceRecommendation.objects.create(
                product=product,
                current_price=product.current_price,
                recommended_price=result["recommended_price"],
                predicted_demand=predicted_demand,
                expected_revenue=result["expected_revenue"],
                price_change_percentage=result["price_change_percentage"],
                reason=result["reason"],
            )
            recommendations.append(rec)

        return Response(PriceRecommendationSerializer(recommendations, many=True).data)


class PriceSimulateView(APIView):
    """POST /api/pricing/simulate/ {product, price} -> live what-if demand/revenue at a candidate price."""
    permission_classes = [IsBusinessOwner]

    def post(self, request):
        business = request.user.business
        product_id = request.data.get("product")
        try:
            price = Decimal(str(request.data.get("price")))
        except Exception:
            return Response({"detail": "A numeric 'price' is required."}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(id=product_id, business=business).first()
        if not product:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            predictor = DemandPredictor(business)
        except PredictionUnavailable as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        tomorrow = date.today() + timedelta(days=1)
        try:
            simulated_demand, confidence = predictor.predict(product, tomorrow, price_override=price)
            current_demand, _ = predictor.predict(product, tomorrow, price_override=product.current_price)
        except PredictionUnavailable as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        simulated_revenue = round(float(price) * simulated_demand, 2)
        current_revenue = round(float(product.current_price) * current_demand, 2)
        revenue_change_pct = (
            ((simulated_revenue - current_revenue) / current_revenue * 100) if current_revenue else 0.0
        )
        demand_change_pct = (
            ((simulated_demand - current_demand) / current_demand * 100) if current_demand else 0.0
        )

        return Response({
            "product": product.product_name,
            "simulated_price": float(price),
            "estimated_demand": simulated_demand,
            "estimated_revenue": simulated_revenue,
            "current_price": float(product.current_price),
            "current_demand": current_demand,
            "current_revenue": current_revenue,
            "revenue_change_percentage": round(revenue_change_pct, 1),
            "demand_change_percentage": round(demand_change_pct, 1),
            "confidence": confidence,
        })


class PriceApplyView(APIView):
    """POST /api/pricing/apply/ {recommendation_id} -> applies the recommended price to the product."""
    permission_classes = [IsBusinessOwner]

    def post(self, request):
        rec_id = request.data.get("recommendation_id")
        rec = PriceRecommendation.objects.filter(id=rec_id, product__business=request.user.business).first()
        if not rec:
            return Response({"detail": "Recommendation not found."}, status=status.HTTP_404_NOT_FOUND)

        product = rec.product
        product.current_price = rec.recommended_price
        product.save(update_fields=["current_price", "updated_at"])

        rec.is_applied = True
        rec.save(update_fields=["is_applied"])

        return Response({
            "detail": f"Price for {product.product_name} updated to {rec.recommended_price}.",
            "product_id": product.id,
            "new_price": float(product.current_price),
        })

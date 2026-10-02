from datetime import timedelta, date

from django.db.models import Avg
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from sales.models import SalesRecord
from .models import DemandPrediction, ModelMetadata
from .serializers import DemandPredictionSerializer, ModelMetadataSerializer
from .services.demand_predictor import DemandPredictor, PredictionUnavailable


class IsBusinessOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "business")


def _generate_forecast(business, product, horizon_days, model_version):
    predictor = DemandPredictor(business)
    results = []
    today = date.today()
    for offset in range(1, horizon_days + 1):
        target_date = today + timedelta(days=offset)
        quantity, confidence = predictor.predict(product, target_date)
        obj, _ = DemandPrediction.objects.update_or_create(
            product=product, prediction_date=target_date, model_version=model_version,
            defaults={"predicted_quantity": quantity, "confidence_score": confidence},
        )
        results.append(obj)
    return results


class DemandForecastView(APIView):
    """GET /api/demand/forecast/?product=<id>&days=7 -> generates/refreshes and returns the forecast."""
    permission_classes = [IsBusinessOwner]

    def get(self, request):
        product_id = request.query_params.get("product")
        days = int(request.query_params.get("days", 7))
        days = max(1, min(days, 30))

        if not product_id:
            return Response({"detail": "product query param is required."}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(id=product_id, business=request.user.business).first()
        if not product:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            metadata = ModelMetadata.objects.get(business=request.user.business)
        except ModelMetadata.DoesNotExist:
            return Response({
                "detail": "No trained model yet. Import sales data and train the model first."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            results = _generate_forecast(request.user.business, product, days, metadata.model_version)
        except PredictionUnavailable as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        since = date.today() - timedelta(days=14)
        historical = list(
            SalesRecord.objects.filter(product=product, sale_date__gte=since)
            .values("sale_date").order_by("sale_date")
        )
        # aggregate in case of multiple records per day
        agg = {}
        for row in SalesRecord.objects.filter(product=product, sale_date__gte=since):
            agg[row.sale_date] = agg.get(row.sale_date, 0) + row.quantity_sold
        historical_series = [{"date": d.isoformat(), "quantity": q} for d, q in sorted(agg.items())]

        recent_avg = SalesRecord.objects.filter(
            product=product, sale_date__gte=date.today() - timedelta(days=14)
        ).aggregate(avg=Avg("quantity_sold"))["avg"] or 0
        predicted_avg = sum(r.predicted_quantity for r in results) / len(results) if results else 0
        growth_pct = round(((predicted_avg - recent_avg) / recent_avg) * 100, 1) if recent_avg else 0.0

        return Response({
            "product": product.product_name,
            "model": ModelMetadataSerializer(metadata).data,
            "forecast": DemandPredictionSerializer(results, many=True).data,
            "historical": historical_series,
            "current_demand": round(float(recent_avg), 1),
            "predicted_demand": round(float(predicted_avg), 1),
            "growth_percentage": growth_pct,
            "avg_confidence": round(sum(r.confidence_score for r in results) / len(results), 1) if results else 0,
        })


class DemandPredictView(APIView):
    permission_classes = [IsBusinessOwner]

    def post(self, request):
        product_id = request.data.get("product")
        days = int(request.data.get("days", 7))
        days = max(1, min(days, 30))

        product = Product.objects.filter(id=product_id, business=request.user.business).first()
        if not product:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            metadata = ModelMetadata.objects.get(business=request.user.business)
        except ModelMetadata.DoesNotExist:
            return Response({"detail": "No trained model yet."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            results = _generate_forecast(request.user.business, product, days, metadata.model_version)
        except PredictionUnavailable as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DemandPredictionSerializer(results, many=True).data)


class ModelRetrainView(APIView):
    """POST /api/model/retrain/ -> re-runs the training pipeline for the logged-in user's business."""
    permission_classes = [IsBusinessOwner]

    def post(self, request):
        from io import StringIO
        from django.core.management import call_command

        out = StringIO()
        try:
            call_command("train_demand_model", business_id=request.user.business.id, stdout=out)
        except Exception as e:
            return Response({"detail": f"Training failed: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        if not ModelMetadata.objects.filter(business=request.user.business).exists():
            return Response({
                "detail": "Not enough sales history to train a model yet (minimum 30 records required)."
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Model retrained successfully.", "log": out.getvalue()})

import csv
import io
from datetime import datetime

from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SalesRecord
from .serializers import SalesRecordSerializer
from products.models import Product


class IsBusinessOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "business")


class SalesRecordViewSet(viewsets.ModelViewSet):
    serializer_class = SalesRecordSerializer
    permission_classes = [IsBusinessOwner]

    def get_queryset(self):
        qs = SalesRecord.objects.filter(business=self.request.user.business).select_related("product")
        product_id = self.request.query_params.get("product")
        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        if product_id:
            qs = qs.filter(product_id=product_id)
        if date_from:
            qs = qs.filter(sale_date__gte=date_from)
        if date_to:
            qs = qs.filter(sale_date__lte=date_to)
        return qs

    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


REQUIRED_CSV_COLUMNS = {"sku", "sale_date", "quantity_sold", "selling_price"}


class SalesImportView(APIView):
    """
    Accepts a CSV upload with columns: sku, sale_date, quantity_sold, selling_price[, discount_percentage]
    Validates each row and reports valid/invalid counts + per-row errors instead of crashing.
    """
    permission_classes = [IsBusinessOwner]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file uploaded. Attach a CSV as 'file'."}, status=status.HTTP_400_BAD_REQUEST)

        if file_obj.size > settings.MAX_CSV_UPLOAD_SIZE:
            return Response({"detail": "File too large. Maximum size is 5MB."}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.lower().endswith(".csv"):
            return Response({"detail": "Only .csv files are accepted."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = file_obj.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response({"detail": "Could not decode file. Please upload a UTF-8 CSV."}, status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(decoded))
        if reader.fieldnames is None or not REQUIRED_CSV_COLUMNS.issubset(set(c.strip().lower() for c in reader.fieldnames)):
            return Response({
                "detail": f"CSV must contain columns: {', '.join(sorted(REQUIRED_CSV_COLUMNS))}"
            }, status=status.HTTP_400_BAD_REQUEST)

        business = request.user.business
        sku_to_product = {p.sku: p for p in Product.objects.filter(business=business)}

        valid_records = []
        errors = []
        total_rows = 0

        for i, raw_row in enumerate(reader, start=2):  # row 1 is header
            total_rows += 1
            row = {k.strip().lower(): (v.strip() if v else v) for k, v in raw_row.items()}
            row_errors = []

            sku = row.get("sku")
            product = sku_to_product.get(sku)
            if not sku:
                row_errors.append("missing sku")
            elif not product:
                row_errors.append(f"unknown product SKU '{sku}'")

            sale_date = None
            try:
                sale_date = datetime.strptime(row.get("sale_date", ""), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                row_errors.append("invalid or missing sale_date (expected YYYY-MM-DD)")

            quantity_sold = None
            try:
                quantity_sold = int(row.get("quantity_sold"))
                if quantity_sold < 0:
                    row_errors.append("negative quantity_sold")
            except (ValueError, TypeError):
                row_errors.append("invalid or missing quantity_sold")

            selling_price = None
            try:
                selling_price = float(row.get("selling_price"))
                if selling_price < 0:
                    row_errors.append("negative selling_price")
            except (ValueError, TypeError):
                row_errors.append("invalid or missing selling_price")

            discount_percentage = 0.0
            raw_discount = row.get("discount_percentage")
            if raw_discount:
                try:
                    discount_percentage = float(raw_discount)
                    if not (0 <= discount_percentage <= 100):
                        row_errors.append("discount_percentage must be between 0 and 100")
                except ValueError:
                    row_errors.append("invalid discount_percentage")

            if row_errors:
                errors.append({"row": i, "errors": row_errors})
                continue

            valid_records.append(SalesRecord(
                business=business,
                product=product,
                sale_date=sale_date,
                quantity_sold=quantity_sold,
                selling_price=selling_price,
                discount_percentage=discount_percentage,
            ))

        for record in valid_records:
            record.save()

        return Response({
            "rows_detected": total_rows,
            "valid_records": len(valid_records),
            "invalid_records": len(errors),
            "errors": errors[:50],  # cap error list shown
        }, status=status.HTTP_200_OK)

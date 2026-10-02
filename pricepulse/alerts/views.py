from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BusinessAlert
from .serializers import BusinessAlertSerializer


class IsBusinessOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "business")


class BusinessAlertListView(APIView):
    permission_classes = [IsBusinessOwner]

    def get(self, request):
        qs = BusinessAlert.objects.filter(business=request.user.business)
        unread_only = request.query_params.get("unread")
        if unread_only == "true":
            qs = qs.filter(is_read=False)
        return Response(BusinessAlertSerializer(qs, many=True).data)


class BusinessAlertMarkReadView(APIView):
    permission_classes = [IsBusinessOwner]

    def post(self, request, pk):
        alert = BusinessAlert.objects.filter(id=pk, business=request.user.business).first()
        if not alert:
            return Response({"detail": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)
        alert.is_read = True
        alert.save(update_fields=["is_read"])
        return Response({"detail": "Alert marked as read."})

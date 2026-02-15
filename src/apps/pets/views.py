from rest_framework import decorators, response

from apps.common.viewsets import RBACModelViewSet

from .models import Pet, PetAttachment
from .serializers import PetAttachmentSerializer, PetSerializer


class PetViewSet(RBACModelViewSet):
    queryset = Pet.objects.select_related("owner").all()
    serializer_class = PetSerializer
    filterset_fields = ["owner", "species", "status", "microchip_id"]
    search_fields = ["name", "owner__phone", "owner__last_name", "microchip_id", "qr_token"]
    ordering_fields = ["created_at", "name", "weight_kg"]

    @decorators.action(detail=False, methods=["get"], url_path="resolve-qr")
    def resolve_qr(self, request):
        token = request.query_params.get("token")
        if not token:
            return response.Response({"detail": "token is required"}, status=400)
        pet = self.get_queryset().filter(qr_token=token).first()
        if pet is None:
            return response.Response({"detail": "pet not found"}, status=404)
        serializer = self.get_serializer(pet)
        return response.Response(serializer.data)


class PetAttachmentViewSet(RBACModelViewSet):
    queryset = PetAttachment.objects.select_related("pet").all()
    serializer_class = PetAttachmentSerializer
    filterset_fields = ["pet"]
    search_fields = ["pet__name", "title"]
    ordering_fields = ["created_at"]

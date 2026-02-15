from apps.common.viewsets import RBACModelViewSet

from .models import ConsentDocument, Owner
from .serializers import ConsentDocumentSerializer, OwnerSerializer


class OwnerViewSet(RBACModelViewSet):
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer
    filterset_fields = ["is_blacklisted", "preferred_branch"]
    search_fields = ["first_name", "last_name", "phone", "email", "preferred_branch__name", "preferred_branch__code"]
    ordering_fields = ["created_at", "last_name"]


class ConsentDocumentViewSet(RBACModelViewSet):
    queryset = ConsentDocument.objects.select_related("owner").all()
    serializer_class = ConsentDocumentSerializer
    filterset_fields = ["consent_type", "owner"]
    search_fields = ["owner__first_name", "owner__last_name", "owner__phone"]
    ordering_fields = ["accepted_at", "created_at"]

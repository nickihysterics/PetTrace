from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import decorators, response, status
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.viewsets import RBACModelViewSet, RBACReadOnlyModelViewSet
from apps.users.access import (
    ensure_user_can_access_branch_cabinet,
    is_unrestricted_user,
    restrict_queryset_for_user_scope,
)

from .models import ClinicalDocument, DocumentStoragePolicy, DocumentTemplate, GeneratedDocument
from .serializers import (
    ClinicalDocumentSerializer,
    DocumentStoragePolicySerializer,
    DocumentTemplateSerializer,
    GeneratedDocumentSerializer,
)
from .services import generate_document_from_template


class DocumentStoragePolicyViewSet(RBACModelViewSet):
    queryset = DocumentStoragePolicy.objects.all()
    serializer_class = DocumentStoragePolicySerializer
    filterset_fields = ["storage_backend", "is_default", "is_active"]
    search_fields = ["name"]


class ClinicalDocumentViewSet(RBACModelViewSet):
    queryset = ClinicalDocument.objects.select_related(
        "pet",
        "visit",
        "lab_order",
        "lab_order__visit",
        "uploaded_by",
        "replaced_by",
        "storage_policy",
    ).all()
    serializer_class = ClinicalDocumentSerializer
    filterset_fields = ["document_type", "pet", "visit", "lab_order", "is_current", "storage_policy"]
    search_fields = ["title", "description", "mime_type"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = getattr(self.request, "user", None)
        if is_unrestricted_user(user):
            return queryset

        visit_docs = restrict_queryset_for_user_scope(
            queryset=queryset.filter(visit__isnull=False),
            user=user,
            branch_field="visit__branch",
            cabinet_field="visit__cabinet",
            allow_unassigned=True,
        )
        lab_docs = restrict_queryset_for_user_scope(
            queryset=queryset.filter(lab_order__isnull=False),
            user=user,
            branch_field="lab_order__visit__branch",
            cabinet_field="lab_order__visit__cabinet",
            allow_unassigned=True,
        )
        pet_only_docs = queryset.filter(visit__isnull=True, lab_order__isnull=True)
        if not user or not user.is_authenticated:
            return queryset.none()
        return queryset.filter(
            Q(id__in=visit_docs.values("id"))
            | Q(id__in=lab_docs.values("id"))
            | Q(id__in=pet_only_docs.values("id"))
        ).distinct()

    def _ensure_scope(self, *, visit=None, lab_order=None) -> None:
        branch = None
        cabinet = None
        if visit is not None:
            branch = visit.branch
            cabinet = visit.cabinet
        elif lab_order is not None:
            branch = getattr(lab_order.visit, "branch", None)
            cabinet = getattr(lab_order.visit, "cabinet", None)

        ensure_user_can_access_branch_cabinet(
            user=self.request.user,
            branch=branch,
            cabinet=cabinet,
        )

    def perform_create(self, serializer):
        visit = serializer.validated_data.get("visit")
        lab_order = serializer.validated_data.get("lab_order")
        try:
            self._ensure_scope(visit=visit, lab_order=lab_order)
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        uploaded_file = serializer.validated_data.get("file")
        file_size = getattr(uploaded_file, "size", 0)
        mime_type = self.request.data.get("mime_type", "")
        storage_policy = serializer.validated_data.get("storage_policy")
        if storage_policy and file_size > (storage_policy.max_file_size_mb * 1024 * 1024):
            raise DRFValidationError("file exceeds storage policy size limit")

        serializer.save(
            uploaded_by=self.request.user if self.request.user.is_authenticated else None,
            file_size_bytes=file_size,
            mime_type=mime_type,
        )

    def perform_update(self, serializer):
        visit = serializer.validated_data.get("visit", serializer.instance.visit)
        lab_order = serializer.validated_data.get("lab_order", serializer.instance.lab_order)
        try:
            self._ensure_scope(visit=visit, lab_order=lab_order)
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        uploaded_file = serializer.validated_data.get("file")
        storage_policy = serializer.validated_data.get("storage_policy", serializer.instance.storage_policy)
        if uploaded_file and storage_policy and uploaded_file.size > (storage_policy.max_file_size_mb * 1024 * 1024):
            raise DRFValidationError("file exceeds storage policy size limit")

        save_kwargs = {}
        if uploaded_file:
            save_kwargs["file_size_bytes"] = getattr(uploaded_file, "size", 0)
            save_kwargs["mime_type"] = self.request.data.get(
                "mime_type",
                serializer.instance.mime_type,
            )
        elif "mime_type" in self.request.data:
            save_kwargs["mime_type"] = self.request.data.get("mime_type", "")
        serializer.save(**save_kwargs)

    @decorators.action(detail=True, methods=["post"], url_path="replace")
    @transaction.atomic
    def replace(self, request, pk=None):
        current_document = self.get_object()
        new_file = request.FILES.get("file")
        if new_file is None:
            return response.Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

        replacement = ClinicalDocument(
            document_type=current_document.document_type,
            title=request.data.get("title", current_document.title),
            description=request.data.get("description", current_document.description),
            file=new_file,
            mime_type=request.data.get("mime_type", current_document.mime_type),
            file_size_bytes=getattr(new_file, "size", 0),
            storage_policy=current_document.storage_policy,
            pet=current_document.pet,
            visit=current_document.visit,
            lab_order=current_document.lab_order,
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        current_document.replace_with(
            new_document=replacement,
            actor=request.user if request.user.is_authenticated else None,
        )
        replacement.save()
        return response.Response(self.get_serializer(replacement).data, status=status.HTTP_201_CREATED)


class DocumentTemplateViewSet(RBACModelViewSet):
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    filterset_fields = ["template_type", "is_active"]
    search_fields = ["code", "name", "body_template"]

    @decorators.action(detail=True, methods=["post"], url_path="generate")
    @transaction.atomic
    def generate(self, request, pk=None):
        template = self.get_object()
        visit = None
        owner = None
        pet = None
        lab_order = None

        visit_id = request.data.get("visit")
        owner_id = request.data.get("owner")
        pet_id = request.data.get("pet")
        lab_order_id = request.data.get("lab_order")

        if visit_id:
            from apps.visits.models import Visit

            visit = Visit.objects.filter(id=visit_id).first()
            if visit is None:
                return response.Response({"detail": "visit not found"}, status=status.HTTP_404_NOT_FOUND)
            owner = visit.owner
            pet = visit.pet
        if owner_id:
            from apps.owners.models import Owner

            owner_obj = Owner.objects.filter(id=owner_id).first()
            if owner_obj is None:
                return response.Response({"detail": "owner not found"}, status=status.HTTP_404_NOT_FOUND)
            if owner and owner.id != owner_obj.id:
                return response.Response(
                    {"detail": "owner does not match selected visit context"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            owner = owner_obj
        if pet_id:
            from apps.pets.models import Pet

            pet_obj = Pet.objects.filter(id=pet_id).first()
            if pet_obj is None:
                return response.Response({"detail": "pet not found"}, status=status.HTTP_404_NOT_FOUND)
            if pet and pet.id != pet_obj.id:
                return response.Response(
                    {"detail": "pet does not match selected visit context"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pet = pet_obj
        if lab_order_id:
            from apps.labs.models import LabOrder

            lab_order = LabOrder.objects.filter(id=lab_order_id).first()
            if lab_order is None:
                return response.Response({"detail": "lab_order not found"}, status=status.HTTP_404_NOT_FOUND)
            if visit and lab_order.visit_id != visit.id:
                return response.Response(
                    {"detail": "lab_order does not belong to selected visit"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if visit is None:
                visit = lab_order.visit

            if owner and owner.id != visit.owner_id:
                return response.Response(
                    {"detail": "owner does not match selected visit/lab_order context"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            owner = visit.owner

            if pet and pet.id != visit.pet_id:
                return response.Response(
                    {"detail": "pet does not match selected visit/lab_order context"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pet = visit.pet

        if owner and pet and pet.owner_id != owner.id:
            return response.Response(
                {"detail": "pet does not belong to selected owner"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = request.data.get("payload", {})
        if visit:
            try:
                ensure_user_can_access_branch_cabinet(
                    user=request.user,
                    branch=visit.branch,
                    cabinet=visit.cabinet,
                )
            except ValidationError as exc:
                detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
                return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        generated = generate_document_from_template(
            template=template,
            payload=payload,
            filename_prefix=template.code.lower(),
            generated_by=request.user if request.user.is_authenticated else None,
            visit=visit,
            owner=owner,
            pet=pet,
            lab_order=lab_order,
        )
        return response.Response(GeneratedDocumentSerializer(generated).data, status=status.HTTP_201_CREATED)


class GeneratedDocumentViewSet(RBACReadOnlyModelViewSet):
    queryset = GeneratedDocument.objects.select_related(
        "template",
        "visit",
        "owner",
        "pet",
        "lab_order",
        "generated_by",
    ).all()
    serializer_class = GeneratedDocumentSerializer
    filterset_fields = ["template", "visit", "owner", "pet", "lab_order", "generated_by"]
    search_fields = ["template__code", "template__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = getattr(self.request, "user", None)
        if is_unrestricted_user(user):
            return queryset

        visit_docs = restrict_queryset_for_user_scope(
            queryset=queryset.filter(visit__isnull=False),
            user=user,
            branch_field="visit__branch",
            cabinet_field="visit__cabinet",
            allow_unassigned=True,
        )
        lab_docs = restrict_queryset_for_user_scope(
            queryset=queryset.filter(lab_order__isnull=False),
            user=user,
            branch_field="lab_order__visit__branch",
            cabinet_field="lab_order__visit__cabinet",
            allow_unassigned=True,
        )
        context_free_docs = queryset.filter(visit__isnull=True, lab_order__isnull=True)
        if not user or not user.is_authenticated:
            return queryset.none()
        return queryset.filter(
            Q(id__in=visit_docs.values("id"))
            | Q(id__in=lab_docs.values("id"))
            | Q(id__in=context_free_docs.values("id"))
        ).distinct()

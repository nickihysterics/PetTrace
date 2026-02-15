from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import DocumentTemplate, GeneratedDocument
from apps.facilities.models import Branch, Cabinet
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.users.models import UserAccessProfile
from apps.visits.models import Visit


class GeneratedDocumentScopeApiTests(APITestCase):
    def setUp(self):
        self.allowed_branch = Branch.objects.create(code="DBAL", name="Docs allowed branch")
        self.allowed_cabinet = Cabinet.objects.create(
            branch=self.allowed_branch,
            code="A110",
            name="Allowed cabinet",
            cabinet_type=Cabinet.CabinetType.CONSULTATION,
        )
        self.denied_branch = Branch.objects.create(code="DBDN", name="Docs denied branch")
        self.denied_cabinet = Cabinet.objects.create(
            branch=self.denied_branch,
            code="D110",
            name="Denied cabinet",
            cabinet_type=Cabinet.CabinetType.CONSULTATION,
        )

        owner = Owner.objects.create(first_name="Docs", last_name="Owner", phone="+79990003001")
        pet = Pet.objects.create(
            owner=owner,
            name="DocsPet",
            species=Pet.Species.CAT,
            microchip_id="900000000003001",
        )
        self.allowed_visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
            branch=self.allowed_branch,
            cabinet=self.allowed_cabinet,
        )
        self.denied_visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
            branch=self.denied_branch,
            cabinet=self.denied_cabinet,
        )

        template = DocumentTemplate.objects.create(
            code="SCOPE_DOC",
            name="Scope template",
            template_type=DocumentTemplate.TemplateType.OTHER,
            body_template="Scope",
        )

        self.allowed_doc = GeneratedDocument.objects.create(
            template=template,
            visit=self.allowed_visit,
            owner=owner,
            pet=pet,
            payload={"scope": "allowed"},
            file=SimpleUploadedFile("allowed.pdf", b"%PDF-1.4 allowed\n", content_type="application/pdf"),
        )
        self.denied_doc = GeneratedDocument.objects.create(
            template=template,
            visit=self.denied_visit,
            owner=owner,
            pet=pet,
            payload={"scope": "denied"},
            file=SimpleUploadedFile("denied.pdf", b"%PDF-1.4 denied\n", content_type="application/pdf"),
        )

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="scope.documents@pettrace.local",
            password="test",
        )
        self._grant_perm("documents", "view_generateddocument")

        profile = UserAccessProfile.objects.create(
            user=self.user,
            home_branch=self.allowed_branch,
            limit_to_assigned_cabinets=True,
        )
        profile.allowed_branches.add(self.allowed_branch)
        profile.allowed_cabinets.add(self.allowed_cabinet)

        self.client.force_authenticate(self.user)

    def _grant_perm(self, app_label: str, codename: str):
        permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        self.user.user_permissions.add(permission)

    def test_list_returns_only_documents_within_scope(self):
        response = self.client.get("/api/documents/generated/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertSetEqual(returned_ids, {self.allowed_doc.id})

    def test_retrieve_out_of_scope_document_returns_404(self):
        response = self.client.get(f"/api/documents/generated/{self.denied_doc.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

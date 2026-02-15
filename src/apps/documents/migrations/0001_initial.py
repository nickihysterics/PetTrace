# Сгенерировано Django 5.2.11 от 2026-02-13 23:30

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('labs', '0005_labparameterreference_labresultvalue_source_and_more'),
        ('owners', '0002_owner_preferred_branch'),
        ('pets', '0002_alter_pet_microchip_id'),
        ('visits', '0003_hospitalization_appointment_branch_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentStoragePolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=128, unique=True)),
                ('storage_backend', models.CharField(choices=[('LOCAL', 'Local'), ('S3', 'S3-compatible')], default='LOCAL', max_length=16)),
                ('max_file_size_mb', models.PositiveIntegerField(default=20)),
                ('allowed_mime_types', models.JSONField(blank=True, default=list)),
                ('is_default', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='DocumentTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('template_type', models.CharField(choices=[('CONSENT', 'Consent'), ('DISCHARGE', 'Discharge'), ('SERVICE_ACT', 'Service Act'), ('LAB_REFERRAL', 'Lab Referral'), ('OTHER', 'Other')], default='OTHER', max_length=16)),
                ('body_template', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='GeneratedDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('file', models.FileField(upload_to='generated-documents/')),
                ('generated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('generated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_documents', to=settings.AUTH_USER_MODEL)),
                ('lab_order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='generated_documents', to='labs.laborder')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='generated_documents', to='owners.owner')),
                ('pet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='generated_documents', to='pets.pet')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_documents', to='documents.documenttemplate')),
                ('visit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='generated_documents', to='visits.visit')),
            ],
            options={
                'ordering': ['-generated_at'],
            },
        ),
        migrations.CreateModel(
            name='ClinicalDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('document_uid', models.UUIDField(db_index=True, default=uuid.uuid4)),
                ('version', models.PositiveIntegerField(default=1)),
                ('is_current', models.BooleanField(db_index=True, default=True)),
                ('document_type', models.CharField(choices=[('XRAY', 'X-Ray'), ('ULTRASOUND', 'Ultrasound'), ('PHOTO', 'Photo'), ('PDF_RESULT', 'PDF Result'), ('DISCHARGE', 'Discharge'), ('OTHER', 'Other')], default='OTHER', max_length=16)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('file', models.FileField(upload_to='clinical-documents/')),
                ('mime_type', models.CharField(blank=True, max_length=128)),
                ('file_size_bytes', models.PositiveBigIntegerField(default=0)),
                ('replaced_at', models.DateTimeField(blank=True, null=True)),
                ('lab_order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='labs.laborder')),
                ('pet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clinical_documents', to='pets.pet')),
                ('previous_version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_versions', to='documents.clinicaldocument')),
                ('replaced_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replaced_documents', to=settings.AUTH_USER_MODEL)),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_documents', to=settings.AUTH_USER_MODEL)),
                ('visit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='visits.visit')),
                ('storage_policy', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='documents.documentstoragepolicy')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['document_uid', 'version'], name='documents_c_documen_5ae09e_idx'), models.Index(fields=['document_type', 'is_current'], name='documents_c_documen_15a165_idx')],
            },
        ),
    ]

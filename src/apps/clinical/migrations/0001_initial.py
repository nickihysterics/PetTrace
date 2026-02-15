# Сгенерировано Django 5.2.11 от 2026-02-13 18:51

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('visits', '0002_visitevent_appointment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ClinicalProtocol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('diagnosis_code', models.CharField(blank=True, max_length=32)),
                ('diagnosis_title', models.CharField(blank=True, max_length=255)),
                ('species', models.CharField(blank=True, choices=[('DOG', 'Dog'), ('CAT', 'Cat'), ('RABBIT', 'Rabbit'), ('BIRD', 'Bird'), ('OTHER', 'Other')], max_length=16)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
                'permissions': [('apply_clinical_protocol', 'Can apply clinical protocol')],
            },
        ),
        migrations.CreateModel(
            name='ContraindicationRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('medication_name', models.CharField(max_length=255)),
                ('allergy_keyword', models.CharField(blank=True, max_length=120)),
                ('species', models.CharField(blank=True, choices=[('DOG', 'Dog'), ('CAT', 'Cat'), ('RABBIT', 'Rabbit'), ('BIRD', 'Bird'), ('OTHER', 'Other')], max_length=16)),
                ('severity', models.CharField(choices=[('WARNING', 'Warning'), ('BLOCKING', 'Blocking')], default='WARNING', max_length=16)),
                ('message', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['medication_name', 'severity'],
            },
        ),
        migrations.CreateModel(
            name='ProcedureChecklistTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('procedure_name', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ClinicalAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('severity', models.CharField(choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('BLOCKING', 'Blocking')], default='WARNING', max_length=16)),
                ('message', models.TextField()),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('prescription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clinical_alerts', to='visits.prescription')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_clinical_alerts', to=settings.AUTH_USER_MODEL)),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clinical_alerts', to='visits.visit')),
                ('rule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alerts', to='clinical.contraindicationrule')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProcedureChecklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('status', models.CharField(choices=[('TODO', 'To Do'), ('IN_PROGRESS', 'In Progress'), ('DONE', 'Done'), ('CANCELED', 'Canceled')], default='TODO', max_length=16)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('procedure_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checklists', to='visits.procedureorder')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='checklists', to='clinical.procedurechecklisttemplate')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProcedureChecklistItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('is_required', models.BooleanField(default=True)),
                ('is_completed', models.BooleanField(default=False)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('checklist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='clinical.procedurechecklist')),
                ('completed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='completed_checklist_items', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['checklist', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ProcedureChecklistTemplateItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('is_required', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='clinical.procedurechecklisttemplate')),
            ],
            options={
                'ordering': ['template', 'sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ProtocolMedicationTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('medication_name', models.CharField(max_length=255)),
                ('dose_mg_per_kg', models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
                ('fixed_dose_mg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('min_dose_mg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('max_dose_mg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('frequency', models.CharField(blank=True, max_length=120)),
                ('duration_days', models.PositiveIntegerField(default=1)),
                ('route', models.CharField(blank=True, max_length=64)),
                ('warnings', models.TextField(blank=True)),
                ('protocol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medication_templates', to='clinical.clinicalprotocol')),
            ],
            options={
                'ordering': ['protocol', 'medication_name'],
            },
        ),
        migrations.CreateModel(
            name='ProtocolProcedureTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('instructions', models.TextField(blank=True)),
                ('protocol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='procedure_templates', to='clinical.clinicalprotocol')),
            ],
            options={
                'ordering': ['protocol', 'name'],
            },
        ),
    ]

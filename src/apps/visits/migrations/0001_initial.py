# Сгенерировано Django 5.2.11 от 2026-02-13 16:02

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('owners', '0001_initial'),
        ('pets', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('status', models.CharField(choices=[('SCHEDULED', 'Scheduled'), ('WAITING', 'Waiting'), ('IN_PROGRESS', 'In Progress'), ('COMPLETED', 'Completed'), ('CLOSED', 'Closed'), ('CANCELED', 'Canceled')], db_index=True, default='SCHEDULED', max_length=16)),
                ('room', models.CharField(blank=True, max_length=64)),
                ('scheduled_at', models.DateTimeField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('chief_complaint', models.TextField(blank=True)),
                ('anamnesis', models.TextField(blank=True)),
                ('physical_exam', models.TextField(blank=True)),
                ('diagnosis_summary', models.TextField(blank=True)),
                ('recommendations', models.TextField(blank=True)),
                ('assistant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assisted_visits', to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='visits', to='owners.owner')),
                ('pet', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='visits', to='pets.pet')),
                ('veterinarian', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_visits', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'permissions': [('close_visit', 'Can close visit')],
            },
        ),
        migrations.CreateModel(
            name='ProcedureOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('instructions', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('PLANNED', 'Planned'), ('IN_PROGRESS', 'In Progress'), ('DONE', 'Done'), ('CANCELED', 'Canceled')], default='PLANNED', max_length=16)),
                ('performed_at', models.DateTimeField(blank=True, null=True)),
                ('performed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='performed_procedures', to=settings.AUTH_USER_MODEL)),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='procedures', to='visits.visit')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Prescription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('medication_name', models.CharField(max_length=255)),
                ('dosage', models.CharField(max_length=120)),
                ('frequency', models.CharField(max_length=120)),
                ('duration_days', models.PositiveIntegerField(default=1)),
                ('route', models.CharField(blank=True, max_length=64)),
                ('warnings', models.TextField(blank=True)),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prescriptions', to='visits.visit')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Observation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('value', models.CharField(max_length=120)),
                ('unit', models.CharField(blank=True, max_length=32)),
                ('notes', models.TextField(blank=True)),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='observations', to='visits.visit')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Diagnosis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(blank=True, max_length=32)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('is_primary', models.BooleanField(default=False)),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='diagnoses', to='visits.visit')),
            ],
            options={
                'ordering': ['-is_primary', 'title'],
            },
        ),
        migrations.AddIndex(
            model_name='visit',
            index=models.Index(fields=['status', 'scheduled_at'], name='visits_visi_status_06e2c3_idx'),
        ),
    ]

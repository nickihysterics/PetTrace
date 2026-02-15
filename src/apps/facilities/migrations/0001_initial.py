# Сгенерировано Django 5.2.11 от 2026-02-13 18:51

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=32, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('phone', models.CharField(blank=True, max_length=32)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='EquipmentType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ServiceRequirement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('service_type', models.CharField(max_length=128, unique=True)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('required_cabinet_type', models.CharField(blank=True, choices=[('CONSULTATION', 'Consultation'), ('PROCEDURE', 'Procedure'), ('LAB', 'Laboratory'), ('SURGERY', 'Surgery'), ('INPATIENT', 'Inpatient'), ('OTHER', 'Other')], max_length=16)),
                ('default_duration_minutes', models.PositiveIntegerField(default=30)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['service_type'],
            },
        ),
        migrations.CreateModel(
            name='Cabinet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=32)),
                ('name', models.CharField(max_length=255)),
                ('cabinet_type', models.CharField(choices=[('CONSULTATION', 'Consultation'), ('PROCEDURE', 'Procedure'), ('LAB', 'Laboratory'), ('SURGERY', 'Surgery'), ('INPATIENT', 'Inpatient'), ('OTHER', 'Other')], default='CONSULTATION', max_length=16)),
                ('capacity', models.PositiveIntegerField(default=1)),
                ('is_active', models.BooleanField(default=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cabinets', to='facilities.branch')),
            ],
            options={
                'ordering': ['branch__name', 'code'],
            },
        ),
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('AVAILABLE', 'Available'), ('IN_USE', 'In Use'), ('MAINTENANCE', 'Maintenance'), ('OUT_OF_SERVICE', 'Out of Service')], default='AVAILABLE', max_length=16)),
                ('is_active', models.BooleanField(default=True)),
                ('last_maintenance_at', models.DateTimeField(blank=True, null=True)),
                ('next_maintenance_due_at', models.DateTimeField(blank=True, null=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipment', to='facilities.branch')),
                ('cabinet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipment', to='facilities.cabinet')),
                ('equipment_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipment', to='facilities.equipmenttype')),
            ],
            options={
                'ordering': ['branch__name', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ServiceRequirementEquipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('equipment_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='service_requirements', to='facilities.equipmenttype')),
                ('requirement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='required_equipment', to='facilities.servicerequirement')),
            ],
            options={
                'ordering': ['requirement__service_type', 'equipment_type__name'],
            },
        ),
        migrations.AddIndex(
            model_name='cabinet',
            index=models.Index(fields=['branch', 'cabinet_type', 'is_active'], name='facilities__branch__31acbb_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='cabinet',
            unique_together={('branch', 'code')},
        ),
        migrations.AddIndex(
            model_name='equipment',
            index=models.Index(fields=['branch', 'equipment_type', 'status', 'is_active'], name='facilities__branch__85e1e5_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='servicerequirementequipment',
            unique_together={('requirement', 'equipment_type')},
        ),
    ]

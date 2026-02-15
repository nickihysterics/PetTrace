# Сгенерировано Django 5.2.11 от 2026-02-13 23:30

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_remove_invoice_issued_at_invoice_discount_amount_and_more'),
        ('facilities', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=32, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AlterField(
            model_name='servicerequirement',
            name='service_type',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.CreateModel(
            name='HospitalWard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=32)),
                ('name', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='wards', to='facilities.branch')),
            ],
            options={
                'ordering': ['branch__name', 'code'],
                'unique_together': {('branch', 'code')},
            },
        ),
        migrations.AddField(
            model_name='branch',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='branches', to='facilities.organization'),
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('category', models.CharField(choices=[('CONSULTATION', 'Consultation'), ('LAB', 'Laboratory'), ('PROCEDURE', 'Procedure'), ('SURGERY', 'Surgery'), ('HOSPITAL', 'Hospital'), ('OTHER', 'Other')], default='OTHER', max_length=16)),
                ('description', models.TextField(blank=True)),
                ('default_duration_minutes', models.PositiveIntegerField(default=30)),
                ('is_active', models.BooleanField(default=True)),
                ('price_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='services', to='billing.priceitem')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='servicerequirement',
            name='service',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='requirement', to='facilities.service'),
        ),
        migrations.CreateModel(
            name='HospitalBed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=32)),
                ('status', models.CharField(choices=[('AVAILABLE', 'Available'), ('OCCUPIED', 'Occupied'), ('CLEANING', 'Cleaning'), ('MAINTENANCE', 'Maintenance'), ('OUT_OF_SERVICE', 'Out of Service')], default='AVAILABLE', max_length=16)),
                ('is_isolation', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('cabinet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hospital_beds', to='facilities.cabinet')),
                ('ward', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='beds', to='facilities.hospitalward')),
            ],
            options={
                'ordering': ['ward__branch__name', 'ward__code', 'code'],
                'indexes': [models.Index(fields=['ward', 'status', 'is_active'], name='facilities__ward_id_9016a0_idx')],
                'unique_together': {('ward', 'code')},
            },
        ),
    ]

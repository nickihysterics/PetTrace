# Сгенерировано Django 5.2.11 от 2026-02-13 23:30

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinical', '0002_diagnosiscatalog_symptomcatalog'),
        ('facilities', '0002_organization_alter_servicerequirement_service_type_and_more'),
        ('inventory', '0002_initial'),
        ('visits', '0003_hospitalization_appointment_branch_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='service',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointments', to='facilities.service'),
        ),
        migrations.AddField(
            model_name='diagnosis',
            name='catalog_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='diagnoses', to='clinical.diagnosiscatalog'),
        ),
        migrations.AddField(
            model_name='hospitalization',
            name='current_bed',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hospitalizations', to='facilities.hospitalbed'),
        ),
        migrations.AddField(
            model_name='observation',
            name='symptom',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='observations', to='clinical.symptomcatalog'),
        ),
        migrations.CreateModel(
            name='HospitalBedStay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('moved_in_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('moved_out_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('is_current', models.BooleanField(default=True)),
                ('bed', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stays', to='facilities.hospitalbed')),
                ('hospitalization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bed_stays', to='visits.hospitalization')),
                ('moved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hospital_bed_moves', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-moved_in_at'],
            },
        ),
        migrations.CreateModel(
            name='HospitalProcedurePlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('instructions', models.TextField(blank=True)),
                ('scheduled_at', models.DateTimeField()),
                ('status', models.CharField(choices=[('PLANNED', 'Planned'), ('IN_PROGRESS', 'In Progress'), ('DONE', 'Done'), ('CANCELED', 'Canceled')], default='PLANNED', max_length=16)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('completed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='completed_hospital_plans', to=settings.AUTH_USER_MODEL)),
                ('hospitalization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='procedure_plans', to='visits.hospitalization')),
            ],
            options={
                'ordering': ['scheduled_at', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='HospitalVitalRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('measured_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('temperature_c', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ('pulse_bpm', models.PositiveIntegerField(blank=True, null=True)),
                ('respiratory_rate', models.PositiveIntegerField(blank=True, null=True)),
                ('appetite_status', models.CharField(choices=[('NORMAL', 'Normal'), ('REDUCED', 'Reduced'), ('ABSENT', 'Absent')], default='NORMAL', max_length=16)),
                ('water_intake_ml', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('urine_output_ml', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('notes', models.TextField(blank=True)),
                ('hospitalization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vitals', to='visits.hospitalization')),
                ('recorded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_hospital_vitals', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-measured_at'],
            },
        ),
        migrations.CreateModel(
            name='MedicationAdministration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('scheduled_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('PLANNED', 'Planned'), ('GIVEN', 'Given'), ('SKIPPED', 'Skipped'), ('CANCELED', 'Canceled')], db_index=True, default='PLANNED', max_length=16)),
                ('dose_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('dose_unit', models.CharField(blank=True, max_length=32)),
                ('route', models.CharField(blank=True, max_length=64)),
                ('given_at', models.DateTimeField(blank=True, null=True)),
                ('deviation_note', models.TextField(blank=True)),
                ('quantity_written_off', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('write_off_note', models.CharField(blank=True, max_length=255)),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='medication_administrations', to='inventory.batch')),
                ('given_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='medication_administrations', to=settings.AUTH_USER_MODEL)),
                ('inventory_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='medication_administrations', to='inventory.inventoryitem')),
                ('prescription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='administrations', to='visits.prescription')),
            ],
            options={
                'ordering': ['scheduled_at', 'created_at'],
            },
        ),
    ]

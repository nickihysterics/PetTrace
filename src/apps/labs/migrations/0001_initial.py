# Сгенерировано Django 5.2.11 от 2026-02-13 16:02

import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContainerLabel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('label_value', models.CharField(max_length=255, unique=True)),
                ('printed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LabOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('status', models.CharField(choices=[('PLANNED', 'Planned'), ('COLLECTED', 'Collected'), ('IN_TRANSPORT', 'In Transport'), ('RECEIVED', 'Received'), ('IN_PROCESS', 'In Process'), ('DONE', 'Done'), ('REJECTED', 'Rejected'), ('CANCELED', 'Canceled')], db_index=True, default='PLANNED', max_length=16)),
                ('notes', models.TextField(blank=True)),
                ('ordered_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('sla_minutes', models.PositiveIntegerField(default=60)),
            ],
            options={
                'ordering': ['-ordered_at'],
                'permissions': [('approve_lab_result', 'Can approve lab result')],
            },
        ),
        migrations.CreateModel(
            name='LabResultValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('parameter_name', models.CharField(max_length=128)),
                ('value', models.CharField(max_length=128)),
                ('unit', models.CharField(blank=True, max_length=32)),
                ('reference_range', models.CharField(blank=True, max_length=120)),
                ('flag', models.CharField(choices=[('LOW', 'Low'), ('NORMAL', 'Normal'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='NORMAL', max_length=16)),
                ('comment', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['parameter_name'],
            },
        ),
        migrations.CreateModel(
            name='LabTest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=64)),
                ('name', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('PLANNED', 'Planned'), ('IN_PROCESS', 'In Process'), ('DONE', 'Done'), ('REJECTED', 'Rejected')], default='PLANNED', max_length=16)),
                ('specimen_type', models.CharField(max_length=64)),
                ('turnaround_minutes', models.PositiveIntegerField(default=30)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Specimen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('specimen_type', models.CharField(max_length=64)),
                ('status', models.CharField(choices=[('PLANNED', 'Planned'), ('COLLECTED', 'Collected'), ('IN_TRANSPORT', 'In Transport'), ('RECEIVED', 'Received'), ('IN_PROCESS', 'In Process'), ('DONE', 'Done'), ('REJECTED', 'Rejected')], db_index=True, default='PLANNED', max_length=16)),
                ('collected_at', models.DateTimeField(blank=True, null=True)),
                ('received_at', models.DateTimeField(blank=True, null=True)),
                ('in_process_at', models.DateTimeField(blank=True, null=True)),
                ('done_at', models.DateTimeField(blank=True, null=True)),
                ('collection_room', models.CharField(blank=True, max_length=64)),
                ('rejection_reason', models.CharField(blank=True, choices=[('HEMOLYZED', 'Hemolyzed'), ('INSUFFICIENT_VOLUME', 'Insufficient Volume'), ('CONTAMINATED', 'Contaminated'), ('EXPIRED', 'Expired'), ('OTHER', 'Other')], max_length=32)),
                ('rejection_note', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SpecimenEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('from_status', models.CharField(blank=True, max_length=16)),
                ('to_status', models.CharField(max_length=16)),
                ('location', models.CharField(blank=True, max_length=128)),
                ('notes', models.TextField(blank=True)),
                ('event_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'ordering': ['-event_at'],
            },
        ),
        migrations.CreateModel(
            name='SpecimenTube',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('quantity', models.PositiveIntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name='Tube',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=64, unique=True)),
                ('tube_type', models.CharField(choices=[('EDTA', 'EDTA'), ('SERUM', 'Serum'), ('URINE', 'Urine'), ('STOOL', 'Stool'), ('OTHER', 'Other')], max_length=16)),
                ('lot_number', models.CharField(max_length=64)),
                ('expires_at', models.DateField(blank=True, null=True)),
            ],
            options={
                'ordering': ['code'],
            },
        ),
    ]

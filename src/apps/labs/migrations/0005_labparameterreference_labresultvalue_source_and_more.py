# Сгенерировано Django 5.2.11 от 2026-02-13 23:30

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labs', '0004_labresultvalue_approval_note_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LabParameterReference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('parameter_name', models.CharField(max_length=128)),
                ('species', models.CharField(blank=True, choices=[('DOG', 'Dog'), ('CAT', 'Cat'), ('RABBIT', 'Rabbit'), ('BIRD', 'Bird'), ('OTHER', 'Other')], max_length=16)),
                ('min_age_months', models.PositiveIntegerField(blank=True, null=True)),
                ('max_age_months', models.PositiveIntegerField(blank=True, null=True)),
                ('unit', models.CharField(blank=True, max_length=32)),
                ('reference_low', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ('reference_high', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ('critical_low', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ('critical_high', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['parameter_name', 'species', 'min_age_months'],
            },
        ),
        migrations.AddField(
            model_name='labresultvalue',
            name='source',
            field=models.CharField(default='MANUAL', max_length=32),
        ),
        migrations.AddField(
            model_name='labresultvalue',
            name='parameter_reference',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='results', to='labs.labparameterreference'),
        ),
        migrations.CreateModel(
            name='SpecimenRecollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('reason', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('REQUESTED', 'Requested'), ('CREATED', 'Created'), ('COLLECTED', 'Collected'), ('CANCELED', 'Canceled')], default='REQUESTED', max_length=16)),
                ('requested_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('note', models.TextField(blank=True)),
                ('original_specimen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recollection_requests', to='labs.specimen')),
                ('recollected_specimen', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recollection_parent', to='labs.specimen')),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='requested_recollections', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-requested_at'],
            },
        ),
    ]

# Сгенерировано Django 5.2.11 от 2026-02-13 16:32

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owners', '0001_initial'),
        ('pets', '0001_initial'),
        ('visits', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('from_status', models.CharField(blank=True, max_length=16)),
                ('to_status', models.CharField(max_length=16)),
                ('notes', models.TextField(blank=True)),
                ('event_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='visits.visit')),
            ],
            options={
                'ordering': ['-event_at'],
            },
        ),
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('service_type', models.CharField(blank=True, max_length=128)),
                ('room', models.CharField(blank=True, max_length=64)),
                ('notes', models.TextField(blank=True)),
                ('start_at', models.DateTimeField(db_index=True)),
                ('end_at', models.DateTimeField(blank=True, null=True)),
                ('duration_minutes', models.PositiveIntegerField(default=30)),
                ('queue_number', models.PositiveIntegerField(blank=True, null=True)),
                ('checked_in_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('BOOKED', 'Booked'), ('CHECKED_IN', 'Checked In'), ('IN_ROOM', 'In Room'), ('COMPLETED', 'Completed'), ('CANCELED', 'Canceled'), ('NO_SHOW', 'No Show')], db_index=True, default='BOOKED', max_length=16)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_appointments', to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='appointments', to='owners.owner')),
                ('pet', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='appointments', to='pets.pet')),
                ('veterinarian', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointments', to=settings.AUTH_USER_MODEL)),
                ('visit', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointment', to='visits.visit')),
            ],
            options={
                'ordering': ['start_at'],
                'indexes': [models.Index(fields=['status', 'start_at'], name='visits_appo_status_863b0a_idx'), models.Index(fields=['veterinarian', 'start_at'], name='visits_appo_veterin_76d108_idx')],
            },
        ),
    ]

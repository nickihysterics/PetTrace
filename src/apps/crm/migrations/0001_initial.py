# Сгенерировано Django 5.2.11 от 2026-02-13 18:51

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('owners', '0002_owner_preferred_branch'),
        ('pets', '0001_initial'),
        ('visits', '0002_visitevent_appointment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OwnerTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=64, unique=True)),
                ('color', models.CharField(blank=True, max_length=16)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CommunicationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('channel', models.CharField(choices=[('SMS', 'SMS'), ('EMAIL', 'Email'), ('PHONE', 'Phone'), ('TELEGRAM', 'Telegram'), ('IN_APP', 'In-App')], default='EMAIL', max_length=16)),
                ('direction', models.CharField(choices=[('OUTBOUND', 'Outbound'), ('INBOUND', 'Inbound')], default='OUTBOUND', max_length=16)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('SENT', 'Sent'), ('FAILED', 'Failed'), ('CANCELED', 'Canceled')], default='PENDING', max_length=16)),
                ('subject', models.CharField(blank=True, max_length=255)),
                ('body', models.TextField()),
                ('scheduled_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='communications', to='owners.owner')),
                ('pet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='communications', to='pets.pet')),
                ('sent_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_communications', to=settings.AUTH_USER_MODEL)),
                ('visit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='communications', to='visits.visit')),
            ],
            options={
                'ordering': ['-scheduled_at', '-created_at'],
                'permissions': [('dispatch_communication', 'Can dispatch communication')],
            },
        ),
        migrations.CreateModel(
            name='Reminder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('reminder_type', models.CharField(choices=[('VACCINATION', 'Vaccination'), ('FOLLOW_UP', 'Follow Up'), ('CHECKUP', 'Checkup'), ('OTHER', 'Other')], default='OTHER', max_length=16)),
                ('status', models.CharField(choices=[('DUE', 'Due'), ('SENT', 'Sent'), ('DISMISSED', 'Dismissed'), ('OVERDUE', 'Overdue')], default='DUE', max_length=16)),
                ('due_at', models.DateTimeField()),
                ('message', models.CharField(max_length=255)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reminders', to='owners.owner')),
                ('pet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reminders', to='pets.pet')),
                ('visit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reminders', to='visits.visit')),
            ],
            options={
                'ordering': ['status', 'due_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OwnerTagAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tag_assignments', to='owners.owner')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owner_assignments', to='crm.ownertag')),
            ],
            options={
                'ordering': ['owner', 'tag'],
                'unique_together': {('owner', 'tag')},
            },
        ),
    ]

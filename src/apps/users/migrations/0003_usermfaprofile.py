# Сгенерировано Django 5.2.11 от 2026-02-13 23:30

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_useraccessprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserMFAProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('secret_key', models.CharField(blank=True, max_length=64)),
                ('is_enabled', models.BooleanField(default=False)),
                ('backup_codes', models.JSONField(blank=True, default=list)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='mfa_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['user__email'],
            },
        ),
    ]

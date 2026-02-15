# Сгенерировано Django 5.2.11 от 2026-02-13 22:51

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facilities", "0001_initial"),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserAccessProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('limit_to_assigned_cabinets', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                ('allowed_branches', models.ManyToManyField(blank=True, related_name='access_profiles', to='facilities.branch')),
                ('allowed_cabinets', models.ManyToManyField(blank=True, related_name='access_profiles', to='facilities.cabinet')),
                ('home_branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='home_users', to='facilities.branch')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='access_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['user__email'],
            },
        ),
    ]

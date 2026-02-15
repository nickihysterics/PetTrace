# Сгенерировано Django 5.2.11 от 2026-02-13 16:02

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Owner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('first_name', models.CharField(max_length=120)),
                ('last_name', models.CharField(max_length=120)),
                ('phone', models.CharField(db_index=True, max_length=32)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('discount_percent', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('is_blacklisted', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.CreateModel(
            name='ConsentDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('consent_type', models.CharField(choices=[('PERSONAL_DATA', 'Personal Data'), ('SURGERY', 'Surgery'), ('ANESTHESIA', 'Anesthesia'), ('GENERAL', 'General')], max_length=32)),
                ('accepted_at', models.DateTimeField()),
                ('document_file', models.FileField(blank=True, upload_to='consents/')),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consents', to='owners.owner')),
            ],
            options={
                'ordering': ['-accepted_at'],
            },
        ),
    ]

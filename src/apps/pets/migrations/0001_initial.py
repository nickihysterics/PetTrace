# Сгенерировано Django 5.2.11 от 2026-02-13 16:02

import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('owners', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('species', models.CharField(choices=[('DOG', 'Dog'), ('CAT', 'Cat'), ('RABBIT', 'Rabbit'), ('BIRD', 'Bird'), ('OTHER', 'Other')], max_length=16)),
                ('breed', models.CharField(blank=True, max_length=120)),
                ('sex', models.CharField(choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('UNKNOWN', 'Unknown')], default='UNKNOWN', max_length=16)),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('weight_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('allergies', models.TextField(blank=True)),
                ('vaccination_notes', models.TextField(blank=True)),
                ('insurance_number', models.CharField(blank=True, max_length=64)),
                ('microchip_id', models.CharField(blank=True, db_index=True, max_length=15, null=True, unique=True, validators=[django.core.validators.RegexValidator(message='Microchip ID must contain exactly 15 digits.', regex='^\\d{15}$')])),
                ('qr_token', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('DECEASED', 'Deceased'), ('ARCHIVED', 'Archived')], default='ACTIVE', max_length=16)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pets', to='owners.owner')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PetAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('file', models.FileField(upload_to='pets/attachments/')),
                ('title', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('pet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='pets.pet')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pet',
            index=models.Index(fields=['name'], name='pets_pet_name_7b5b83_idx'),
        ),
        migrations.AddIndex(
            model_name='pet',
            index=models.Index(fields=['species', 'breed'], name='pets_pet_species_d5b52d_idx'),
        ),
    ]

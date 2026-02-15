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
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('sku', models.CharField(max_length=64, unique=True)),
                ('category', models.CharField(choices=[('MEDICINE', 'Medicine'), ('CONSUMABLE', 'Consumable'), ('LAB', 'Lab'), ('OTHER', 'Other')], default='OTHER', max_length=16)),
                ('unit', models.CharField(default='pcs', max_length=16)),
                ('min_stock', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Batch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('lot_number', models.CharField(max_length=64)),
                ('expires_at', models.DateField(blank=True, null=True)),
                ('quantity_received', models.DecimalField(decimal_places=2, max_digits=10)),
                ('quantity_available', models.DecimalField(decimal_places=2, max_digits=10)),
                ('supplier', models.CharField(blank=True, max_length=255)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batches', to='inventory.inventoryitem')),
            ],
            options={
                'ordering': ['expires_at', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('movement_type', models.CharField(choices=[('INBOUND', 'Inbound'), ('WRITE_OFF', 'Write Off'), ('ADJUSTMENT', 'Adjustment'), ('RESERVATION', 'Reservation'), ('RELEASE', 'Release')], max_length=16)),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('reference_type', models.CharField(blank=True, max_length=64)),
                ('reference_id', models.CharField(blank=True, max_length=64)),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movements', to='inventory.batch')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movements', to='inventory.inventoryitem')),
            ],
            options={
                'ordering': ['-created_at'],
                'permissions': [('write_off_stock', 'Can write off stock')],
            },
        ),
    ]

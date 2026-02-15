# Сгенерировано Django 5.2.11 от 2026-02-13 16:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_initial'),
        ('labs', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tube',
            name='inventory_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='lab_tubes', to='inventory.inventoryitem'),
        ),
    ]

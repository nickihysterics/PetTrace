# Сгенерировано Django 5.2.11 от 2026-02-13 16:46

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labs', '0003_tube_inventory_item'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='labresultvalue',
            name='approval_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='labresultvalue',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='labresultvalue',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_lab_results', to=settings.AUTH_USER_MODEL),
        ),
    ]

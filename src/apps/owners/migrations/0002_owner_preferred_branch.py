# Сгенерировано Django 5.2.11 от 2026-02-13 18:51

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facilities', '0001_initial'),
        ('owners', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='owner',
            name='preferred_branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='preferred_owners', to='facilities.branch'),
        ),
    ]

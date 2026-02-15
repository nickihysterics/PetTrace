# Сгенерировано Django 5.2.11 от 2026-02-13 16:02

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('labs', '0001_initial'),
        ('visits', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='laborder',
            name='ordered_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordered_lab_orders', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='laborder',
            name='visit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lab_orders', to='visits.visit'),
        ),
        migrations.AddField(
            model_name='labtest',
            name='lab_order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tests', to='labs.laborder'),
        ),
        migrations.AddField(
            model_name='labresultvalue',
            name='lab_test',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='result_values', to='labs.labtest'),
        ),
        migrations.AddField(
            model_name='specimen',
            name='collected_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='collected_specimens', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='specimen',
            name='lab_order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='specimens', to='labs.laborder'),
        ),
        migrations.AddField(
            model_name='containerlabel',
            name='specimen',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='label', to='labs.specimen'),
        ),
        migrations.AddField(
            model_name='specimenevent',
            name='actor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='specimenevent',
            name='specimen',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='labs.specimen'),
        ),
        migrations.AddField(
            model_name='specimentube',
            name='specimen',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='specimen_tubes', to='labs.specimen'),
        ),
        migrations.AddField(
            model_name='specimentube',
            name='tube',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='usage_records', to='labs.tube'),
        ),
        migrations.AlterUniqueTogether(
            name='labtest',
            unique_together={('lab_order', 'code')},
        ),
        migrations.AlterUniqueTogether(
            name='specimentube',
            unique_together={('specimen', 'tube')},
        ),
    ]

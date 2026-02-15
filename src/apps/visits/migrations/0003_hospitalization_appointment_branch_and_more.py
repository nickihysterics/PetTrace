# Сгенерировано Django 5.2.11 от 2026-02-13 18:51

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facilities', '0001_initial'),
        ('owners', '0002_owner_preferred_branch'),
        ('pets', '0001_initial'),
        ('visits', '0002_visitevent_appointment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Hospitalization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('status', models.CharField(choices=[('ADMITTED', 'Admitted'), ('UNDER_OBSERVATION', 'Under Observation'), ('CRITICAL', 'Critical'), ('DISCHARGED', 'Discharged'), ('CANCELED', 'Canceled')], db_index=True, default='ADMITTED', max_length=24)),
                ('admitted_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('discharged_at', models.DateTimeField(blank=True, null=True)),
                ('cage_number', models.CharField(blank=True, max_length=64)),
                ('care_plan', models.TextField(blank=True)),
                ('feeding_instructions', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-admitted_at'],
            },
        ),
        migrations.AddField(
            model_name='appointment',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointments', to='facilities.branch'),
        ),
        migrations.AddField(
            model_name='appointment',
            name='cabinet',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointments', to='facilities.cabinet'),
        ),
        migrations.AddField(
            model_name='visit',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='visits', to='facilities.branch'),
        ),
        migrations.AddField(
            model_name='visit',
            name='cabinet',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='visits', to='facilities.cabinet'),
        ),
        migrations.AddIndex(
            model_name='appointment',
            index=models.Index(fields=['branch', 'cabinet', 'start_at'], name='visits_appo_branch__00f3ac_idx'),
        ),
        migrations.AddIndex(
            model_name='visit',
            index=models.Index(fields=['branch', 'cabinet', 'scheduled_at'], name='visits_visi_branch__9f5f5b_idx'),
        ),
        migrations.AddField(
            model_name='hospitalization',
            name='branch',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='hospitalizations', to='facilities.branch'),
        ),
        migrations.AddField(
            model_name='hospitalization',
            name='cabinet',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hospitalizations', to='facilities.cabinet'),
        ),
        migrations.AddField(
            model_name='hospitalization',
            name='visit',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='hospitalization', to='visits.visit'),
        ),
    ]

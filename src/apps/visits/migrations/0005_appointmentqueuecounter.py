# Сгенерировано Django 5.2.11 от 2026-02-15 21:10

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("visits", "0004_appointment_service_diagnosis_catalog_item_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AppointmentQueueCounter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("queue_date", models.DateField(db_index=True)),
                ("last_number", models.PositiveIntegerField(default=0)),
                (
                    "veterinarian",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="appointment_queue_counters",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-queue_date", "veterinarian_id"],
            },
        ),
        migrations.AddConstraint(
            model_name="appointmentqueuecounter",
            constraint=models.UniqueConstraint(
                condition=models.Q(veterinarian__isnull=False),
                fields=("veterinarian", "queue_date"),
                name="visits_appointment_queue_counter_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="appointmentqueuecounter",
            constraint=models.UniqueConstraint(
                condition=models.Q(veterinarian__isnull=True),
                fields=("queue_date",),
                name="visits_appointment_queue_counter_unassigned_unique",
            ),
        ),
    ]

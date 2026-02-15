# Сгенерировано Django 5.2.11 от 2026-02-13 22:56

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pets', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pet',
            name='microchip_id',
            field=models.CharField(blank=True, db_index=True, max_length=15, null=True, unique=True, validators=[django.core.validators.RegexValidator(message='ID микрочипа должен содержать ровно 15 цифр.', regex='^\\d{15}$')]),
        ),
    ]

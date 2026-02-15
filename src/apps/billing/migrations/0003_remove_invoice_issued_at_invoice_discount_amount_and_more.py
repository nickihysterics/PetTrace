# Сгенерировано Django 5.2.11 от 2026-02-13 23:30

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_initial'),
        ('crm', '0001_initial'),
        ('owners', '0002_owner_preferred_branch'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoice',
            name='issued_at',
        ),
        migrations.AddField(
            model_name='invoice',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='invoice',
            name='discount_code',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='invoice',
            name='formed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='posted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invoiceline',
            name='is_void',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='invoiceline',
            name='void_reason',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('FORMED', 'Formed'), ('POSTED', 'Posted'), ('PAID', 'Paid'), ('CANCELED', 'Canceled')], default='DRAFT', max_length=16),
        ),
        migrations.CreateModel(
            name='DiscountRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('scope', models.CharField(choices=[('GLOBAL', 'Global'), ('OWNER', 'Owner'), ('OWNER_TAG', 'Owner Tag'), ('PROMO', 'Promo')], default='GLOBAL', max_length=16)),
                ('discount_type', models.CharField(choices=[('PERCENT', 'Percent'), ('FIXED', 'Fixed')], default='PERCENT', max_length=16)),
                ('value', models.DecimalField(decimal_places=2, max_digits=12)),
                ('promo_code', models.CharField(blank=True, db_index=True, max_length=64)),
                ('min_subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('auto_apply', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='discount_rules', to='owners.owner')),
                ('owner_tag', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='discount_rules', to='crm.ownertag')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='invoice',
            name='applied_discount_rule',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='applied_invoices', to='billing.discountrule'),
        ),
        migrations.CreateModel(
            name='PaymentAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('adjustment_type', models.CharField(choices=[('REFUND', 'Refund'), ('CORRECTION', 'Correction')], max_length=16)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('reason', models.CharField(max_length=255)),
                ('adjusted_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('external_reference', models.CharField(blank=True, max_length=128)),
                ('adjusted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_adjustments', to=settings.AUTH_USER_MODEL)),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='adjustments', to='billing.payment')),
            ],
            options={
                'ordering': ['-adjusted_at', '-created_at'],
            },
        ),
    ]

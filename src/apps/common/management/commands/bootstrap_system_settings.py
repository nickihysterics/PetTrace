from django.core.management.base import BaseCommand

from apps.common.models import FeatureFlag, SystemSetting


class Command(BaseCommand):
    help = "Создает или обновляет системные настройки и feature-флаги по умолчанию."

    def handle(self, *args, **options):
        default_settings = [
            {
                "key": "visit.auto_close_on_payment",
                "value_type": SystemSetting.ValueType.BOOLEAN,
                "value_text": "true",
                "description": "Автоматически закрывать завершенный визит при полной оплате счета",
            },
            {
                "key": "labs.sla_overdue_minutes",
                "value_type": SystemSetting.ValueType.INTEGER,
                "value_text": "15",
                "description": "Количество минут до пометки образца/лабораторного заказа как просроченного",
            },
            {
                "key": "audit.retention_days",
                "value_type": SystemSetting.ValueType.INTEGER,
                "value_text": "180",
                "description": "Период хранения записей аудита в днях",
            },
            {
                "key": "tenancy.mode",
                "value_type": SystemSetting.ValueType.STRING,
                "value_text": "single",
                "description": "Режим размещения: single или multi",
            },
            {
                "key": "auth.rate_limit_attempts",
                "value_type": SystemSetting.ValueType.INTEGER,
                "value_text": "10",
                "description": "Максимум попыток входа в рамках окна rate-limit",
            },
            {
                "key": "auth.rate_limit_window_seconds",
                "value_type": SystemSetting.ValueType.INTEGER,
                "value_text": "300",
                "description": "Длительность скользящего окна ограничения входа в секундах",
            },
            {
                "key": "billing.allow_overpayment",
                "value_type": SystemSetting.ValueType.BOOLEAN,
                "value_text": "false",
                "description": "Разрешать оплату сверх непогашенной суммы счета",
            },
        ]

        for payload in default_settings:
            setting, created = SystemSetting.objects.update_or_create(
                key=payload["key"],
                defaults=payload,
            )
            action = "создана" if created else "обновлена"
            self.stdout.write(self.style.SUCCESS(f"SystemSetting {setting.key}: {action}"))

        default_flags = [
            {
                "code": "hospitalization.enabled",
                "name": "Модуль стационара",
                "description": "Включает workflow стационарного лечения",
                "enabled": True,
            },
            {
                "code": "inventory.enabled",
                "name": "Модуль склада",
                "description": "Включает учет остатков в рабочих процессах",
                "enabled": True,
            },
            {
                "code": "billing.enabled",
                "name": "Модуль финансов",
                "description": "Включает workflow счетов и оплат",
                "enabled": True,
            },
            {
                "code": "documents.pdf_generation",
                "name": "Генерация PDF",
                "description": "Включает рендеринг шаблонов документов в PDF",
                "enabled": True,
            },
            {
                "code": "security.mfa",
                "name": "Поддержка MFA",
                "description": "Включает OTP-эндпоинты для многофакторной аутентификации",
                "enabled": False,
            },
        ]

        for payload in default_flags:
            flag, created = FeatureFlag.objects.update_or_create(
                code=payload["code"],
                defaults=payload,
            )
            action = "создан" if created else "обновлен"
            self.stdout.write(self.style.SUCCESS(f"FeatureFlag {flag.code}: {action}"))

from django.core.management.base import BaseCommand

from apps.reports.tasks import warm_reports_cache


class Command(BaseCommand):
    help = "Предварительно рассчитывает отчеты и сохраняет их в кеш."

    def handle(self, *args, **options):
        result = warm_reports_cache()
        message = (
            "Кеш отчетов прогрет: "
            f"периоды={result['windows']}, "
            f"отчеты={result['reports']}, "
            f"записи={result['entries']}"
        )
        self.stdout.write(
            self.style.SUCCESS(message)
        )

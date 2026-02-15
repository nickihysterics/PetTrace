from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.utils import timezone


class Command(BaseCommand):
    help = "Создает логический бэкап (dumpdata + архив media)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default="backups",
            help="Каталог для файлов бэкапа",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"]).resolve()
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        target_dir = output_dir / f"backup_{timestamp}"
        target_dir.mkdir(parents=True, exist_ok=True)

        dump_path = target_dir / "db_dump.json"
        with dump_path.open("w", encoding="utf-8") as dump_file:
            call_command(
                "dumpdata",
                "--exclude=contenttypes",
                "--exclude=auth.permission",
                stdout=dump_file,
            )

        media_root = Path(settings.MEDIA_ROOT)
        media_archive_path = target_dir / "media"
        if media_root.exists():
            shutil.make_archive(str(media_archive_path), "zip", root_dir=media_root)

        self.stdout.write(self.style.SUCCESS(f"Бэкап создан: {target_dir}"))

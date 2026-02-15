from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Восстанавливает логический бэкап (loaddata + опциональный архив media)."

    def add_arguments(self, parser):
        parser.add_argument("--dump-file", required=True, help="Путь к db_dump.json")
        parser.add_argument("--media-archive", default="", help="Опциональный путь к media.zip")
        parser.add_argument(
            "--flush",
            action="store_true",
            default=False,
            help="Очистить БД перед восстановлением",
        )

    def handle(self, *args, **options):
        dump_file = Path(options["dump_file"]).resolve()
        if not dump_file.exists():
            self.stderr.write(self.style.ERROR(f"Файл дампа не найден: {dump_file}"))
            return

        if options["flush"]:
            call_command("flush", "--noinput")

        call_command("loaddata", str(dump_file))

        media_archive = options["media_archive"]
        if media_archive:
            archive_path = Path(media_archive).resolve()
            if archive_path.exists():
                media_root = Path(settings.MEDIA_ROOT)
                media_root.mkdir(parents=True, exist_ok=True)
                shutil.unpack_archive(str(archive_path), extract_dir=str(media_root))

        self.stdout.write(self.style.SUCCESS("Восстановление завершено"))

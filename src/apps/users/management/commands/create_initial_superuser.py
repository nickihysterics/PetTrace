import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Создает суперпользователя по умолчанию, если он отсутствует."

    def handle(self, *args, **options):
        email = os.getenv("SUPERUSER_EMAIL")
        password = os.getenv("SUPERUSER_PASSWORD")

        if not email or not password:
            self.stdout.write("SUPERUSER_EMAIL или SUPERUSER_PASSWORD не заданы; пропуск")
            return

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            self.stdout.write(f"Суперпользователь '{email}' уже существует")
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Суперпользователь '{email}' создан"))

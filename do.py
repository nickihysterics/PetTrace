#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DEMO_USERS_SHELL = (
    "from django.contrib.auth import get_user_model; "
    "User=get_user_model(); "
    "print('\\n'.join("
    "User.objects.filter(email__in=["
    "'registrar@pettrace.local',"
    "'vet@pettrace.local',"
    "'assistant@pettrace.local',"
    "'lab@pettrace.local',"
    "'inventory@pettrace.local',"
    "'cashier@pettrace.local'"
    "]).order_by('email').values_list('email', flat=True)"
    "))"
)

METRICS_SHELL = (
    "from apps.owners.models import Owner; "
    "from apps.pets.models import Pet; "
    "from apps.visits.models import Visit, Appointment; "
    "from apps.labs.models import LabOrder; "
    "from apps.billing.models import Invoice, Payment; "
    "from apps.tasks.models import Task; "
    "print('owners', Owner.objects.count()); "
    "print('pets', Pet.objects.count()); "
    "print('visits_total', Visit.objects.count()); "
    "print('visits_closed', Visit.objects.filter(status=Visit.VisitStatus.CLOSED).count()); "
    "print('visits_completed', Visit.objects.filter(status=Visit.VisitStatus.COMPLETED).count()); "
    "print('visits_in_progress', Visit.objects.filter(status=Visit.VisitStatus.IN_PROGRESS).count()); "
    "print('appointments_completed', "
    "Appointment.objects.filter(status=Appointment.AppointmentStatus.COMPLETED).count()); "
    "print('lab_done', LabOrder.objects.filter(status=LabOrder.LabOrderStatus.DONE).count()); "
    "print('invoices_paid', Invoice.objects.filter(status=Invoice.InvoiceStatus.PAID).count()); "
    "print('payments_total', Payment.objects.count()); "
    "print('tasks_total', Task.objects.count())"
)


def run(cmd: list[str], *, dry_run: bool = False) -> None:
    print(f"+ {' '.join(cmd)}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=ROOT, check=True)


def compose(*args: str) -> list[str]:
    return ["docker", "compose", *args]


def web_manage(*args: str) -> list[str]:
    return compose("run", "--rm", "web", "python", "manage.py", *args)


def ensure_env(*, force: bool = False, dry_run: bool = False) -> None:
    env_path = ROOT / ".env"
    env_example_path = ROOT / ".env.example"
    if not env_example_path.exists():
        raise FileNotFoundError(f"Файл не найден: {env_example_path}")

    if env_path.exists() and not force:
        print(f"Файл .env уже существует: {env_path}")
        return

    if dry_run:
        print(f"+ copy {env_example_path} -> {env_path}")
        return

    shutil.copyfile(env_example_path, env_path)
    print(f"Создан .env из .env.example: {env_path}")


def cmd_prepare(args: argparse.Namespace) -> None:
    ensure_env(force=args.force_env, dry_run=args.dry_run)


def cmd_up(args: argparse.Namespace) -> None:
    command = compose("up", "-d")
    if args.build:
        command.append("--build")
    run(command, dry_run=args.dry_run)


def cmd_bootstrap(args: argparse.Namespace) -> None:
    commands = [
        web_manage("migrate", "--noinput"),
        web_manage("bootstrap_rbac"),
        web_manage("bootstrap_facilities"),
        web_manage("bootstrap_system_settings"),
        web_manage("create_initial_superuser"),
    ]
    for command in commands:
        run(command, dry_run=args.dry_run)


def cmd_seed_demo(args: argparse.Namespace) -> None:
    manage_args = ["seed_demo_data"]
    if args.reset:
        manage_args.append("--reset")
    manage_args.extend(["--bulk-cases", str(args.bulk_cases), "--days", str(args.days)])
    run(web_manage(*manage_args), dry_run=args.dry_run)


def cmd_demo_users(args: argparse.Namespace) -> None:
    run(web_manage("shell", "-c", DEMO_USERS_SHELL), dry_run=args.dry_run)


def cmd_metrics(args: argparse.Namespace) -> None:
    run(web_manage("shell", "-c", METRICS_SHELL), dry_run=args.dry_run)


def cmd_qa(args: argparse.Namespace) -> None:
    commands = [
        compose("run", "--rm", "web", "ruff", "check", "."),
        web_manage("test", "--noinput"),
    ]
    for command in commands:
        run(command, dry_run=args.dry_run)


def cmd_down(args: argparse.Namespace) -> None:
    run(compose("down"), dry_run=args.dry_run)


def cmd_all(args: argparse.Namespace) -> None:
    ensure_env(force=args.force_env, dry_run=args.dry_run)

    up_args = argparse.Namespace(build=args.build, dry_run=args.dry_run)
    cmd_up(up_args)

    stage_args = argparse.Namespace(dry_run=args.dry_run)
    cmd_bootstrap(stage_args)

    seed_args = argparse.Namespace(
        reset=args.reset,
        bulk_cases=args.bulk_cases,
        days=args.days,
        dry_run=args.dry_run,
    )
    cmd_seed_demo(seed_args)

    cmd_demo_users(stage_args)
    cmd_metrics(stage_args)

    if args.with_qa:
        cmd_qa(stage_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Скрипт-помощник PetTrace для типовых Docker-сценариев (как в демо-ноутбуке)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Создать .env из .env.example, если файла нет.")
    prepare.add_argument("--force-env", action="store_true", help="Перезаписать существующий .env.")
    prepare.add_argument("--dry-run", action="store_true", help="Показать команды без выполнения.")
    prepare.set_defaults(func=cmd_prepare)

    up = subparsers.add_parser("up", help="Запустить сервисы docker compose.")
    up.add_argument(
        "--no-build",
        action="store_false",
        dest="build",
        help="Запустить docker compose up без --build.",
    )
    up.set_defaults(build=True)
    up.add_argument("--dry-run", action="store_true", help="Показать команды без выполнения.")
    up.set_defaults(func=cmd_up)

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help=(
            "Выполнить migrate/bootstrap_rbac/bootstrap_facilities/"
            "bootstrap_system_settings/create_initial_superuser."
        ),
    )
    bootstrap.add_argument("--dry-run", action="store_true", help="Показать команды без выполнения.")
    bootstrap.set_defaults(func=cmd_bootstrap)

    seed_demo = subparsers.add_parser("seed-demo", help="Заполнить базу демо-данными.")
    seed_demo.add_argument("--bulk-cases", type=int, default=240, help="Количество bulk-кейсов.")
    seed_demo.add_argument("--days", type=int, default=120, help="Распределить кейсы на N дней.")
    seed_demo.add_argument(
        "--no-reset",
        action="store_false",
        dest="reset",
        help="Не очищать предыдущие демо-данные.",
    )
    seed_demo.add_argument("--dry-run", action="store_true", help="Показать команды без выполнения.")
    seed_demo.set_defaults(func=cmd_seed_demo, reset=True)

    demo_users = subparsers.add_parser("demo-users", help="Вывести демо-пользователей из БД.")
    demo_users.add_argument("--dry-run", action="store_true", help="Показать команды без выполнения.")
    demo_users.set_defaults(func=cmd_demo_users)

    metrics = subparsers.add_parser("metrics", help="Вывести демо-метрики из БД.")
    metrics.add_argument("--dry-run", action="store_true", help="Показать команды без выполнения.")
    metrics.set_defaults(func=cmd_metrics)

    qa = subparsers.add_parser("qa", help="Запустить ruff и django-тесты в docker.")
    qa.add_argument("--dry-run", action="store_true", help="Показать команды без выполнения.")
    qa.set_defaults(func=cmd_qa)

    down = subparsers.add_parser("down", help="Остановить сервисы docker compose.")
    down.add_argument("--dry-run", action="store_true", help="Показать команды без выполнения.")
    down.set_defaults(func=cmd_down)

    all_in_one = subparsers.add_parser(
        "all",
        help=(
            "Полный сценарий как в ноутбуке: "
            "prepare -> up -> bootstrap -> seed-demo -> demo-users -> metrics."
        ),
    )
    all_in_one.add_argument("--force-env", action="store_true", help="Перезаписать существующий .env.")
    all_in_one.add_argument(
        "--no-build",
        action="store_false",
        dest="build",
        help="Запустить docker compose up без --build.",
    )
    all_in_one.set_defaults(build=True)
    all_in_one.add_argument("--bulk-cases", type=int, default=240, help="Количество bulk-кейсов.")
    all_in_one.add_argument("--days", type=int, default=120, help="Распределить кейсы на N дней.")
    all_in_one.add_argument(
        "--no-reset",
        action="store_false",
        dest="reset",
        help="Не очищать предыдущие демо-данные.",
    )
    all_in_one.add_argument("--with-qa", action="store_true", help="Запустить QA-этап в конце.")
    all_in_one.add_argument("--dry-run", action="store_true", help="Показать команды без выполнения.")
    all_in_one.set_defaults(func=cmd_all, reset=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

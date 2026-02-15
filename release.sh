#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

BUILD=true
RUN_LINT=true
RUN_TESTS=true
RUN_SMOKE=true
WITH_DEMO_SEED=false
BULK_CASES=240
DAYS=120
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health/}"
PROFILE="${COMPOSE_PROFILE:-prod}"
DRY_RUN=false

usage() {
  cat <<'EOF'
Скрипт финальной проверки и подготовки релизного окружения PetTrace.

Использование:
  ./release.sh [опции]

Опции:
  --no-build          Не выполнять сборку образов при docker compose up.
  --skip-lint         Пропустить ruff check.
  --skip-tests        Пропустить django-тесты.
  --skip-smoke        Пропустить smoke-проверку /health/.
  --with-demo-seed    Заполнить БД демо-данными (seed_demo_data --reset).
  --bulk-cases N      Количество кейсов для демо-сидинга (по умолчанию: 240).
  --days N            Распределение демо-кейсов по дням (по умолчанию: 120).
  --health-url URL    URL для smoke-проверки (по умолчанию: http://localhost:8000/health/).
  --profile NAME      Профиль docker compose (по умолчанию: prod).
  --dry-run           Показать команды без выполнения.
  -h, --help          Показать эту справку.
EOF
}

log_step() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

fail() {
  printf 'Ошибка: %s\n' "$1" >&2
  exit 1
}

run() {
  printf '+'
  for arg in "$@"; do
    printf ' %q' "$arg"
  done
  printf '\n'

  if [[ "$DRY_RUN" == true ]]; then
    return 0
  fi

  "$@"
}

run_compose() {
  run docker compose "$@"
}

run_manage() {
  run docker compose exec -T web python manage.py "$@"
}

run_web_cmd() {
  run docker compose exec -T web "$@"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-build)
        BUILD=false
        ;;
      --skip-lint)
        RUN_LINT=false
        ;;
      --skip-tests)
        RUN_TESTS=false
        ;;
      --skip-smoke)
        RUN_SMOKE=false
        ;;
      --with-demo-seed)
        WITH_DEMO_SEED=true
        ;;
      --bulk-cases)
        shift
        [[ $# -gt 0 ]] || fail "Для --bulk-cases нужно передать число."
        BULK_CASES="$1"
        [[ "$BULK_CASES" =~ ^[0-9]+$ ]] || fail "--bulk-cases должен быть целым числом."
        ;;
      --days)
        shift
        [[ $# -gt 0 ]] || fail "Для --days нужно передать число."
        DAYS="$1"
        [[ "$DAYS" =~ ^[0-9]+$ ]] || fail "--days должен быть целым числом."
        ;;
      --health-url)
        shift
        [[ $# -gt 0 ]] || fail "Для --health-url нужно передать URL."
        HEALTH_URL="$1"
        ;;
      --profile)
        shift
        [[ $# -gt 0 ]] || fail "Для --profile нужно передать имя профиля."
        PROFILE="$1"
        ;;
      --dry-run)
        DRY_RUN=true
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail "Неизвестный аргумент: $1"
        ;;
    esac
    shift
  done
}

check_prerequisites() {
  command -v docker >/dev/null 2>&1 || fail "Не найден docker. Установите Docker Desktop/Engine."
  if [[ "$RUN_SMOKE" == true ]]; then
    command -v curl >/dev/null 2>&1 || fail "Не найден curl для smoke-проверки."
  fi

  if [[ ! -f .env ]]; then
    fail "Не найден .env. Создайте его из .env.example и заполните переменные."
  fi
}

smoke_check() {
  if [[ "$RUN_SMOKE" == false ]]; then
    return 0
  fi
  if [[ "$DRY_RUN" == true ]]; then
    printf 'Smoke-check пропущен: включен dry-run.\n'
    return 0
  fi

  log_step "Проверка доступности ${HEALTH_URL}"
  local attempts=30
  local delay_seconds=2

  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$HEALTH_URL" >/dev/null; then
      printf 'Smoke-check успешен: %s\n' "$HEALTH_URL"
      return 0
    fi
    sleep "$delay_seconds"
  done

  fail "Smoke-check не пройден: ${HEALTH_URL} недоступен."
}

main() {
  parse_args "$@"
  check_prerequisites

  log_step "Подъем сервисов Docker Compose (profile=${PROFILE})"
  if [[ "$BUILD" == true ]]; then
    run_compose --profile "$PROFILE" up -d --build
  else
    run_compose --profile "$PROFILE" up -d
  fi

  log_step "Инфраструктурный bootstrap Django"
  run_manage migrate --noinput
  run_manage bootstrap_rbac
  run_manage bootstrap_facilities
  run_manage bootstrap_system_settings
  run_manage create_initial_superuser
  run_manage collectstatic --noinput
  run_manage check

  if [[ "$WITH_DEMO_SEED" == true ]]; then
    log_step "Заполнение базы демо-данными"
    run_manage seed_demo_data --reset --bulk-cases "$BULK_CASES" --days "$DAYS"
  fi

  if [[ "$RUN_LINT" == true ]]; then
    log_step "Проверка code style (ruff)"
    run_web_cmd ruff check .
  fi

  if [[ "$RUN_TESTS" == true ]]; then
    log_step "Запуск автотестов"
    run_manage test apps --noinput
  fi

  log_step "Статус сервисов"
  run_compose ps

  smoke_check

  log_step "Релизный прогон завершен успешно"
}

main "$@"

#!/bin/sh
set -eu

wait_for_postgres() {
  echo "Waiting for postgres ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
  until nc -z "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
}

fix_shared_volume_permissions() {
  for path in /app/staticfiles /app/media; do
    if [ -e "$path" ]; then
      chmod -R a+rX "$path" 2>/dev/null || true
    fi
  done
}

bootstrap_django() {
  python manage.py migrate --noinput
  python manage.py bootstrap_rbac
  python manage.py bootstrap_facilities
  python manage.py bootstrap_system_settings
  python manage.py create_initial_superuser
  python manage.py collectstatic --noinput
  fix_shared_volume_permissions
}

wait_for_postgres

if [ "${1:-}" = "gunicorn" ] || { [ "${1:-}" = "python" ] && [ "${2:-}" = "manage.py" ] && [ "${3:-}" = "runserver" ]; }; then
  bootstrap_django
fi

exec "$@"

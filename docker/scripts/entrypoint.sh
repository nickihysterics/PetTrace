#!/bin/sh
set -eu

wait_for_postgres() {
  echo "Waiting for postgres ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
  until nc -z "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
}

bootstrap_django() {
  python manage.py migrate --noinput
  python manage.py bootstrap_rbac
  python manage.py bootstrap_facilities
  python manage.py bootstrap_system_settings
  python manage.py create_initial_superuser
  python manage.py collectstatic --noinput
}

wait_for_postgres

if [ "${1:-}" = "gunicorn" ] || { [ "${1:-}" = "python" ] && [ "${2:-}" = "manage.py" ] && [ "${3:-}" = "runserver" ]; }; then
  bootstrap_django
fi

exec "$@"

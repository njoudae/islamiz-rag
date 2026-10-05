#!/bin/sh
# Prepares the application on every container start, then runs the web server.
set -eu

# Generate the application key once and keep it on the storage volume, so a
# fresh `docker compose up` needs no manual `key:generate` and sessions survive
# restarts. An APP_KEY supplied through the environment always wins.
if [ -z "${APP_KEY:-}" ]; then
    key_file=storage/app/private/app.key
    if [ ! -s "$key_file" ]; then
        php artisan key:generate --show --no-ansi > "$key_file"
        chmod 600 "$key_file"
    fi
    APP_KEY="$(cat "$key_file")"
    export APP_KEY
fi

php artisan db:ensure-schema --no-ansi
php artisan migrate --force --no-ansi
php artisan db:seed --force --no-ansi

# Optional synthetic history for the dashboards. Every row is flagged as demo
# and labelled in the admin area; remove it with `php artisan daleel:demo-data --purge`.
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    php artisan daleel:demo-data --if-missing --no-ansi
fi
php artisan optimize --no-ansi

exec "$@"

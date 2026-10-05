#!/bin/sh
# Starts the AI service on loopback, then the website on the port the host assigns.
set -eu

PORT="${PORT:-10000}"
export SERVER_NAME=":${PORT}"
export APP_URL="${APP_URL:-${RENDER_EXTERNAL_URL:-http://localhost:${PORT}}}"

# The two processes share one container, so the internal token only has to match between them.
AI_SERVICE_TOKEN="${AI_SERVICE_TOKEN:-$(php -r 'echo bin2hex(random_bytes(24));')}"
export AI_SERVICE_TOKEN
export INTERNAL_API_TOKEN="$AI_SERVICE_TOKEN"

# The disk is not kept between restarts, so the application key comes from a stable secret
# instead of a generated file. An APP_KEY supplied through the environment always wins.
if [ -z "${APP_KEY:-}" ] && [ -n "${APP_SECRET:-}" ]; then
    APP_KEY="$(php -r 'echo "base64:".base64_encode(hash("sha256", getenv("APP_SECRET"), true));')"
    export APP_KEY
fi

echo "[daleel] starting the AI service on 127.0.0.1:8000"
/opt/ai/bin/python -m uvicorn app.main:app --app-dir /srv/daleel/apps/api --host 127.0.0.1 --port 8000 --no-access-log &

echo "[daleel] starting the website on port ${PORT}"
cd /app
exec docker/entrypoint.sh frankenphp run --config /etc/frankenphp/Caddyfile --adapter caddyfile

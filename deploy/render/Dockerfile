# Daleel on one small host: the website and the AI service in a single container.
# For free hosting tiers (512 MB). Build context: repository root.
#
# The embedding model is not in this image: the question is embedded by the same model
# hosted on Cloudflare Workers AI (QUERY_EMBEDDING_BACKEND=cloudflare). The database is external.
# The normal local setup is docker-compose.yml, which this file does not affect.

FROM dunglas/frankenphp:1-php8.4 AS base
RUN install-php-extensions pdo_pgsql intl zip opcache pcntl bcmath
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
WORKDIR /app

# --- PHP dependencies (production only) -------------------------------------
FROM base AS vendor
COPY apps/site/composer.json apps/site/composer.lock ./
RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist --no-interaction --no-progress
COPY apps/site .
RUN composer dump-autoload --optimize --no-dev --no-interaction

# --- Frontend assets ---------------------------------------------------------
FROM node:22-alpine AS assets
WORKDIR /app
COPY apps/site/package.json apps/site/package-lock.json apps/site/.npmrc ./
RUN npm ci
COPY apps/site/vite.config.js ./
COPY apps/site/resources resources
RUN npm run build

# --- Runtime -----------------------------------------------------------------
FROM base AS runtime

ENV APP_ENV=production \
    APP_DEBUG=false \
    LOG_CHANNEL=stderr \
    DB_CONNECTION=pgsql \
    DB_SCHEMA=site \
    DB_SSLMODE=require \
    SESSION_DRIVER=database \
    CACHE_STORE=database \
    QUEUE_CONNECTION=sync \
    INERTIA_SSR_ENABLED=false \
    TRUSTED_PROXIES=* \
    AI_SERVICE_URL=http://127.0.0.1:8000 \
    QUERY_EMBEDDING_BACKEND=cloudflare \
    CONVERSATION_DB_PATH=/srv/daleel/data/conversations.sqlite3 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# The AI service without the local model stack (no PyTorch): it only needs the API, NumPy and OpenAI.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/ai \
    && /opt/ai/bin/pip install --no-cache-dir \
        "fastapi>=0.115,<1" "uvicorn>=0.32,<1" "pydantic-settings>=2.6,<3" "psycopg[binary]>=3.2,<4" \
        "httpx>=0.27,<1" "python-multipart>=0.0.20,<1" "numpy>=2.0,<3" "openai>=3.22,<4"

COPY artifacts/benchmark/final_30q_retrieval/production_index /srv/daleel/artifacts/benchmark/final_30q_retrieval/production_index
COPY prompts /srv/daleel/prompts
COPY apps/api/app /srv/daleel/apps/api/app

RUN cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
COPY apps/site/docker/php.ini "$PHP_INI_DIR/conf.d/zz-daleel.ini"
# Two small processes share 512 MB, so keep PHP's shared cache modest.
RUN echo "opcache.memory_consumption = 64" > "$PHP_INI_DIR/conf.d/zzz-small-host.ini"

# The stock binary carries a file capability (to bind ports below 1024). Hosts that forbid gaining
# privileges refuse to start such a binary as a non-root user; a plain copy drops the capability,
# which is not needed on a high port.
RUN cp /usr/local/bin/frankenphp /usr/local/bin/frankenphp.plain \
    && mv /usr/local/bin/frankenphp.plain /usr/local/bin/frankenphp

COPY --from=vendor /app /app
COPY --from=assets /app/public/build public/build
COPY deploy/render/start.sh /usr/local/bin/daleel-start

# Normalise line endings so the image also builds from a Windows checkout.
RUN sed -i 's/\r$//' docker/entrypoint.sh /usr/local/bin/daleel-start \
    && chmod +x docker/entrypoint.sh /usr/local/bin/daleel-start \
    && mkdir -p storage/app/private storage/framework/cache/data storage/framework/sessions storage/framework/views storage/logs bootstrap/cache /srv/daleel/data \
    && chown -R www-data:www-data storage bootstrap/cache /data/caddy /config/caddy /srv/daleel/data

USER www-data
EXPOSE 10000

CMD ["daleel-start"]

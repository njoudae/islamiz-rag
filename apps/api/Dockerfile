# Daleel AI service (FastAPI + E5 + Qwen reranker). Build context: repository root.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/models

WORKDIR /srv/daleel

# CPU-only PyTorch keeps the image several GB smaller than the default CUDA wheels.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install dependencies against a stub package so this layer is cached until pyproject.toml changes.
# The install is editable: the code keeps running from /srv/daleel/apps/api, which the service
# relies on to locate the repository-level artifacts/ directory.
COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN mkdir -p apps/api/app && touch apps/api/app/__init__.py \
    && pip install -e ./apps/api

COPY infra/schema.sql infra/schema.sql
COPY artifacts/corpus artifacts/corpus
COPY apps/api/app apps/api/app
COPY apps/api/docker apps/api/docker

RUN useradd --create-home --uid 10001 daleel \
    && mkdir -p /models artifacts \
    && chown -R daleel:daleel /models artifacts
USER daleel

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20m --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

CMD ["python", "apps/api/docker/start.py"]

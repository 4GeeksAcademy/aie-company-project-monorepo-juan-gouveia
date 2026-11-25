# Imagen de la cola de tareas (ticket #DEV-55): la usan los servicios celery-worker (el consumidor, un
# proceso aparte de la API) y flower (el monitor) de docker-compose.yml, con distinto comando.
#
# Se construye desde docker-compose.yml (raíz) con `context: ./services` (aplica services/.dockerignore:
# sin .env, pruebas ni entornos locales), porque el paquete depende de services/telemetry (las métricas del
# informe). Instala lo fijado en services/tasks/uv.lock, sin las pruebas. El entorno vive en /opt/venv,
# fuera de /repo, para que los bind mounts del código no lo tapen.

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    TZ=UTC

WORKDIR /repo/services/tasks

# 1. Dependencias de terceros, en una capa propia: solo se reinstalan si cambia uv.lock.
COPY telemetry/pyproject.toml /repo/services/telemetry/pyproject.toml
COPY tasks/pyproject.toml tasks/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-install-package brasaland-telemetry

# 2. Código: services/telemetry y services/tasks, instalados en modo editable. En desarrollo, los bind
#    mounts de docker-compose.yml los sustituyen por los del host (un reinicio del worker basta).
COPY telemetry/*.py /repo/services/telemetry/
COPY tasks/*.py ./
RUN uv sync --frozen --no-dev

# Usuario sin privilegios: el worker no necesita escribir en disco.
RUN useradd --create-home --uid 1000 brasaland \
    && chown -R brasaland:brasaland /repo /opt/venv
USER brasaland

# Por defecto, el worker de las dos colas. Flower cambia el comando en docker-compose.yml.
CMD ["celery", "-A", "brasaland_tasks.celery_app", "worker", "-Q", "default,dead_letter", "--loglevel=INFO"]

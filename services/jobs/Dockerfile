# Imagen del servicio nightly-scheduler (ticket #DEV-53): supercronic ejecuta cada noche
# scripts/nightly_export.py según scripts/nightly_export.crontab. El script exporta la telemetría del día
# anterior a CSV, lanza el pipeline del Hito 6 como subproceso y registra la ejecución en ops.job_runs.
# Es un proceso aparte de la API: no comparte su contenedor ni su hilo.
#
# Se construye desde docker-compose.yml (raíz) con `context: ./services` (aplica services/.dockerignore:
# sin .env, pruebas ni entornos locales) y dos contextos adicionales: `data` (data/pipelines y
# data/process, de los que solo se copian los archivos necesarios) y `scripts`. Instala lo fijado en
# services/jobs/uv.lock, sin las pruebas. El entorno vive en /opt/venv, fuera de /repo, para que los
# bind mounts del código no lo tapen.

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

# supercronic: cron pensado para contenedores (sin root, log a stdout y reenvío de señales a los jobs).
# Versión y sha256 fijados: los publica GitHub en la release. TARGETARCH lo define BuildKit.
ARG SUPERCRONIC_VERSION=v0.2.51
ARG TARGETARCH
RUN set -eu; \
    arch="${TARGETARCH:-amd64}"; \
    case "$arch" in \
      amd64) sha256=cc232108374e8e2b537045f2d5eaa1229f619db314c3ba6a14d38b35dc0aa123 ;; \
      arm64) sha256=4ae22576a78223d8ccdf5f3b3660a5cbb5288416bf0ca96afc4a36d195932b94 ;; \
      *) echo "Arquitectura no soportada: $arch" >&2; exit 1 ;; \
    esac; \
    python -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])" \
      "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${arch}" \
      /usr/local/bin/supercronic; \
    echo "${sha256}  /usr/local/bin/supercronic" | sha256sum -c -; \
    chmod +x /usr/local/bin/supercronic

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    TZ=UTC

WORKDIR /repo/services/jobs

# 1. Dependencias de terceros, en una capa propia: solo se reinstalan si cambia algún uv.lock.
COPY --from=data process/pyproject.toml /repo/data/process/pyproject.toml
COPY --from=data pipelines/pyproject.toml pipelines/uv.lock /repo/data/pipelines/
COPY jobs/pyproject.toml jobs/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project \
      --no-install-package brasaland-pipelines --no-install-package brasaland-process

# 2. Código: data/process, data/pipelines, services/jobs y el script con su crontab, instalados en modo
#    editable. En desarrollo, los bind mounts de docker-compose.yml los sustituyen por los del host.
COPY --from=data process/__init__.py process/weekly_location_performance.py /repo/data/process/
COPY --from=data pipelines/*.py /repo/data/pipelines/
COPY jobs/*.py ./
COPY --from=scripts nightly_export.py nightly_export.crontab /repo/scripts/
RUN uv sync --frozen --no-dev

# Usuario sin privilegios. /repo/data recibe el CSV (data/raw/telemetry_exports) y las salidas del
# pipeline; ~/.prefect, los resultados cacheados del pipeline (un volumen en docker-compose.yml).
RUN useradd --create-home --uid 1000 brasaland \
    && mkdir -p /repo/data/raw/telemetry_exports /home/brasaland/.prefect \
    && chown -R brasaland:brasaland /repo /home/brasaland/.prefect /opt/venv
USER brasaland
WORKDIR /repo

# -passthrough-logs: la salida del script va tal cual al log del contenedor, con su propio formato.
CMD ["supercronic", "-passthrough-logs", "/repo/scripts/nightly_export.crontab"]

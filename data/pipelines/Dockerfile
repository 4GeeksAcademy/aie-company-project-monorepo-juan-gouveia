# Imagen del servicio reporting-pipeline: sirve el deployment del pipeline del Reporte Semanal de Costo y
# Merma por Local (`python pipeline.py --serve`) y ejecuta las corridas manuales que pide la API. La
# corrida programada la lanza cada noche el servicio nightly-scheduler (ticket #DEV-53).
#
# Se construye desde docker-compose.yml (raíz) con `context: ./data`. Instala lo fijado en
# data/pipelines/uv.lock, con Prefect (grupo orchestration) y sin las pruebas. El entorno vive en
# /opt/venv, fuera de /repo/data, para que el bind mount del código no lo tape.

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /repo/data/pipelines

# 1. Dependencias de terceros, en una capa propia: solo se reinstalan si cambia uv.lock.
COPY process/pyproject.toml /repo/data/process/pyproject.toml
COPY pipelines/pyproject.toml pipelines/uv.lock ./
RUN uv sync --frozen --no-dev --group orchestration --no-install-project --no-install-package brasaland-process

# 2. Código de data/process y data/pipelines, instalados en modo editable. En desarrollo, el bind mount
#    de docker-compose.yml los sustituye por los del host.
COPY process/__init__.py process/weekly_location_performance.py /repo/data/process/
COPY pipelines/*.py ./
RUN uv sync --frozen --no-dev --group orchestration

# Usuario sin privilegios. ~/.prefect guarda los resultados cacheados (un volumen en docker-compose.yml)
# y /repo/data, las salidas de cada corrida (raw/telemetry_events y eval/weekly_location_performance).
RUN useradd --create-home --uid 1000 brasaland \
    && mkdir -p /home/brasaland/.prefect \
    && chown -R brasaland:brasaland /repo /home/brasaland/.prefect /opt/venv
USER brasaland

CMD ["python", "pipeline.py", "--serve"]

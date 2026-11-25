# Imagen de desarrollo de la API de Brasaland (services/brasaland-api), con recarga en caliente.
#
# Se construye desde docker-compose.yml (raíz) con:
#   context: ./services
#   additional_contexts: shared: ./packages/shared, data: ./data
# Los paquetes locales packages/shared (brasaland-shared), data/process y data/pipelines están fuera de
# ./services, así que llegan por los contextos adicionales `shared` y `data`. La imagen reproduce la
# estructura del monorepo (/repo/...) para que las rutas relativas de los pyproject.toml sigan siendo
# válidas dentro del contenedor.

FROM python:3.12-slim

# uv desde la imagen oficial de Astral, con la misma versión que se usa en local (uv.lock y requirements.txt).
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

# Sin .pyc en los bind mounts del host y con la salida de Python sin búfer (logs al momento).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /repo/services/brasaland-api

# 1. Dependencias de terceros, en una capa propia: solo se reinstalan si cambia requirements.txt.
COPY requirements.txt /repo/services/requirements.txt
RUN uv pip install --system --no-cache -r /repo/services/requirements.txt

# 2. Paquete local brasaland-shared, editable: con el bind mount de packages/shared, sus cambios se ven sin reconstruir.
COPY --from=shared pyproject.toml /repo/packages/shared/pyproject.toml
COPY --from=shared brasaland_shared /repo/packages/shared/brasaland_shared
RUN uv pip install --system --no-cache --no-deps -e /repo/packages/shared

# 3. Paquete local brasaland-telemetry (services/telemetry, el pipeline del reporte técnico), editable.
#    Está dentro del contexto ./services; sus dependencias (pandas) ya llegaron con requirements.txt.
COPY telemetry/ /repo/services/telemetry/
RUN uv pip install --system --no-cache --no-deps -e /repo/services/telemetry

# 4. Pipeline de desempeño de negocio, editable: data/process (brasaland-process) y data/pipelines
#    (brasaland-pipelines) llegan por el contexto adicional `data`; services/reporting (brasaland-reporting,
#    los endpoints de /reporting) está en ./services. Sus dependencias (pandas, httpx) van en
#    requirements.txt. Prefect no: la API no lo importa; el flow corre en su propia imagen
#    (data/pipelines/Dockerfile, servicio reporting-pipeline).
COPY --from=data process/pyproject.toml process/__init__.py process/weekly_location_performance.py /repo/data/process/
COPY --from=data pipelines/pyproject.toml pipelines/*.py /repo/data/pipelines/
COPY reporting/ /repo/services/reporting/
RUN uv pip install --system --no-cache --no-deps -e /repo/data/process -e /repo/data/pipelines -e /repo/services/reporting

# 5. Cola de tareas (#DEV-55): services/tasks (brasaland-tasks), editable. La API solo usa su configuración
#    de Celery para encolar por nombre y leer el estado de Redis; el worker corre en su propio servicio.
#    Sus dependencias (celery, redis, kombu) van en requirements.txt.
COPY tasks/ /repo/services/tasks/
RUN uv pip install --system --no-cache --no-deps -e /repo/services/tasks

# 6. Código de la API. En desarrollo, el bind mount de docker-compose.yml lo sustituye por el del host.
COPY brasaland-api/ ./

# Usuario sin privilegios; storage/ guarda las bases TinyDB y debe poder escribirse.
RUN useradd --create-home --uid 1000 brasaland \
    && mkdir -p storage \
    && chown -R brasaland:brasaland /repo
USER brasaland

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

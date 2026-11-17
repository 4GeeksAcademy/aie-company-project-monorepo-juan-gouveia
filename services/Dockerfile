# Imagen de desarrollo de la API de Brasaland (services/brasaland-api), con recarga en caliente.
#
# Se construye desde docker-compose.yml (raíz) con:
#   context: ./services
#   additional_contexts: shared: ./packages/shared
# El paquete local packages/shared (brasaland-shared) está fuera de ./services, así que llega por el
# contexto adicional `shared`. La imagen reproduce la estructura del monorepo (/repo/...) para que la
# ruta ../../packages/shared de pyproject.toml siga siendo válida dentro del contenedor.

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

# 3. Código de la API. En desarrollo, el bind mount de docker-compose.yml lo sustituye por el del host.
COPY brasaland-api/ ./

# Usuario sin privilegios; storage/ guarda las bases TinyDB y debe poder escribirse.
RUN useradd --create-home --uid 1000 brasaland \
    && mkdir -p storage \
    && chown -R brasaland:brasaland /repo
USER brasaland

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

"""Punto de entrada de la API: crea la aplicación y registra los routers de cada dominio."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.core.config import API_PREFIX, get_settings
from app.core.errors import register_error_handlers
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.router import router as auth_router
from app.domains.incidents.manager_router import router as incident_manager_router
from app.domains.incidents.router import router as incidents_router
from app.domains.profiles.router import router as profiles_router
from app.domains.suppliers.dependencies import get_repository as get_supplier_repository
from app.domains.suppliers.router import router as suppliers_router
from app.domains.suppliers.seed import seed_if_empty
from app.domains.users.router import router as users_router

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Sin SECRET_KEY ni ACCESS_TOKEN_EXPIRE_MINUTES válidas, la API no arranca (ConfigError dice cuál falta).
    settings = get_settings()
    if not settings.email_enabled:
        # AUTH-03: sin clave de Resend la API funciona, pero no envía los enlaces de restablecimiento.
        logger.warning("Envío de correos desactivado: falta RESEND_API_KEY. /auth/forgot-password no enviará enlaces.")

    # El directorio de proveedores nunca arranca vacío: si la tabla no tiene datos, se siembra.
    # Se respeta dependency_overrides para que las pruebas usen su propia base temporal.
    repository = app.dependency_overrides.get(get_supplier_repository, get_supplier_repository)()
    result = seed_if_empty(repository)
    if result is not None:
        logger.info("Directorio de proveedores sembrado: %s proveedores insertados.", result.inserted)
    yield


app = FastAPI(title="Brasaland API", version="0.1.0", lifespan=lifespan)
register_error_handlers(app)
# Rutas con datos sensibles: todas exigen un token válido (AUTH-01). Sin token, 401.
PROTECTED = [Depends(get_current_user)]
app.include_router(incidents_router, prefix=API_PREFIX, dependencies=PROTECTED)
# Gestor de incidencias centralizado: mismo prefijo /incidents que el analizador del CSV.
app.include_router(incident_manager_router, prefix=API_PREFIX, dependencies=PROTECTED)
app.include_router(suppliers_router, prefix=API_PREFIX, dependencies=PROTECTED)
# Autenticación (AUTH-01): login, usuarios (solo credenciales) y perfiles. AUTH-03 añade a /auth el
# restablecimiento (público) y el cambio (protegido) de contraseña.
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(profiles_router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Comprueba que el servicio responde. Fuera de /api/v1 y pública: no expone datos (propuesta 3.4)."""
    return {"status": "ok"}

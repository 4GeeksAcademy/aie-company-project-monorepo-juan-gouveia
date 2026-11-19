"""CORS solo para un prefijo de rutas.

El backoffice llama a la API a través de su intermediario (BFF), en el mismo origen, así que la API
no necesita CORS. La excepción es la telemetría: el navegador envía los lotes directamente al
receptor (`POST /telemetry/events`, en el puerto de la API), también con `navigator.sendBeacon`. Este
middleware aplica `CORSMiddleware` solo a ese prefijo: el resto de rutas sigue sin aceptar llamadas
de otros orígenes.
"""

from collections.abc import Sequence

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


class PathScopedCORSMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        path_prefix: str,
        allow_origins: Sequence[str],
        allow_methods: Sequence[str],
        allow_headers: Sequence[str] = (),
    ) -> None:
        self.app = app
        self.path_prefix = path_prefix.rstrip("/")
        self.cors = CORSMiddleware(app, allow_origins=allow_origins, allow_methods=allow_methods, allow_headers=allow_headers)

    def _applies_to(self, path: str) -> bool:
        return path == self.path_prefix or path.startswith(self.path_prefix + "/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._applies_to(scope["path"]):
            await self.cors(scope, receive, send)
        else:
            await self.app(scope, receive, send)

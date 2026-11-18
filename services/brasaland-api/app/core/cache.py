"""Caché en memoria con TTL, para respuestas de lectura caras que se repiten.

Cada valor expira a los `ttl_seconds` de guardarse, y `invalidate()` la vacía cuando cambian los
datos de los que depende. Vive en el proceso de la API: con un solo proceso de uvicorn (el despliegue
actual, local y en Docker) todas las peticiones ven la misma caché. Con varios workers, cada uno
tendría su copia y una escritura solo limpiaría la suya; ese caso pide una caché compartida (Redis).

Solo debe guardar respuestas iguales para todos los usuarios autorizados: una clave compartida para
datos de un usuario sería una fuga de datos.
"""

import time
from collections.abc import Callable
from threading import Lock
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Diccionario clave → valor con expiración, seguro entre hilos.

    FastAPI ejecuta los endpoints síncronos en un pool de hilos, así que varias peticiones pueden
    leer, cargar e invalidar a la vez.
    """

    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic):
        if ttl_seconds <= 0:
            raise ValueError("El TTL debe ser mayor que 0: sin expiración, un dato obsoleto viviría para siempre.")
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[str, tuple[float, T]] = {}
        # Sube en cada invalidación. Una carga que empezó antes de una invalidación no guarda su
        # resultado: pudo leer la base antes de la escritura y lo guardaría ya obsoleto.
        self._generation = 0
        self._lock = Lock()

    def get(self, key: str) -> T | None:
        """El valor vigente de `key`, o None si no está o ya expiró (y entonces lo retira)."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if self._clock() >= expires_at:
                del self._entries[key]
                return None
            return value

    def get_or_load(self, key: str, load: Callable[[], T]) -> tuple[T, bool]:
        """Devuelve `(valor, acierto)`. Si no hay valor vigente, llama a `load()` y lo guarda.

        `load()` se ejecuta fuera del bloqueo: una consulta lenta no frena al resto de claves. Si dos
        peticiones fallan a la vez, las dos cargan; es aceptable con tan pocas claves.
        """
        cached = self.get(key)
        if cached is not None:
            return cached, True
        with self._lock:
            generation = self._generation
        value = load()
        with self._lock:
            if generation == self._generation:
                self._entries[key] = (self._clock() + self.ttl_seconds, value)
        return value, False

    def invalidate(self) -> None:
        """Vacía la caché: los datos de los que dependen sus valores han cambiado."""
        with self._lock:
            self._entries.clear()
            self._generation += 1

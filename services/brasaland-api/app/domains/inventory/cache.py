"""Caché de las dos lecturas caras del inventario (tarea de caching, decisión D1).

- `GET /inventory/products`: cada petición es una ida y vuelta a Supabase (~100 ms) y es la lectura
  más frecuente (lista de ingredientes, formulario de salida y panel de stock).
- `GET /inventory/orders`: devuelve el historial completo; con ~21 000 órdenes tarda ~1,3 s (consulta,
  modelos, validación y 5,8 MB de JSON).

Se guarda el JSON ya serializado, no los modelos: un acierto solo envía bytes.

Las dos respuestas son iguales para cualquier usuario autenticado (ninguna se filtra por usuario; el
backoffice marca las órdenes propias en el navegador), así que la clave no lleva el usuario. Si un
día se filtraran por usuario, la clave tendría que incluirlo.

Invalidación: cualquier escritura del inventario cambia el stock o el historial, así que
`service.py` llama a `invalidate_inventory()` justo después de cada `commit`. El TTL cubre lo que
esa invalidación no ve: escrituras de otros procesos (scripts de semilla, panel de Supabase).
"""

from app.core.cache import TTLCache

# Stock: se consulta justo antes de registrar una salida. Si alguien escribe fuera de la API, el
# usuario podría ver hasta 60 s un stock desactualizado; la salida no se rompe por eso, porque la
# API vuelve a calcular el stock en la base, con bloqueo, y responde 400 si no alcanza.
PRODUCTS_TTL_SECONDS = 60
# Historial: es de consulta y no decide nada. Que una orden escrita fuera de la API tarde hasta
# 5 minutos en aparecer no tiene consecuencias, y cada recarga evitada ahorra ~1,3 s.
ORDERS_TTL_SECONDS = 300

products_cache: TTLCache[bytes] = TTLCache(PRODUCTS_TTL_SECONDS)
orders_cache: TTLCache[bytes] = TTLCache(ORDERS_TTL_SECONDS)

ORDERS_KEY = "orders"


def products_key(country: str | None) -> str:
    """Una entrada por filtro: todos los mercados, CO o US."""
    return f"products:{country or 'all'}"


def invalidate_inventory() -> None:
    """Limpia las dos cachés: se llama tras cada escritura confirmada del inventario."""
    products_cache.invalidate()
    orders_cache.invalidate()

"""Genera `catalog.py` desde `docs/telemetry/event-schemas.json` (fuente única de verdad).

Uso: `uv run telemetry-catalog` (después de cambiar `event-schemas.json`).

Entran los 44 eventos, sea cual sea su emisor: el receptor guarda los del backoffice y, cuando exista,
los de la API. Para cada uno se copian la versión del esquema, las propiedades obligatorias, el
allowlist y las tres anotaciones de la tabla `telemetry_events` (`x-level`, `x-value` y `x-message`;
plan de telemetría, sección 14.2). La prueba `tests/telemetry/test_telemetry_catalog.py` falla si el
archivo generado no coincide con el JSON, así que no puede quedar desactualizado sin que se note.

Es una herramienta de desarrollo: lee `docs/`, que no forma parte de la imagen de la API. La API en
ejecución solo importa el `catalog.py` ya generado.
"""

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[5]
SCHEMAS_PATH = REPO_ROOT / "docs" / "telemetry" / "event-schemas.json"
OUTPUT_PATH = Path(__file__).with_name("catalog.py")

HEADER = '''"""ARCHIVO GENERADO por `app/domains/telemetry/generate_catalog.py` desde `docs/telemetry/event-schemas.json`.

No lo edites a mano: cambia el esquema y ejecuta `uv run telemetry-catalog`.

Los 44 eventos del plan, con la versión de su esquema, sus propiedades obligatorias, su allowlist y cómo
se guardan en `telemetry_events`: `level`, la propiedad que se copia en `value` (o `None`) y la plantilla
de `message` (plan de telemetría, sección 14.2).
"""

from typing import NamedTuple


class CatalogEntry(NamedTuple):
    version: str
    required: tuple[str, ...]
    allowed: tuple[str, ...]
    level: str
    value: str | None
    message: str


TELEMETRY_CATALOG: dict[str, CatalogEntry] = {
'''


def build_catalog(schemas: dict[str, Any]) -> dict[str, dict[str, Any]]:
    catalog = {}
    for event_type, event in schemas["definitions"]["events"].items():
        properties = event["properties"]["properties"]
        catalog[event_type] = {
            "version": event["properties"]["schemaVersion"]["const"],
            "required": tuple(properties["required"]),
            "allowed": tuple(properties["properties"]),
            "level": event["x-level"],
            "value": event["x-value"],
            "message": event["x-message"],
        }
    return catalog


def _literal(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, tuple):
        inner = ", ".join(_literal(item) for item in value)
        return f"({inner},)" if len(value) == 1 else f"({inner})"
    # json.dumps produce un literal de cadena válido en Python, con comillas dobles.
    return json.dumps(value, ensure_ascii=False)


def render_catalog(catalog: dict[str, dict[str, Any]]) -> str:
    lines = [HEADER.rstrip("\n")]
    for event_type, entry in catalog.items():
        lines.append(f"    {_literal(event_type)}: CatalogEntry(")
        for field, value in entry.items():
            lines.append(f"        {field}={_literal(value)},")
        lines.append("    ),")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> None:
    schemas = json.loads(SCHEMAS_PATH.read_text(encoding="utf-8"))
    catalog = build_catalog(schemas)
    OUTPUT_PATH.write_text(render_catalog(catalog), encoding="utf-8")
    print(f"{len(catalog)} eventos escritos en app/domains/telemetry/catalog.py")


if __name__ == "__main__":
    main()

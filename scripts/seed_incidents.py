"""Carga el histórico de incidencias del CSV del analizador en el gestor de incidencias.

Uso (desde la raíz del repositorio, con el entorno de la API, que tiene TinyDB):
    uv run --project services/brasaland-api python scripts/seed_incidents.py [ruta-al-csv]

Sin ruta, usa data/raw/incidents-brasaland.csv. Escribe en el archivo TinyDB de la API
(services/brasaland-api/storage/brasaland-db.json, o BRASALAND_DB_PATH si está definida).

Qué hace con cada fila del CSV:
1. La valida con las reglas del analizador (packages/shared, brasaland_shared.incidents.validation).
   Las filas inválidas no se insertan y se listan al final con su motivo (las etiquetas de las reglas
   son las del briefing del analizador, en inglés).
2. La transforma al modelo del gestor según el briefing: estado, categoría, título (primeros 120
   caracteres de la descripción), fecha (medianoche UTC), sede y origen `customer`.
3. La inserta solo si su `incident_id` no se cargó antes: ejecutarlo dos veces no duplica nada.
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# Con `uv run --project services/brasaland-api` los dos paquetes ya están instalados; las rutas
# permiten además ejecutar el script con el Python del entorno de la API desde cualquier carpeta.
sys.path.insert(0, str(REPO_ROOT / "packages" / "shared"))
sys.path.insert(0, str(REPO_ROOT / "services" / "brasaland-api"))

from brasaland_shared.incidents.exceptions import IncidentFileError  # noqa: E402
from brasaland_shared.incidents.validation import RULE_LABELS, load_records, validate_record  # noqa: E402

from app.core.storage import get_brasaland_db_path  # noqa: E402
from app.domains.incidents.incident_repository import IncidentRepository  # noqa: E402
from app.domains.incidents.models import (  # noqa: E402
    MAX_TITLE_LENGTH,
    Branch,
    IncidentCategory,
    IncidentOrigin,
    IncidentRecord,
    IncidentStatus,
)

DEFAULT_CSV = REPO_ROOT / "data" / "raw" / "incidents-brasaland.csv"

# --- Transformaciones CSV → modelo (briefing, "Datos históricos — seed desde CSV") -------------

STATUS_MAP = {
    "OPEN": IncidentStatus.OPEN,
    "CLOSED": IncidentStatus.RESOLVED,
    "DISCARDED": IncidentStatus.DISCARDED,
}

CATEGORY_MAP = {
    "CUSTOMER_COMPLAINT": IncidentCategory.CUSTOMER_COMPLAINT,
    "EQUIPMENT": IncidentCategory.EQUIPMENT_FAILURE,
    "SUPPLY": IncidentCategory.SUPPLY_ISSUE,
    "FOOD_QUALITY": IncidentCategory.CUSTOMER_COMPLAINT,
    "STAFF": IncidentCategory.STAFF_ISSUE,
}

BRANCH_MAP = {
    "COL-01": Branch.MEDELLIN_CENTRO,
    "COL-02": Branch.MEDELLIN_LAURELES,
    "COL-03": Branch.MEDELLIN_ENVIGADO,
    "COL-04": Branch.MEDELLIN_BELLO,
    "COL-05": Branch.MEDELLIN_ITAGUI,
    "COL-06": Branch.BOGOTA_CHAPINERO,
    "COL-07": Branch.BOGOTA_USAQUEN,
    "COL-08": Branch.CALI_GRANADA,
    "COL-09": Branch.BARRANQUILLA_NORTE,
    "COL-10": Branch.CENTRAL,
    "FLA-01": Branch.MIAMI_DORAL,
    "FLA-02": Branch.MIAMI_HIALEAH,
    "FLA-03": Branch.MIAMI_KENDALL,
    "FLA-04": Branch.ORLANDO_INTERNATIONAL,
}


class TransformError(ValueError):
    """La fila es válida para el analizador, pero no se puede convertir al modelo del gestor."""


@dataclass(frozen=True)
class SeedRow:
    source_id: str
    incident: IncidentRecord
    created_at: datetime


def transform(record: dict) -> SeedRow:
    """Convierte una fila válida del CSV al modelo del gestor; TransformError si no se puede."""
    title = record["description"][:MAX_TITLE_LENGTH].strip()
    if not title:
        raise TransformError("La descripción queda vacía al recortarla como título")
    if record["status"] not in STATUS_MAP:
        raise TransformError(f"Estado sin mapeo: {record['status'] or '(vacío)'}")
    if record["category"] not in CATEGORY_MAP:
        raise TransformError(f"Categoría sin mapeo: {record['category'] or '(vacía)'}")
    try:
        created_at = datetime.strptime(record["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise TransformError(f"Fecha no válida (se espera AAAA-MM-DD): {record['date'] or '(vacía)'}") from None

    incident = IncidentRecord(
        title=title,
        description=record["description"],
        category=CATEGORY_MAP[record["category"]],
        status=STATUS_MAP[record["status"]],
        origin=IncidentOrigin.CUSTOMER,
        # Sin location_id o sin mapeo, la sede es `central` (briefing).
        branch=BRANCH_MAP.get(record["location_id"], Branch.CENTRAL),
    )
    # Identificador para no duplicar: incident_id; si falta, título + fecha (briefing).
    source_id = record["incident_id"] or f"{title}|{created_at.isoformat()}"
    return SeedRow(source_id=source_id, incident=incident, created_at=created_at)


# --- Carga ------------------------------------------------------------------------------------


@dataclass
class SeedResult:
    total: int = 0
    inserted: int = 0
    skipped: int = 0
    # (incident_id, fila del archivo, motivos)
    invalid: list[tuple[str, int, list[str]]] = field(default_factory=list)


def seed(records: list[dict], repository: IncidentRepository) -> SeedResult:
    """Valida, transforma e inserta las filas; devuelve el recuento para el informe."""
    result = SeedResult(total=len(records))
    for index, record in enumerate(records):
        row = index + 2  # el encabezado es la fila 1
        broken = validate_record(record)
        if broken:
            result.invalid.append((record["incident_id"], row, [RULE_LABELS[rule] for rule in broken]))
            continue
        try:
            prepared = transform(record)
        except TransformError as error:
            result.invalid.append((record["incident_id"], row, [str(error)]))
            continue
        if repository.create_from_seed(prepared.source_id, prepared.incident, prepared.created_at) is None:
            result.skipped += 1
        else:
            result.inserted += 1
    return result


def format_report(result: SeedResult, source: Path, db_path: Path) -> str:
    lines = [
        f"Seed de incidencias desde {source.name}",
        f"  Filas leídas ..................... {result.total:>3}",
        f"  Insertadas ....................... {result.inserted:>3}",
        f"  Ya cargadas antes (omitidas) ..... {result.skipped:>3}",
        f"  Inválidas (no insertadas) ........ {len(result.invalid):>3}",
    ]
    for incident_id, row, reasons in result.invalid:
        lines.append(f"    - {incident_id or '(sin incident_id)'} (fila {row}): {'; '.join(reasons)}")
    # Ruta absoluta a propósito: confirma a quien lo ejecuta qué archivo se modificó
    # (BRASALAND_DB_PATH puede apuntar a cualquier sitio).
    lines.append(f"Base de datos: {db_path}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("Uso: python scripts/seed_incidents.py [ruta-al-csv]", file=sys.stderr)
        return 2
    source = Path(args[0]) if args else DEFAULT_CSV
    if not source.is_file():
        print(f"No se encontró el archivo: {source}", file=sys.stderr)
        return 1
    try:
        records = load_records(source)
    except IncidentFileError as error:
        print(f"No se puede cargar el archivo: {error}", file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        print("No se puede cargar el archivo: no está en UTF-8.", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"No se puede leer el archivo {source}: {error.strerror or error}.", file=sys.stderr)
        return 1

    db_path = get_brasaland_db_path()
    try:
        repository = IncidentRepository.from_path(db_path)
    except OSError as error:
        # Por ejemplo, sin permiso para crear la carpeta o el archivo.
        print(f"No se puede abrir la base de datos {db_path}: {error.strerror or error}.", file=sys.stderr)
        return 1
    try:
        result = seed(records, repository)
    except json.JSONDecodeError:
        # TinyDB lee el archivo en la primera operación, antes de escribir nada.
        print(
            f"La base de datos {db_path} no es un JSON válido y no se ha modificado. "
            "Revisa el archivo o restáuralo (si se borra, la API lo crea vacío al arrancar).",
            file=sys.stderr,
        )
        return 1
    except OSError as error:
        # Por ejemplo, disco lleno. Cada fila se inserta por separado, así que puede quedar una carga
        # parcial; incident_seed_log evita duplicados al repetir.
        print(
            f"No se pudo escribir en la base de datos {db_path}: {error.strerror or error}. "
            "Puede que se haya cargado una parte; al ejecutarlo de nuevo no se duplica nada.",
            file=sys.stderr,
        )
        return 1
    finally:
        repository.close()
    print(format_report(result, source, db_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())

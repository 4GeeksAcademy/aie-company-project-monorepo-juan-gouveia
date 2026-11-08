"""Validación del CSV de incidentes: columnas, valores permitidos, lectura y reglas de invalidez.

Es la fuente única de estas reglas. La usan el analizador, el seed del gestor de incidencias y la API.
"""

import csv
import io
from collections import Counter
from pathlib import Path

from brasaland_shared.incidents.exceptions import (
    EmptyFileError,
    InvalidEncodingError,
    MissingColumnsError,
    NoRecordsError,
)

FIELDS = [
    "incident_id",
    "date",
    "location_id",
    "category",
    "description",
    "status",
    "customer_id",
    "satisfaction_score",
    "reporter_id",
]

LOCATIONS = {f"COL-{n:02d}" for n in range(1, 11)} | {f"FLA-{n:02d}" for n in range(1, 5)}
CATEGORIES = ["CUSTOMER_COMPLAINT", "EQUIPMENT", "SUPPLY", "FOOD_QUALITY", "STAFF"]
STATUSES = ["OPEN", "CLOSED", "DISCARDED"]
MIN_DESCRIPTION_LENGTH = 5
MIN_SCORE, MAX_SCORE = 1, 5

# Reglas de invalidez en el orden del reporte: (clave, etiqueta).
# invalid_status no está en el briefing: evita que un estado desconocido cuente como válido.
RULES = [
    ("missing_location", "Missing location_id"),
    ("invalid_category", "Invalid or missing category"),
    ("empty_description", "Empty description"),
    ("missing_reporter", "Missing reporter_id"),
    ("invalid_status", "Invalid or missing status"),
    ("closed_without_score", "Closed case, no score"),
    ("score_out_of_range", "Score out of range"),
]
RULE_LABELS = dict(RULES)


def parse_records(text, source_name=None):
    """Convierte el texto de un CSV en registros con los campos sin espacios sobrantes."""
    reader = csv.DictReader(io.StringIO(text, newline=""))
    missing = [field for field in FIELDS if field not in (reader.fieldnames or [])]
    if missing:
        raise MissingColumnsError(missing, source_name)
    return [{field: (row[field] or "").strip() for field in FIELDS} for row in reader]


def load_records(path):
    """Lee un CSV del disco; utf-8-sig tolera el BOM que añaden algunas hojas de cálculo."""
    with open(path, encoding="utf-8-sig", newline="") as file:
        return parse_records(file.read(), Path(path).name)


def parse_upload(data):
    """Valida y lee un archivo subido (bytes); lanza un IncidentFileError si no se puede analizar."""
    if not data:
        raise EmptyFileError()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InvalidEncodingError() from None
    records = parse_records(text)
    if not records:
        raise NoRecordsError()
    return records


def parse_score(value):
    """Devuelve el puntaje como entero, o None si no es un entero sin signo (por ejemplo "4.5")."""
    return int(value) if value.isdigit() else None


def validate_record(record):
    """Devuelve la lista de reglas que incumple el registro; vacía si es válido."""
    broken = []
    if record["location_id"] not in LOCATIONS:
        broken.append("missing_location")
    if record["category"] not in CATEGORIES:
        broken.append("invalid_category")
    if len(record["description"]) < MIN_DESCRIPTION_LENGTH:
        broken.append("empty_description")
    if not record["reporter_id"]:
        broken.append("missing_reporter")
    if record["status"] not in STATUSES:
        broken.append("invalid_status")

    score = record["satisfaction_score"]
    if record["status"] == "CLOSED" and not score:
        broken.append("closed_without_score")
    if score:
        parsed = parse_score(score)
        if parsed is None or not MIN_SCORE <= parsed <= MAX_SCORE:
            broken.append("score_out_of_range")
    return broken


def split_records(records):
    """Separa válidos e inválidos y cuenta cada regla una vez por registro que la incumple.

    Cada inválido se devuelve como {incident_id, row, rules}; row es la fila del archivo,
    contando el encabezado como fila 1.
    """
    valid, invalid = [], []
    rule_counts = Counter()
    for index, record in enumerate(records):
        broken = validate_record(record)
        if broken:
            invalid.append({"incident_id": record["incident_id"], "row": index + 2, "rules": broken})
            rule_counts.update(broken)
        else:
            valid.append(record)
    return valid, invalid, rule_counts

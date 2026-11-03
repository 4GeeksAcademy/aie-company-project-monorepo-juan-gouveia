"""Reglas de validación y análisis de los reportes de incidentes de Brasaland.

Es la fuente de verdad de estas reglas: la usan la API y el script de consola
(scripts/incident-report/analyze.py). Por eso solo depende de la librería estándar.
"""

import csv
import io
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from app.domains.incidents.exceptions import (
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

SCORE_LABELS = {
    1: "Very dissatisfied",
    2: "Dissatisfied",
    3: "Neutral",
    4: "Satisfied",
    5: "Very satisfied",
}

EXPORT_COLUMNS = ["metric", "value", "percentage"]


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


def analyze(records):
    """Calcula las métricas del reporte; categorías, estados y puntajes salen solo de registros válidos."""
    valid, invalid, rule_counts = split_records(records)
    categories = Counter(record["category"] for record in valid)
    statuses = Counter(record["status"] for record in valid)

    closed = [record for record in valid if record["status"] == "CLOSED"]
    scores = [parse_score(record["satisfaction_score"]) for record in closed if record["satisfaction_score"]]
    score_counts = Counter(scores)

    return {
        "total": len(records),
        "valid": len(valid),
        "invalid": len(invalid),
        "rules": {key: rule_counts[key] for key, _ in RULES},
        "invalid_details": invalid,
        "categories": {code: categories[code] for code in CATEGORIES},
        "statuses": {code: statuses[code] for code in STATUSES},
        "closed_cases": len(closed),
        "scored_cases": len(scores),
        "scores": {score: score_counts[score] for score in range(MIN_SCORE, MAX_SCORE + 1)},
        # Decimal evita errores de coma flotante al redondear (por ejemplo 2.25 -> 2.3).
        "average_score": Decimal(sum(scores)) / Decimal(len(scores)) if scores else None,
    }


def percentage(part, whole):
    """Porcentaje con 1 decimal, redondeando hacia arriba en el empate; None si el total es 0."""
    if not whole:
        return None
    return (Decimal(part * 100) / Decimal(whole)).quantize(Decimal("0.1"), ROUND_HALF_UP)


def rounded_average(summary):
    """Promedio de satisfacción con 2 decimales, o None si no hay puntajes."""
    average = summary["average_score"]
    return None if average is None else average.quantize(Decimal("0.01"), ROUND_HALF_UP)


def build_export_rows(summary):
    """Una fila por métrica; las reglas salen siempre, aunque estén en 0, para que el esquema no cambie."""
    valid = summary["valid"]

    def row(metric, value, percent=None):
        return {"metric": metric, "value": value, "percentage": "" if percent is None else percent}

    rows = [
        row("total_records", summary["total"]),
        row("valid_records", valid, percentage(valid, summary["total"])),
        row("invalid_records", summary["invalid"], percentage(summary["invalid"], summary["total"])),
    ]
    rows += [row(f"invalid.{key}", count) for key, count in summary["rules"].items()]
    rows += [row(f"category.{code}", count, percentage(count, valid)) for code, count in summary["categories"].items()]
    rows += [row(f"status.{code}", count, percentage(count, valid)) for code, count in summary["statuses"].items()]

    average = rounded_average(summary)
    rows += [
        row("satisfaction.closed_cases", summary["closed_cases"]),
        row("satisfaction.scored_cases", summary["scored_cases"]),
        row("satisfaction.average", "" if average is None else average),
    ]
    rows += [
        row(f"satisfaction.score_{score}", count, percentage(count, summary["scored_cases"]))
        for score, count in summary["scores"].items()
    ]
    return rows


def export_csv_text(rows):
    """Devuelve las filas de exportación como texto CSV, con encabezado."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()

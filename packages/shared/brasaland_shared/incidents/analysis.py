"""Métricas del reporte de incidentes y su exportación a CSV, a partir de los registros validados."""

import csv
import io
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from brasaland_shared.incidents.validation import (
    CATEGORIES,
    MAX_SCORE,
    MIN_SCORE,
    RULES,
    STATUSES,
    parse_score,
    split_records,
)

SCORE_LABELS = {
    1: "Very dissatisfied",
    2: "Dissatisfied",
    3: "Neutral",
    4: "Satisfied",
    5: "Very satisfied",
}

EXPORT_COLUMNS = ["metric", "value", "percentage"]


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

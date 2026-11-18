"""Reglas del CSV de incidentes que usa el analizador de la API.

Las reglas no viven aquí: están en el paquete compartido `packages/shared` (`brasaland_shared`),
que también usan los scripts `scripts/incident-report/analyze.py` y `scripts/seed_incidents.py`.
Este módulo solo las reúne con los nombres que ya usaban el router, los esquemas y las pruebas.
"""

from brasaland_shared.incidents.analysis import (
    EXPORT_COLUMNS,
    SCORE_LABELS,
    analyze,
    build_export_rows,
    export_csv_text,
    percentage,
    rounded_average,
)
from brasaland_shared.incidents.validation import (
    CATEGORIES,
    FIELDS,
    LOCATIONS,
    MAX_SCORE,
    MIN_DESCRIPTION_LENGTH,
    MIN_SCORE,
    RULES,
    STATUSES,
    load_records,
    parse_records,
    parse_score,
    parse_upload,
    split_records,
    validate_record,
)

__all__ = [
    "CATEGORIES",
    "EXPORT_COLUMNS",
    "FIELDS",
    "LOCATIONS",
    "MAX_SCORE",
    "MIN_DESCRIPTION_LENGTH",
    "MIN_SCORE",
    "RULES",
    "SCORE_LABELS",
    "STATUSES",
    "analyze",
    "build_export_rows",
    "export_csv_text",
    "load_records",
    "parse_records",
    "parse_score",
    "parse_upload",
    "percentage",
    "rounded_average",
    "split_records",
    "validate_record",
]

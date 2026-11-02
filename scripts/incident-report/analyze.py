"""Procesador de reportes de incidentes de Brasaland.

Uso:
    python analyze.py <ruta-al-csv>

Si la ruta no existe desde la carpeta actual, se busca el mismo nombre en data/raw/.
"""

import csv
import sys
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
EXPORT_PATH = REPO_ROOT / "data" / "process" / "results.csv"
EXPORT_COLUMNS = ["metric", "value", "percentage"]
EXPORT_PROMPT = "¿Deseas exportar los resultados a CSV? [s / n]: "
YES_ANSWERS = {"s", "si", "sí", "y", "yes"}

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

# Reglas de invalidez en el orden del reporte: (clave, etiqueta de consola).
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

# Formato de consola: ancho de los separadores y columna donde terminan los puntos guía.
SEPARATOR = "=" * 60
LABEL_WIDTH = 36


def resolve_source(arg):
    """Devuelve la ruta del CSV: tal cual si existe; si no, el mismo nombre en data/raw/."""
    path = Path(arg)
    if path.is_file():
        return path
    fallback = RAW_DIR / path.name
    if fallback.is_file():
        return fallback
    raise FileNotFoundError(f"File not found: {arg} (also checked {fallback})")


def load_records(path):
    """Lee el CSV y devuelve una lista de diccionarios con los campos sin espacios sobrantes."""
    # utf-8-sig tolera el BOM que añaden algunas exportaciones de hojas de cálculo.
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = [field for field in FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing columns in {Path(path).name}: {', '.join(missing)}")
        return [{field: (row[field] or "").strip() for field in FIELDS} for row in reader]


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
    """Separa válidos e inválidos y cuenta cada regla una vez por registro que la incumple."""
    valid, invalid = [], []
    rule_counts = Counter()
    for record in records:
        broken = validate_record(record)
        if broken:
            invalid.append(record)
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


def dotted(label, value, indent=""):
    """Línea con puntos guía entre la etiqueta y el valor, que queda alineado a la derecha."""
    return f"{indent}{label} ".ljust(LABEL_WIDTH, ".") + f" {value:>3}"


def tree(items):
    """Dibuja una lista de (etiqueta, valor, sufijo) con conectores ├─ y └─."""
    lines = []
    for index, (label, value, suffix) in enumerate(items):
        connector = "└─" if index == len(items) - 1 else "├─"
        lines.append(dotted(label, value, f"  {connector} ") + suffix)
    return lines


def with_percentage(part, whole):
    """Sufijo de porcentaje alineado, por ejemplo "  (30.2%)" o "   (9.4%)"."""
    value = percentage(part, whole)
    text = "(n/a)" if value is None else f"({value}%)"
    return f"{text:>9}"


def format_report(summary, source_name):
    """Devuelve el resumen de consola con el formato del briefing."""
    valid = summary["valid"]
    lines = [
        SEPARATOR,
        "  BRASALAND — INCIDENT REPORT ANALYSIS",
        f"  Source file: {source_name}",
        SEPARATOR,
        "",
        dotted("TOTAL RECORDS IN FILE", summary["total"]),
        *tree([
            ("Valid records", valid, ""),
            ("Invalid / incomplete", summary["invalid"], ""),
        ]),
        "",
        "INVALID RECORDS BREAKDOWN",
    ]

    # Solo se listan las reglas con casos; un registro puede sumar en varias.
    broken_rules = [(label, summary["rules"][key], "") for key, label in RULES if summary["rules"][key]]
    lines += tree(broken_rules) if broken_rules else ["  No invalid records."]
    if sum(summary["rules"].values()) > summary["invalid"]:
        lines.append("  Note: some records break more than one rule, so counts exceed the invalid total.")

    lines += ["", "BREAKDOWN BY CATEGORY (valid records)"]
    lines += tree([(code, count, with_percentage(count, valid)) for code, count in summary["categories"].items()])

    lines += ["", "BREAKDOWN BY STATUS (valid records)"]
    lines += tree([(code, count, with_percentage(count, valid)) for code, count in summary["statuses"].items()])

    average = rounded_average(summary)
    lines += [
        "",
        "SATISFACTION INDEX (closed cases)",
        f"  Scored cases: {summary['scored_cases']} of {summary['closed_cases']}",
        f"  Average score: {'n/a' if average is None else average} / {MAX_SCORE:.2f}",
    ]
    lines += tree([
        (f"Score {score} ({SCORE_LABELS[score]})", count, "")
        for score, count in summary["scores"].items()
    ])

    lines += ["", SEPARATOR]
    return "\n".join(lines)


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


def export_csv(rows, path=EXPORT_PATH):
    """Escribe las filas en CSV, sobrescribiendo el archivo anterior, y devuelve la ruta."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def wants_export():
    """Pregunta si exportar; sin entrada disponible (EOF) responde que no."""
    try:
        answer = input(EXPORT_PROMPT)
    except EOFError:
        print()
        return False
    return answer.strip().lower() in YES_ANSWERS


def main(argv):
    if len(argv) != 1:
        print("Usage: python analyze.py <path-to-csv>", file=sys.stderr)
        return 1
    try:
        source = resolve_source(argv[0])
        records = load_records(source)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    # La consola de Windows usa cp1252 por defecto y no puede imprimir ├─ ni └─.
    sys.stdout.reconfigure(encoding="utf-8")
    summary = analyze(records)
    print(format_report(summary, source.name))

    if wants_export():
        path = export_csv(build_export_rows(summary))
        print(f"Results exported to {path}")
    else:
        print("Export skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

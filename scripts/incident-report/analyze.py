"""Procesador de reportes de incidentes de Brasaland.

Uso:
    python analyze.py <ruta-al-csv>

Si la ruta no existe desde la carpeta actual, se busca el mismo nombre en data/raw/.

Las reglas de validación y el análisis viven en el paquete compartido packages/shared
(brasaland_shared.incidents), que también usan la API y el seed del gestor de incidencias;
este script solo se ocupa de la consola y de la exportación. El paquete usa solo la
librería estándar, así que no hace falta instalar nada.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "shared"))

# FIELDS, EXPORT_COLUMNS y validate_record no se usan aquí: se reexportan para las pruebas.
from brasaland_shared.incidents.analysis import (  # noqa: E402
    EXPORT_COLUMNS,
    SCORE_LABELS,
    analyze,
    build_export_rows,
    export_csv_text,
    percentage,
    rounded_average,
)
from brasaland_shared.incidents.validation import (  # noqa: E402
    FIELDS,
    MAX_SCORE,
    RULES,
    load_records,
    validate_record,
)

RAW_DIR = REPO_ROOT / "data" / "raw"
EXPORT_PATH = REPO_ROOT / "data" / "process" / "results.csv"
EXPORT_PROMPT = "¿Deseas exportar los resultados a CSV? [s / n]: "
YES_ANSWERS = {"s", "si", "sí", "y", "yes"}

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


def invalid_detail_lines(details):
    """Una línea por registro inválido, por ejemplo "  ├─ BRS-000044 (row 45): Missing location_id"."""
    labels = dict(RULES)
    lines = []
    for index, detail in enumerate(details):
        connector = "└─" if index == len(details) - 1 else "├─"
        reasons = "; ".join(labels[rule] for rule in detail["rules"])
        lines.append(f"  {connector} {detail['incident_id'] or '(no id)'} (row {detail['row']}): {reasons}")
    return lines


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

    if summary["invalid_details"]:
        lines += ["", "INVALID RECORDS DETAIL"]
        lines += invalid_detail_lines(summary["invalid_details"])

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


def export_csv(rows, path=EXPORT_PATH):
    """Escribe las filas en CSV, sobrescribiendo el archivo anterior, y devuelve la ruta."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(export_csv_text(rows))
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

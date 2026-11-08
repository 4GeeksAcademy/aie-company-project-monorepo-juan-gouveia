"""Reglas del CSV de incidentes del sistema legacy (`incidents-<empresa>.csv`).

- `validation`: columnas, valores permitidos, lectura del archivo y reglas de invalidez.
- `analysis`: métricas del reporte y su exportación a CSV.
- `exceptions`: errores de un archivo que no se puede analizar.

Lo usan el analizador (`scripts/incident-report/analyze.py`), el seed del gestor
(`scripts/seed_incidents.py`) y la API (`services/brasaland-api`, dominio `incidents`).
"""

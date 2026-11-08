"""Almacén del último análisis de incidentes.

Aún no hay base de datos: se guarda en la memoria del proceso y se pierde al reiniciar la API.
Cuando exista la base de datos, solo cambia esta clase; el router usa la misma interfaz.
"""

from dataclasses import dataclass
from threading import Lock

from app.domains.incidents.schemas import AnalysisResponse


@dataclass(frozen=True)
class StoredAnalysis:
    result: AnalysisResponse
    export_csv: str


class LastAnalysisRepository:
    def __init__(self):
        self._lock = Lock()
        self._last: StoredAnalysis | None = None

    def save(self, analysis: StoredAnalysis) -> None:
        with self._lock:
            self._last = analysis

    def get(self) -> StoredAnalysis | None:
        with self._lock:
            return self._last

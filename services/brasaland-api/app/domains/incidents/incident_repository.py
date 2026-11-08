"""Acceso a las incidencias del gestor guardadas en TinyDB.

Es la única pieza del gestor que conoce TinyDB: el router y el seed trabajan con modelos Pydantic.
Usa el archivo de datos de negocio (`storage/brasaland-db.json`), que comparte con proveedores, y
su mismo bloqueo (`core.storage.lock_for`).

Tablas:
- `incidents`: las incidencias, con el `doc_id` de TinyDB como `id`.
- `incident_seed_log`: qué filas del CSV histórico ya se cargaron (`incident_id` del CSV → `id`).
  El briefing pide no guardar `incident_id` en la incidencia, pero el seed lo necesita para no
  duplicar registros: `title + created_at` no sirve, porque varias filas del CSV lo comparten.
"""

# Las anotaciones se evalúan en diferido: dentro de la clase, `list` es el método y no el tipo.
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from tinydb import Query, TinyDB
from tinydb.table import Document

from app.core.storage import insert_with_file_id, lock_for, open_db
from app.domains.incidents.exceptions import InvalidTransitionError
from app.domains.incidents.models import (
    TRANSITIONS,
    Branch,
    Incident,
    IncidentCategory,
    IncidentCreate,
    IncidentOrigin,
    IncidentRecord,
    IncidentStatus,
    IncidentSummary,
)

INCIDENTS_TABLE = "incidents"
SEED_LOG_TABLE = "incident_seed_log"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IncidentRepository:
    def __init__(self, db: TinyDB, lock: RLock | None = None):
        self._db = db
        # Sin caché: así se ven también las incidencias que carga el seed desde otro proceso.
        self._table = db.table(INCIDENTS_TABLE, cache_size=0)
        self._seed_log = db.table(SEED_LOG_TABLE, cache_size=0)
        # TinyDB no es seguro entre hilos; el bloqueo es el del archivo (lo comparte con proveedores).
        self._lock = lock or RLock()

    @classmethod
    def from_path(cls, path: Path) -> IncidentRepository:
        return cls(open_db(path), lock_for(path))

    def close(self) -> None:
        self._db.close()

    # --- Lectura ---------------------------------------------------------------------------

    def list(
        self,
        status: IncidentStatus | None = None,
        origin: IncidentOrigin | None = None,
        branch: Branch | None = None,
        category: IncidentCategory | None = None,
    ) -> list[Incident]:
        """Incidencias de la más reciente a la más antigua; los filtros se combinan."""
        with self._lock:
            documents = self._table.all()
        incidents = [self._to_incident(document) for document in documents]
        filters = {"status": status, "origin": origin, "branch": branch, "category": category}
        for field, value in filters.items():
            if value is not None:
                incidents = [incident for incident in incidents if getattr(incident, field) == value]
        return sorted(incidents, key=lambda incident: (incident.created_at, incident.id), reverse=True)

    def get(self, incident_id: int) -> Incident | None:
        with self._lock:
            document = self._table.get(doc_id=incident_id)
        return None if document is None else self._to_incident(document)

    def summary(self) -> IncidentSummary:
        """Totales por estado, categoría, origen y sede, con todos los valores aunque estén en 0."""
        with self._lock:
            documents = self._table.all()

        def count(field: str, values: type) -> dict:
            counts = Counter(document[field] for document in documents)
            return {value: counts[value.value] for value in values}

        return IncidentSummary(
            total=len(documents),
            by_status=count("status", IncidentStatus),
            by_category=count("category", IncidentCategory),
            by_origin=count("origin", IncidentOrigin),
            by_branch=count("branch", Branch),
        )

    def is_seeded(self, source_id: str) -> bool:
        """True si la fila del CSV con ese `incident_id` ya se cargó."""
        with self._lock:
            return self._seed_log.contains(Query().source_id == source_id)

    # --- Escritura -------------------------------------------------------------------------

    def create(self, data: IncidentCreate, now: datetime | None = None) -> Incident:
        """Guarda una incidencia nueva; `created_at` y `updated_at` son la hora actual en UTC."""
        moment = (now or utc_now()).isoformat()
        with self._lock:
            return self._insert(data, created_at=moment)

    def create_from_seed(self, source_id: str, data: IncidentRecord, created_at: datetime) -> Incident | None:
        """Carga una fila del CSV histórico. Devuelve None, sin insertar nada, si ya se había cargado.

        La comprobación y las dos inserciones se hacen con el mismo bloqueo, así que dos cargas a la
        vez dentro del proceso no duplican nada.
        """
        with self._lock:
            if self._seed_log.contains(Query().source_id == source_id):
                return None
            incident = self._insert(data, created_at=created_at.isoformat())
            insert_with_file_id(self._seed_log, {"source_id": source_id, "incident_id": incident.id})
            return incident

    def update_status(self, incident_id: int, status: IncidentStatus, now: datetime | None = None) -> Incident | None:
        """Cambia solo el estado (y `updated_at`). None si no existe; InvalidTransitionError si el
        ciclo de vida no permite el cambio."""
        target = IncidentStatus(status)
        with self._lock:
            document = self._table.get(doc_id=incident_id)
            if document is None:
                return None
            current = IncidentStatus(document["status"])
            allowed = TRANSITIONS[current]
            if target not in allowed:
                raise InvalidTransitionError(current, target, allowed)
            self._table.update(
                {"status": target.value, "updated_at": (now or utc_now()).isoformat()}, doc_ids=[incident_id]
            )
            document = self._table.get(doc_id=incident_id)
        return self._to_incident(document)

    # --- Internos --------------------------------------------------------------------------

    def _insert(self, data: IncidentCreate | IncidentRecord, created_at: str) -> Incident:
        # Quien llama tiene el bloqueo. El ID se calcula desde el archivo (core.storage).
        record = data.model_dump(mode="json")
        record["created_at"] = created_at
        record["updated_at"] = created_at
        incident_id = insert_with_file_id(self._table, record)
        return self._to_incident(self._table.get(doc_id=incident_id))

    @staticmethod
    def _to_incident(document: Document) -> Incident:
        return Incident(id=document.doc_id, **document)

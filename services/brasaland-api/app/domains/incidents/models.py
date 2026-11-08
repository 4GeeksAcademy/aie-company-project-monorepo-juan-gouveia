"""Modelo del gestor de incidencias centralizado.

Los nombres de campos, categorías, estados, orígenes y sedes son exactamente los del briefing
("Gestor de Incidencias Centralizado"). FastAPI valida con estos modelos antes de ejecutar el
endpoint, así que una entrada inválida no llega a TinyDB.

El analizador del CSV (service.py y schemas.py) usa otro esquema, el del sistema legacy
(`OPEN`/`CLOSED`, `CUSTOMER_COMPLAINT`…); el seed lo transforma a este modelo.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class IncidentCategory(StrEnum):
    EQUIPMENT_FAILURE = "equipment_failure"
    SUPPLY_ISSUE = "supply_issue"
    CUSTOMER_COMPLAINT = "customer_complaint"
    STAFF_ISSUE = "staff_issue"
    FACILITY_ISSUE = "facility_issue"
    POS_SYSTEM = "pos_system"
    DELIVERY_ISSUE = "delivery_issue"
    OTHER = "other"


class IncidentStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISCARDED = "discarded"


class IncidentOrigin(StrEnum):
    CUSTOMER = "customer"
    BRANCH = "branch"
    INTERNAL = "internal"


class Branch(StrEnum):
    """Sedes del briefing. `central` se usa cuando la incidencia no corresponde a un local."""

    CENTRAL = "central"
    MEDELLIN_CENTRO = "medellin_centro"
    MEDELLIN_LAURELES = "medellin_laureles"
    MEDELLIN_ENVIGADO = "medellin_envigado"
    MEDELLIN_BELLO = "medellin_bello"
    MEDELLIN_ITAGUI = "medellin_itagui"
    BOGOTA_CHAPINERO = "bogota_chapinero"
    BOGOTA_USAQUEN = "bogota_usaquen"
    CALI_GRANADA = "cali_granada"
    BARRANQUILLA_NORTE = "barranquilla_norte"
    MIAMI_DORAL = "miami_doral"
    MIAMI_HIALEAH = "miami_hialeah"
    MIAMI_KENDALL = "miami_kendall"
    ORLANDO_INTERNATIONAL = "orlando_international"
    FORT_LAUDERDALE = "fort_lauderdale"


# Ciclo de vida del briefing: resolved y discarded son finales.
TRANSITIONS: dict[IncidentStatus, tuple[IncidentStatus, ...]] = {
    IncidentStatus.OPEN: (IncidentStatus.IN_PROGRESS, IncidentStatus.DISCARDED),
    IncidentStatus.IN_PROGRESS: (IncidentStatus.RESOLVED, IncidentStatus.DISCARDED),
    IncidentStatus.RESOLVED: (),
    IncidentStatus.DISCARDED: (),
}

MAX_TITLE_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 2000

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TITLE_LENGTH)]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
]


class IncidentFields(BaseModel):
    title: Title = Field(description="Título breve de la incidencia")
    description: Description = Field(description="Descripción detallada")
    category: IncidentCategory = Field(description="Categoría del briefing")
    origin: IncidentOrigin = Field(description="Origen del reporte: customer, branch o internal")
    branch: Branch = Field(description="Sede que gestiona o reporta la incidencia; `central` si no es un local")


class IncidentCreate(IncidentFields):
    """Entrada de POST /incidents. `id`, `created_at` y `updated_at` los genera el sistema."""

    model_config = ConfigDict(extra="forbid")

    status: IncidentStatus = Field(
        default=IncidentStatus.OPEN, description="Toda incidencia nueva empieza en `open`; se puede omitir"
    )

    @field_validator("status")
    @classmethod
    def starts_open(cls, status: IncidentStatus) -> IncidentStatus:
        if status != IncidentStatus.OPEN:
            raise ValueError("Una incidencia nueva siempre empieza en open; cambia el estado después.")
        return status


class IncidentRecord(IncidentFields):
    """Incidencia con su estado, sin los campos que genera el sistema. La usa el seed: las filas del
    CSV histórico llegan ya resueltas o descartadas, así que no pasan por la regla de `IncidentCreate`."""

    model_config = ConfigDict(extra="forbid")

    status: IncidentStatus


class StatusUpdate(BaseModel):
    """Entrada de PATCH /incidents/{id}/status."""

    model_config = ConfigDict(extra="forbid")

    status: IncidentStatus


class Incident(IncidentFields):
    """Incidencia tal como la devuelve la API."""

    id: int = Field(description="Identificador generado automáticamente")
    status: IncidentStatus
    created_at: datetime = Field(description="Fecha y hora de creación (UTC)")
    updated_at: datetime = Field(description="Fecha y hora de la última modificación (UTC)")


class IncidentSummary(BaseModel):
    """Métricas de GET /incidents/summary. Cada desglose incluye todos los valores del briefing, también los que están en 0."""

    total: int
    by_status: dict[IncidentStatus, int]
    by_category: dict[IncidentCategory, int]
    by_origin: dict[IncidentOrigin, int]
    by_branch: dict[Branch, int]

"""Esquemas de los endpoints de `/reporting` (diseño, §6; briefing del pipeline, §6)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LocationWeekPerformance(BaseModel):
    """Una fila del Reporte Semanal de Costo y Merma por Local: un local en una semana."""

    location_id: str = Field(description="Código del local (`locations.code`), p. ej. `medellin_centro`")
    location_name: str | None = Field(description="Nombre del local para mostrar (`locations.name`), p. ej. `Medellín Centro`")
    country: Literal["CO", "US"] = Field(description="País del local")
    total_purchase_cost: float = Field(description="Costo de compra de la semana: Σ cantidad × coste unitario de las entradas, en `currency`")
    total_waste_cost: float = Field(description="Costo de merma de la semana: Σ cantidad × coste unitario de las mermas, en `currency`")
    waste_ratio: float = Field(description="Ratio de merma: `total_waste_cost / total_purchase_cost`; 0 si no hubo compras")
    stockout_events_count: int = Field(description="Quiebres de stock de la semana (`stock_threshold_triggered`)")
    price_alert_events_count: int = Field(description="Alertas de subida de precio de la semana (`ingredient_price_variance_detected`)")
    currency: Literal["COP", "USD"] = Field(description="Moneda del local; nunca se convierte")


class WeeklyLocationPerformance(BaseModel):
    """`GET /reporting/weekly-location-performance`: todos los locales de una semana."""

    week_start: date = Field(description="Lunes de la semana ISO (UTC)")
    locations: list[LocationWeekPerformance] = Field(description="Los locales de esa semana, por país y por local")


class PipelineRunRead(BaseModel):
    """Estado y metadata de una corrida del pipeline (`reporting.pipeline_runs`; diseño, §4.4)."""

    id: UUID = Field(description="Id de la corrida")
    pipeline: str = Field(description="Pipeline que corrió (`weekly_location_performance`)")
    trigger: Literal["scheduled", "manual"] = Field(description="Corrida programada de los lunes o pedida a mano")
    status: Literal["pending", "running", "completed", "failed"] = Field(description="Estado de la corrida")
    week_from: date = Field(description="Primera semana (lunes) que recalcula")
    week_to: date = Field(description="Última semana (lunes) que recalcula")
    created_at: datetime = Field(description="Cuándo se pidió")
    started_at: datetime | None = Field(description="Hora de inicio; null mientras espera en la cola")
    finished_at: datetime | None = Field(description="Hora de fin; null mientras corre")
    events_read: int = Field(description="Eventos leídos de `telemetry_events`")
    events_rejected: int = Field(description="Eventos excluidos por datos inválidos")
    events_discarded: int = Field(description="Eventos excluidos por regla (duplicados, alertas de bajada, fuera de las semanas)")
    waste_events_without_cost: int = Field(description="Mermas sin `unit_cost`, contadas con coste 0")
    issues: dict[str, int] = Field(description="Eventos excluidos y pasos opcionales fallidos, por motivo")
    rows_written: int = Field(description="Filas escritas en `reporting.weekly_location_performance`")
    failed_task: str | None = Field(description="Task en la que falló la corrida")
    error_message: str | None = Field(description="Error resumido, sin datos de conexión")


class PipelineRunRequest(BaseModel):
    """Cuerpo opcional de `POST /reporting/pipeline-runs`: un backfill por rango."""

    model_config = ConfigDict(extra="forbid")

    week_from: date | None = Field(default=None, description="Primer lunes del rango; sin rango, las 4 últimas semanas cerradas")
    week_to: date | None = Field(default=None, description="Último lunes del rango (como mucho, la última semana cerrada)")

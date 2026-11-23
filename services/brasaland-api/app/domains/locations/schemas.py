"""Schema de respuesta del catálogo de locales. Independiente del modelo ORM de `models.py`."""

from typing import Literal

from pydantic import BaseModel, Field


class LocationRead(BaseModel):
    """Un local tal como lo devuelve `GET /api/v1/locations`."""

    id: int = Field(description="`location_id` de las órdenes y de la telemetría (1–14)")
    code: str = Field(description="Código de la sede del briefing, p. ej. `medellin_centro`")
    name: str = Field(description='Nombre para mostrar, p. ej. "Medellín Centro"')
    city: str
    country: Literal["CO", "US"] = Field(description="País del local")
    currency: Literal["COP", "USD"] = Field(description="Moneda del local, sin conversión")

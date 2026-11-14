"""Schemas Pydantic de petición y respuesta del inventario.

Son clases independientes de los modelos ORM de `models.py`, aunque compartan campos: los endpoints
reciben y devuelven siempre estos schemas, nunca un objeto SQLModel.

Los nombres de campos y los valores válidos son exactamente los del briefing. Las entradas no
admiten campos que genera el sistema (`id`, `created_at`, `user_uuid`) ni `current_stock`: si
llegan, la API responde 422. Así un ingrediente nace siempre con stock 0, y el `user_uuid` de una
orden es siempre el del usuario autenticado (decisión D3).
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.domains.inventory.models import NAME_MAX_LENGTH, SKU_MAX_LENGTH, SUPPLIER_NAME_MAX_LENGTH

# Los locales de Brasaland van del 1 al 14 (regla de negocio 5); no es FK en este hito.
MIN_LOCATION_ID = 1
MAX_LOCATION_ID = 14


class Unit(StrEnum):
    KG = "kg"
    LITRO = "litro"
    UNIDAD = "unidad"


class Category(StrEnum):
    MEAT = "meat"
    PRODUCE = "produce"
    SAUCE = "sauce"
    BEVERAGE = "beverage"
    PACKAGING = "packaging"
    CLEANING = "cleaning"


class Country(StrEnum):
    CO = "CO"
    US = "US"


class ExitReason(StrEnum):
    CONSUMPTION = "consumption"
    WASTE = "waste"


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH)]
Sku = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=SKU_MAX_LENGTH)]
SupplierName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=SUPPLIER_NAME_MAX_LENGTH)
]
# Cantidad estricta: un número mayor que 0. Rechaza textos ("10"), booleanos, NaN e infinito.
Quantity = Annotated[float, Field(gt=0, strict=True, allow_inf_nan=False)]
IngredientId = Annotated[int, Field(ge=1, strict=True)]
LocationId = Annotated[int, Field(ge=MIN_LOCATION_ID, le=MAX_LOCATION_ID, strict=True)]


def as_utc(value: datetime) -> datetime:
    """Devuelve la fecha en UTC (ISO 8601 con +00:00). PostgreSQL la devuelve con zona; si llega sin
    ella (SQLite, en las pruebas), es UTC, porque así se guardó."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


# --- Ingredientes ----------------------------------------------------------------------------


class IngredientCreate(BaseModel):
    """Entrada de POST /inventory/products. No admite `current_stock`: el stock nace en 0."""

    model_config = ConfigDict(extra="forbid")

    name: Name = Field(description='Nombre del ingrediente, p. ej. "Falda de ternera"')
    sku: Sku = Field(description='Código interno único, p. ej. "BRS-BEEF-001"')
    unit: Unit = Field(description='Unidad de medida: "kg", "litro" o "unidad"')
    category: Category = Field(description='"meat", "produce", "sauce", "beverage", "packaging" o "cleaning"')
    country: Country = Field(description='"CO" (Colombia) o "US" (Estados Unidos)')


class IngredientRead(BaseModel):
    """Ingrediente tal como lo devuelve la API, con su stock calculado."""

    id: int
    name: str
    sku: str
    unit: Unit
    category: Category
    country: Country
    current_stock: float = Field(
        description="Calculado, no almacenado: suma de las entradas menos suma de las salidas"
    )


class IngredientSummary(BaseModel):
    """Datos del ingrediente que acompañan a cada orden en GET /inventory/orders."""

    id: int
    name: str
    sku: str
    unit: Unit
    country: Country


# --- Órdenes ---------------------------------------------------------------------------------


class IngredientEntryCreate(BaseModel):
    """Entrada de POST /inventory/orders/inbound. `user_uuid` sale del token, no del cuerpo."""

    model_config = ConfigDict(extra="forbid")

    ingredient_id: IngredientId
    quantity: Quantity = Field(description="Cantidad recibida, en la unidad del ingrediente")
    supplier_name: SupplierName = Field(description="Proveedor de esta entrega")
    location_id: LocationId = Field(description="Local receptor (1–14)")


class IngredientExitCreate(BaseModel):
    """Entrada de POST /inventory/orders/outbound. `user_uuid` sale del token, no del cuerpo."""

    model_config = ConfigDict(extra="forbid")

    ingredient_id: IngredientId
    quantity: Quantity = Field(description="Cantidad consumida o mermada, en la unidad del ingrediente")
    reason: ExitReason = Field(description='"consumption" (consumo) o "waste" (merma)')
    location_id: LocationId = Field(description="Local donde ocurrió la salida (1–14)")


class OrderReadBase(BaseModel):
    id: int
    ingredient_id: int
    quantity: float
    location_id: int
    created_at: datetime = Field(description="Momento del registro, en UTC")
    user_uuid: str = Field(description="UUID (TinyDB) del usuario autenticado que registró la orden")
    ingredient: IngredientSummary

    @field_validator("created_at")
    @classmethod
    def created_at_in_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class IngredientEntryRead(OrderReadBase):
    supplier_name: str


class IngredientExitRead(OrderReadBase):
    reason: ExitReason


class OrdersRead(BaseModel):
    """Respuesta de GET /inventory/orders: entradas y salidas, de la más reciente a la más antigua."""

    inbound: list[IngredientEntryRead]
    outbound: list[IngredientExitRead]

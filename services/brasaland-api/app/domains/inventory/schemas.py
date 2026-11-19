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

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationInfo, field_validator

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


class WasteReason(StrEnum):
    """Motivo de una merma, con los valores del briefing de telemetría (brecha B6)."""

    EXPIRED = "expired"
    KITCHEN_ERROR = "kitchen_error"
    THEFT_SUSPECTED = "theft_suspected"


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH)]
Sku = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=SKU_MAX_LENGTH)]
SupplierName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=SUPPLIER_NAME_MAX_LENGTH)
]
# Cantidad estricta: un número mayor que 0. Rechaza textos ("10"), booleanos, NaN e infinito.
Quantity = Annotated[float, Field(gt=0, strict=True, allow_inf_nan=False)]
# Coste unitario estricto, mayor que 0, en la moneda del país del ingrediente (COP o USD).
UnitCost = Annotated[float, Field(gt=0, strict=True, allow_inf_nan=False)]
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


# --- Órdenes ---------------------------------------------------------------------------------


class IngredientEntryCreate(BaseModel):
    """Entrada de POST /inventory/orders/inbound. `user_uuid` sale del token, no del cuerpo."""

    model_config = ConfigDict(extra="forbid")

    ingredient_id: IngredientId
    quantity: Quantity = Field(description="Cantidad recibida, en la unidad del ingrediente")
    supplier_name: SupplierName = Field(description="Proveedor de esta entrega")
    unit_cost: UnitCost = Field(
        description="Coste por unidad del ingrediente, en la moneda de su país (COP o USD)"
    )
    location_id: LocationId = Field(description="Local receptor (1–14)")


class IngredientExitCreate(BaseModel):
    """Entrada de POST /inventory/orders/outbound. `user_uuid` sale del token, no del cuerpo."""

    model_config = ConfigDict(extra="forbid")

    ingredient_id: IngredientId
    quantity: Quantity = Field(description="Cantidad consumida o mermada, en la unidad del ingrediente")
    reason: ExitReason = Field(description='"consumption" (consumo) o "waste" (merma)')
    waste_reason: WasteReason | None = Field(
        default=None,
        # Se valida también cuando falta, para exigirlo en las mermas.
        validate_default=True,
        description='Solo en las mermas, y obligatorio en ellas: "expired", "kitchen_error" o "theft_suspected"',
    )
    location_id: LocationId = Field(description="Local donde ocurrió la salida (1–14)")

    @field_validator("waste_reason")
    @classmethod
    def waste_reason_only_for_waste(cls, value: WasteReason | None, info: ValidationInfo) -> WasteReason | None:
        # `reason` se valida antes (va antes en el modelo); si no es válido, ya tiene su propio error.
        reason = info.data.get("reason")
        if reason == ExitReason.WASTE and value is None:
            raise ValueError("Indica el motivo de la merma.")
        if reason == ExitReason.CONSUMPTION and value is not None:
            raise ValueError("Un consumo no lleva motivo de merma.")
        return value


class OrderReadBase(BaseModel):
    """Campos comunes de una orden en la respuesta: proyección plana del ingrediente.

    El ingrediente no va anidado: la orden lleva su `ingredient_id` y solo los tres datos que muestra
    el backoffice (nombre, SKU y unidad). Ver docs/serialization-audit.md (4.7 y sección 5).
    """

    id: int = Field(description="Identificador de la orden")
    ingredient_id: int = Field(description="ID del ingrediente (referencia a GET /inventory/products/{id})")
    ingredient_name: str = Field(description="Nombre del ingrediente")
    ingredient_sku: str = Field(description="SKU del ingrediente")
    ingredient_unit: Unit = Field(description="Unidad en la que se expresa `quantity`")
    quantity: float = Field(description="Cantidad de la orden, en la unidad del ingrediente")
    location_id: int = Field(description="Local de la orden (1–14)")
    created_at: datetime = Field(description="Momento del registro, en UTC")
    user_uuid: str = Field(description="UUID (TinyDB) del usuario autenticado que registró la orden")

    @field_validator("created_at")
    @classmethod
    def created_at_in_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class IngredientEntryRead(OrderReadBase):
    """Salida de POST /inventory/orders/inbound y de cada entrada en GET /inventory/orders."""

    supplier_name: str = Field(description="Proveedor de la entrega")
    unit_cost: float | None = Field(description="Coste por unidad, en la moneda del país; null en entradas anteriores")


class IngredientExitRead(OrderReadBase):
    """Salida de POST /inventory/orders/outbound y de cada salida en GET /inventory/orders."""

    reason: ExitReason = Field(description='"consumption" (consumo) o "waste" (merma)')
    waste_reason: WasteReason | None = Field(description="Motivo de la merma; null en los consumos y en mermas anteriores")


class OrdersRead(BaseModel):
    """Respuesta de GET /inventory/orders: entradas y salidas, de la más reciente a la más antigua."""

    inbound: list[IngredientEntryRead]
    outbound: list[IngredientExitRead]

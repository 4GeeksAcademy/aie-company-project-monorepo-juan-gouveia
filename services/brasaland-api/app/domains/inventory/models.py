"""Modelos ORM del inventario (SQLModel, `table=True`): cada clase es una tabla de Supabase.

Los nombres de entidades y campos son exactamente los del briefing del Hito 5:

- `Ingredient` (el «producto» de la consigna): **no tiene columna de stock**. `current_stock` se
  calcula siempre a partir de las órdenes y solo existe en el schema de respuesta (`schemas.py`).
- `IngredientEntry` (orden de entrada): una entrega de un proveedor; suma stock.
- `IngredientExit` (orden de salida): un consumo o una merma; resta stock.

Las dos órdenes tienen una clave foránea real a `ingredients.id`, aplicada por la base de datos.
`user_uuid` guarda el `id` del usuario de TinyDB que registró la orden, sin FK: ninguna tabla de
usuarios se replica en Supabase. `location_id` (1–14) tampoco es FK en este hito.

Estas clases nunca salen de la API: los endpoints responden con los schemas de `schemas.py`.
Los `Relationship` documentan la relación, pero el código no los recorre en bucles (problema N+1):
las consultas cargan el ingrediente con un `join` (ver `service.py`).
"""

from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel

# Longitudes máximas de las columnas de texto; los schemas aplican las mismas.
NAME_MAX_LENGTH = 120
SKU_MAX_LENGTH = 40
SUPPLIER_NAME_MAX_LENGTH = 120
# UUID de TinyDB en texto (36 caracteres con guiones).
USER_UUID_LENGTH = 36


def utc_now() -> datetime:
    """Hora actual en UTC, con zona: SQLModel guarda `datetime` como `timestamp with time zone` y
    rechaza las fechas sin zona."""
    return datetime.now(UTC)


class Ingredient(SQLModel, table=True):
    __tablename__ = "ingredients"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=NAME_MAX_LENGTH)
    # Código interno único (p. ej. BRS-BEEF-001): la base de datos impide duplicados.
    sku: str = Field(max_length=SKU_MAX_LENGTH, unique=True, index=True)
    # "kg", "litro" o "unidad"; los valores válidos los impone el schema de entrada.
    unit: str = Field(max_length=10)
    # "meat", "produce", "sauce", "beverage", "packaging" o "cleaning".
    category: str = Field(max_length=20)
    # "CO" o "US": los ingredientes de los dos mercados conviven en la misma tabla.
    country: str = Field(max_length=2, index=True)

    entries: list["IngredientEntry"] = Relationship(back_populates="ingredient")
    exits: list["IngredientExit"] = Relationship(back_populates="ingredient")


class IngredientEntry(SQLModel, table=True):
    """Entrega de ingredientes recibida de un proveedor (orden de entrada)."""

    __tablename__ = "ingredient_entries"

    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredients.id", index=True)
    quantity: float
    supplier_name: str = Field(max_length=SUPPLIER_NAME_MAX_LENGTH)
    location_id: int
    created_at: datetime = Field(default_factory=utc_now)
    user_uuid: str = Field(max_length=USER_UUID_LENGTH, index=True)

    ingredient: Ingredient | None = Relationship(back_populates="entries")


class IngredientExit(SQLModel, table=True):
    """Consumo o merma de ingredientes (orden de salida)."""

    __tablename__ = "ingredient_exits"

    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredients.id", index=True)
    quantity: float
    # "consumption" o "waste"; los valores válidos los impone el schema de entrada.
    reason: str = Field(max_length=20)
    location_id: int
    created_at: datetime = Field(default_factory=utc_now)
    user_uuid: str = Field(max_length=USER_UUID_LENGTH, index=True)

    ingredient: Ingredient | None = Relationship(back_populates="exits")

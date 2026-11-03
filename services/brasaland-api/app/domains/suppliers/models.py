"""Modelos Pydantic del directorio de proveedores.

Los nombres de campos, países, monedas, categorías y estados son exactamente los del briefing.
FastAPI valida con estos modelos antes de ejecutar el endpoint, así que una entrada inválida
recibe un 422 sin llegar a TinyDB.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, ValidationInfo, field_validator


class Country(StrEnum):
    COLOMBIA = "Colombia"
    USA = "USA"


class Currency(StrEnum):
    COP = "COP"
    USD = "USD"


class SupplierStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Category(StrEnum):
    """VALID_CATEGORIES del briefing, en el mismo orden."""

    CARNE = "carne"
    VERDURAS_Y_HORTALIZAS = "verduras_y_hortalizas"
    SALSAS_Y_CONDIMENTOS = "salsas_y_condimentos"
    BEBIDAS = "bebidas"
    PACKAGING = "packaging"
    PRODUCTOS_LIMPIEZA = "productos_limpieza"
    LACTEOS = "lacteos"
    CARBON_Y_COMBUSTIBLE = "carbon_y_combustible"


VALID_CATEGORIES = [category.value for category in Category]
VALID_STATUSES = [status.value for status in SupplierStatus]

# Restricción de negocio: cada país opera en su moneda.
CURRENCY_BY_COUNTRY = {Country.COLOMBIA: Currency.COP, Country.USA: Currency.USD}

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
# Tarifa estricta: un número mayor que 0. Rechaza textos ("10"), booleanos, NaN e infinito.
Rate = Annotated[float, Field(gt=0, strict=True, allow_inf_nan=False)]


class SupplierBase(BaseModel):
    name: Name = Field(description="Nombre comercial del proveedor")
    country: Country = Field(description='País de operación: "Colombia" o "USA"')
    categories: list[Category] = Field(min_length=1, description="Categorías de producto que suministra")
    rate_per_unit: Rate = Field(description="Tarifa vigente por unidad en la moneda del país")
    currency: Currency = Field(description='"COP" para Colombia, "USD" para USA')
    status: SupplierStatus = Field(description='"active" o "suspended"')
    contact_email: EmailStr | None = Field(default=None, description="Email de contacto del proveedor")
    notes: Notes | None = Field(default=None, description="Observaciones internas del equipo de compras")

    @field_validator("categories")
    @classmethod
    def categories_are_unique(cls, categories: list[Category]) -> list[Category]:
        if len(set(categories)) != len(categories):
            raise ValueError("Las categorías no pueden repetirse.")
        return categories

    @field_validator("currency")
    @classmethod
    def currency_matches_country(cls, currency: Currency, info: ValidationInfo) -> Currency:
        # Si el país ya es inválido, ese error basta; aquí solo se compara con un país válido.
        country = info.data.get("country")
        if country is not None and CURRENCY_BY_COUNTRY[country] != currency:
            expected = CURRENCY_BY_COUNTRY[country]
            raise ValueError(f"Un proveedor de {country.value} debe usar {expected.value}.")
        return currency

    @field_validator("notes")
    @classmethod
    def empty_notes_are_none(cls, notes: str | None) -> str | None:
        return notes or None


class SupplierCreate(SupplierBase):
    """Entrada de POST /suppliers. `id` y `updated_at` los genera el sistema: si llegan, es un 422."""

    model_config = ConfigDict(extra="forbid")


class RateUpdate(BaseModel):
    """Entrada de PATCH /suppliers/{id}/rate."""

    model_config = ConfigDict(extra="forbid")

    rate_per_unit: Rate


class StatusUpdate(BaseModel):
    """Entrada de PATCH /suppliers/{id}/status."""

    model_config = ConfigDict(extra="forbid")

    status: SupplierStatus


class Supplier(SupplierBase):
    """Proveedor tal como lo devuelve la API."""

    id: int = Field(description="ID asignado por TinyDB")
    updated_at: datetime = Field(description="Timestamp (UTC) de la última actualización de tarifa")

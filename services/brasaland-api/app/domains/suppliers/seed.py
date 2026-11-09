"""Seeder del directorio de proveedores: importa la hoja de cálculo de Lucía a TinyDB.

Uso: `uv run seed` desde services/brasaland-api/. Inserta solo los proveedores que falten
(comparando por nombre), así que ejecutarlo varias veces no duplica nada.

La API también siembra al arrancar, pero solo si la tabla está vacía: un proveedor eliminado
con DELETE (corrección de datos) no reaparece al reiniciar.
"""

import json
import sys
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.errors import describe_validation_errors
from app.domains.suppliers.database import get_db_path
from app.domains.suppliers.models import SupplierCreate
from app.domains.suppliers.repository import SupplierRepository

# Copia literal de SUPPLIERS_SEED del briefing.
SUPPLIERS_SEED = [
    {
        "name": "Carnes del Valle S.A.S.",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 28500.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "ventas@carnesdelvalle.co",
        "notes": "Proveedor principal de res y cerdo para Medellín. Entrega martes y viernes.",
    },
    {
        "name": "Frigorífico Antioqueño",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 27900.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "pedidos@frigorificoa.co",
        "notes": "Proveedor secundario. Usado cuando Carnes del Valle no tiene stock.",
    },
    {
        "name": "Verduras La Cosecha",
        "country": "Colombia",
        "categories": ["verduras_y_hortalizas"],
        "rate_per_unit": 3200.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "lacosecha@gmail.com",
        "notes": "Mercado mayorista de Medellín. Entrega diaria antes de las 7am.",
    },
    {
        "name": "Condimentos El Sabor",
        "country": "Colombia",
        "categories": ["salsas_y_condimentos"],
        "rate_per_unit": 12400.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "info@elsabor.co",
    },
    {
        "name": "Distribuidora RefriCol",
        "country": "Colombia",
        "categories": ["bebidas", "lacteos"],
        "rate_per_unit": 4100.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "refricol.pedidos@gmail.com",
    },
    {
        "name": "Empaques y Más",
        "country": "Colombia",
        "categories": ["packaging"],
        "rate_per_unit": 890.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "ventas@empaquesymas.co",
        "notes": "Suministra cajas, bolsas y servilletas para todos los locales de Colombia.",
    },
    {
        "name": "Limpiahogar Profesional",
        "country": "Colombia",
        "categories": ["productos_limpieza"],
        "rate_per_unit": 7600.0,
        "currency": "COP",
        "status": "suspended",
        "contact_email": "limpiahogar@promail.co",
        "notes": "Suspendido por incumplimiento en entregas. En revisión por Lucía.",
    },
    {
        "name": "CarboCo",
        "country": "Colombia",
        "categories": ["carbon_y_combustible"],
        "rate_per_unit": 45000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "pedidos@carboco.co",
        "notes": "Único proveedor homologado de carbón para las brasas. Contrato anual.",
    },
    {
        "name": "Miami Meat Distributors LLC",
        "country": "USA",
        "categories": ["carne"],
        "rate_per_unit": 6.80,
        "currency": "USD",
        "status": "active",
        "contact_email": "orders@miamimeat.com",
        "notes": "Proveedor principal de carne para los locales de Florida.",
    },
    {
        "name": "Sunshine Produce FL",
        "country": "USA",
        "categories": ["verduras_y_hortalizas"],
        "rate_per_unit": 2.15,
        "currency": "USD",
        "status": "active",
        "contact_email": "sales@sunshineproduce.com",
    },
    {
        "name": "Latin Flavors Inc.",
        "country": "USA",
        "categories": ["salsas_y_condimentos", "bebidas"],
        "rate_per_unit": 4.50,
        "currency": "USD",
        "status": "active",
        "contact_email": "orders@latinflavors.com",
        "notes": "Importa salsas colombianas para el mercado de Florida.",
    },
    {
        "name": "PackRight USA",
        "country": "USA",
        "categories": ["packaging"],
        "rate_per_unit": 0.35,
        "currency": "USD",
        "status": "active",
        "contact_email": "info@packright.us",
    },
    {
        "name": "CleanPro Florida",
        "country": "USA",
        "categories": ["productos_limpieza"],
        "rate_per_unit": 12.90,
        "currency": "USD",
        "status": "active",
        "contact_email": "orders@cleanproflorida.com",
    },
    {
        "name": "GrillFuel Supply Co.",
        "country": "USA",
        "categories": ["carbon_y_combustible"],
        "rate_per_unit": 38.50,
        "currency": "USD",
        "status": "active",
        "contact_email": "supply@grillfuel.com",
        "notes": "Proveedor de carbón para Florida. Precio sujeto a revisión trimestral.",
    },
    {
        "name": "Bebidas Andinas",
        "country": "Colombia",
        "categories": ["bebidas"],
        "rate_per_unit": 3800.0,
        "currency": "COP",
        "status": "suspended",
        "contact_email": "ventas@bebidasandinas.co",
        "notes": "Suspendido. Precio por encima del mercado tras última renegociación.",
    },
]


@dataclass(frozen=True)
class SeedResult:
    inserted: int
    skipped: int


def seed(repository: SupplierRepository) -> SeedResult:
    """Inserta los proveedores del briefing que aún no existan, comparando por nombre."""
    # Se validan todos antes de escribir: el seed cumple las mismas reglas que la API.
    suppliers = [SupplierCreate(**item) for item in SUPPLIERS_SEED]
    inserted = 0
    for supplier in suppliers:
        if repository.find_by_name(supplier.name) is None:
            repository.create(supplier)
            inserted += 1
    return SeedResult(inserted=inserted, skipped=len(suppliers) - inserted)


def seed_if_empty(repository: SupplierRepository) -> SeedResult | None:
    """Siembra al arrancar la API solo si la tabla está vacía; si ya hay datos, no hace nada."""
    return seed(repository) if repository.is_empty() else None


def _error(message: str) -> None:
    print(message, file=sys.stderr)


def main() -> int:
    """Punto de entrada de `uv run seed`. Devuelve el código de salida: 0 si termina bien, 1 si falla."""
    path = get_db_path()
    try:
        repository = SupplierRepository.from_path(path)
    except OSError as error:
        _error(f"No se puede abrir la base de proveedores {path}: {error.strerror or error}.")
        return 1
    try:
        result = seed(repository)
        total = repository.count()
    except ValidationError as error:
        # SUPPLIERS_SEED es una copia del briefing: solo falla si alguien la edita mal. Se valida
        # todo antes de escribir, así que la base no cambia.
        fields = ", ".join(item["field"] for item in describe_validation_errors(error.errors()))
        _error(f"Los datos iniciales de proveedores no son válidos ({fields}). No se insertó nada.")
        return 1
    except json.JSONDecodeError:
        # TinyDB lee el archivo en la primera consulta, antes de escribir nada.
        _error(
            f"La base de proveedores {path} no es un JSON válido y no se ha modificado. "
            "Revisa el archivo o restáuralo (si se borra, se crea de nuevo con los datos iniciales)."
        )
        return 1
    except OSError as error:
        # Por ejemplo, disco lleno. Se inserta proveedor a proveedor, así que puede quedar una carga
        # parcial; al repetir se comparan los nombres y no se duplica nada.
        _error(
            f"No se pudo escribir en la base de proveedores {path}: {error.strerror or error}. "
            "Puede que se haya cargado una parte; al ejecutarlo de nuevo no se duplica nada."
        )
        return 1
    finally:
        repository.close()
    print(
        f"Seeder completado: {result.inserted} proveedores insertados, "
        f"{result.skipped} ya existían. Total en la base: {total} ({path})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

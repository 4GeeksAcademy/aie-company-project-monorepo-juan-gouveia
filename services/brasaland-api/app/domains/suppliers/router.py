"""Endpoints del directorio de proveedores. Solo traducen HTTP: validan los modelos Pydantic
(422 antes de tocar TinyDB) y delegan en el repositorio.

Los endpoints son síncronos porque TinyDB lo es; FastAPI los ejecuta en su pool de hilos.
"""

from fastapi import APIRouter, Depends, Query, status

from app.core.errors import ApiError
from app.domains.suppliers.dependencies import get_repository
from app.domains.suppliers.exceptions import DuplicateSupplierError
from app.domains.suppliers.models import Category, Country, RateUpdate, StatusUpdate, Supplier, SupplierCreate
from app.domains.suppliers.repository import SupplierRepository

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

ERROR_RESPONSES = {
    404: {"description": "No existe ningún proveedor con ese ID (`supplier_not_found`)"},
    422: {"description": "Entrada inválida (`invalid_request`, con `details` por campo)"},
}


def not_found(supplier_id: int) -> ApiError:
    return ApiError(404, "supplier_not_found", f"No existe ningún proveedor con el ID {supplier_id}.")


def found(supplier: Supplier | None, supplier_id: int) -> Supplier:
    if supplier is None:
        raise not_found(supplier_id)
    return supplier


@router.post(
    "",
    response_model=Supplier,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Ya existe un proveedor con ese nombre (`duplicate_supplier`)"},
        422: ERROR_RESPONSES[422],
    },
)
def create_supplier(
    data: SupplierCreate, repository: SupplierRepository = Depends(get_repository)
) -> Supplier:
    """Registra un proveedor nuevo y lo devuelve con su ID asignado por TinyDB."""
    try:
        return repository.create(data)
    except DuplicateSupplierError as error:
        raise ApiError(
            409, "duplicate_supplier", f"Ya existe un proveedor llamado «{error.name}». Actualízalo en lugar de crearlo."
        ) from None


@router.get("", response_model=list[Supplier], responses={422: ERROR_RESPONSES[422]})
def list_suppliers(
    country: Country | None = Query(None, description='Filtra por país: "Colombia" o "USA"'),
    category: Category | None = Query(None, description="Filtra por categoría de producto"),
    repository: SupplierRepository = Depends(get_repository),
) -> list[Supplier]:
    """Lista los proveedores. Sin parámetros devuelve todos; los filtros se pueden combinar."""
    return repository.list(country=country, category=category)


@router.get("/{supplier_id}", response_model=Supplier, responses=ERROR_RESPONSES)
def get_supplier(supplier_id: int, repository: SupplierRepository = Depends(get_repository)) -> Supplier:
    """Detalle de un proveedor."""
    return found(repository.get(supplier_id), supplier_id)


@router.patch("/{supplier_id}/rate", response_model=Supplier, responses=ERROR_RESPONSES)
def update_rate(
    supplier_id: int, data: RateUpdate, repository: SupplierRepository = Depends(get_repository)
) -> Supplier:
    """Actualiza la tarifa y registra en `updated_at` el timestamp exacto del cambio."""
    return found(repository.update_rate(supplier_id, data.rate_per_unit), supplier_id)


@router.patch("/{supplier_id}/status", response_model=Supplier, responses=ERROR_RESPONSES)
def update_status(
    supplier_id: int, data: StatusUpdate, repository: SupplierRepository = Depends(get_repository)
) -> Supplier:
    """Activa o suspende un proveedor. No modifica `updated_at` (fecha de la última tarifa)."""
    return found(repository.update_status(supplier_id, data.status), supplier_id)


@router.delete("/{supplier_id}", response_model=Supplier, responses=ERROR_RESPONSES)
def delete_supplier(supplier_id: int, repository: SupplierRepository = Depends(get_repository)) -> Supplier:
    """Elimina un proveedor y lo devuelve. Solo para corregir datos erróneos: lo habitual es suspender."""
    return found(repository.delete(supplier_id), supplier_id)

"""Endpoints del inventario, bajo `/inventory` (montado en `/api/v1`, decisión D2).

Solo traducen HTTP: validan los schemas (422 antes de tocar la base) y delegan en `service.py`.
Todas las rutas exigen token (se registran con `get_current_user` en `app/main.py`). Las de
órdenes lo reciben además como parámetro para guardar su `id` como `user_uuid` (decisión D3).

No hay ninguna ruta para modificar o borrar ingredientes ni órdenes: el stock solo cambia
registrando órdenes de entrada o de salida.

Los endpoints son síncronos, como la sesión de SQLModel; FastAPI los ejecuta en su pool de hilos.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.inventory import service
from app.domains.inventory.schemas import (
    Country,
    IngredientCreate,
    IngredientEntryCreate,
    IngredientEntryRead,
    IngredientExitCreate,
    IngredientExitRead,
    IngredientRead,
    OrdersRead,
)
from app.domains.users.models import User

router = APIRouter(prefix="/inventory", tags=["inventory"])

INVALID = {422: {"description": "Entrada inválida (`invalid_request`, con `details` por campo)"}}
NOT_FOUND = {404: {"description": "No existe ningún ingrediente con ese ID (`ingredient_not_found`)"}}


@router.get("/products", response_model=list[IngredientRead], responses=INVALID)
def list_products(
    country: Annotated[Country | None, Query(description='Filtra por mercado: "CO" o "US"')] = None,
    session: Session = Depends(get_db),
) -> list[IngredientRead]:
    """Lista los ingredientes con su `current_stock` calculado (entradas − salidas)."""
    return service.list_ingredients(session, country)


@router.post(
    "/products",
    response_model=IngredientRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Ya existe un ingrediente con ese SKU (`duplicate_sku`)"}, **INVALID},
)
def create_product(data: IngredientCreate, session: Session = Depends(get_db)) -> IngredientRead:
    """Crea un ingrediente. Nace con `current_stock` 0; solo las entradas lo aumentan."""
    return service.create_ingredient(session, data)


@router.get("/products/{ingredient_id}", response_model=IngredientRead, responses={**NOT_FOUND, **INVALID})
def get_product(ingredient_id: int, session: Session = Depends(get_db)) -> IngredientRead:
    """Un ingrediente con su stock actual."""
    return service.get_ingredient(session, ingredient_id)


@router.post(
    "/orders/inbound",
    response_model=IngredientEntryRead,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND, **INVALID},
)
def create_inbound_order(
    data: IngredientEntryCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> IngredientEntryRead:
    """Registra una entrega de proveedor (`IngredientEntry`), que suma stock."""
    return service.create_entry(session, data, current_user.id)


@router.post(
    "/orders/outbound",
    response_model=IngredientExitRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "La salida dejaría el stock en negativo (`insufficient_stock`); no se escribe nada"},
        **NOT_FOUND,
        **INVALID,
    },
)
def create_outbound_order(
    data: IngredientExitCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> IngredientExitRead:
    """Registra un consumo o una merma (`IngredientExit`), que resta stock."""
    return service.create_exit(session, data, current_user.id)


@router.get("/orders", response_model=OrdersRead)
def list_orders(session: Session = Depends(get_db)) -> OrdersRead:
    """Lista todas las entradas y salidas con los datos de su ingrediente y su `user_uuid`."""
    return service.list_orders(session)

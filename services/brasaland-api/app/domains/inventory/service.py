"""Reglas de negocio del inventario sobre una sesión SQLModel (Supabase en producción).

- **El stock nunca se almacena:** `current_stock = SUMA(entradas) − SUMA(salidas)` por ingrediente,
  calculado por la base de datos en cada lectura. Ninguna función modifica un stock directamente:
  la única forma de cambiarlo es registrar una orden. El alcance es global por ingrediente
  (decisión D7): `location_id` se guarda, pero no parte el stock.
- **Sin stock negativo:** una salida que supere el stock disponible se rechaza con 400
  `insufficient_stock` antes de escribir nada.
- **Trazabilidad:** cada orden guarda el `user_uuid` del usuario autenticado, que llega del token.
- **Sin N+1:** cada listado es un número fijo de consultas, sin importar cuántas filas haya. El
  stock se suma en SQL con subconsultas agrupadas, y las órdenes se cargan con su ingrediente
  mediante un `join`. Solo se usa lo que exporta `sqlmodel` (`select`, `func`, `col`).

Las funciones devuelven schemas de `schemas.py`, nunca objetos ORM.
"""

from sqlmodel import Session, col, func, select

from app.core.errors import ApiError
from app.domains.inventory.models import Ingredient, IngredientEntry, IngredientExit
from app.domains.inventory.schemas import (
    Country,
    IngredientCreate,
    IngredientEntryCreate,
    IngredientEntryRead,
    IngredientExitCreate,
    IngredientExitRead,
    IngredientRead,
    IngredientSummary,
    OrdersRead,
)

# Decimales con los que se compara y se muestra el stock: evita que la suma de floats
# (p. ej. 0.1 + 0.2) rechace una salida que deja el stock exactamente a 0.
STOCK_DECIMALS = 6


# --- Errores ---------------------------------------------------------------------------------


def ingredient_not_found(ingredient_id: int) -> ApiError:
    return ApiError(404, "ingredient_not_found", f"No existe ningún ingrediente con el ID {ingredient_id}.")


def duplicate_sku(sku: str) -> ApiError:
    return ApiError(409, "duplicate_sku", f"Ya existe un ingrediente con el SKU «{sku}».")


def format_quantity(value: float) -> str:
    """52.0 → "52"; 12.5 → "12.5". Sin notación científica ni ceros sobrantes."""
    return f"{value:.{STOCK_DECIMALS}f}".rstrip("0").rstrip(".")


def insufficient_stock(name: str, available: float, requested: float) -> ApiError:
    # Mensaje del briefing (regla 2), traducido al español como el resto de la API (decisión D6).
    return ApiError(
        400,
        "insufficient_stock",
        f"Stock insuficiente para el ingrediente '{name}'. "
        f"Disponible: {format_quantity(available)}, solicitado: {format_quantity(requested)}.",
    )


# --- Stock -----------------------------------------------------------------------------------


def _stock_query():
    """SELECT Ingredient, current_stock: una sola consulta para cualquier número de ingredientes."""
    entries = (
        select(IngredientEntry.ingredient_id, func.sum(IngredientEntry.quantity).label("total"))
        .group_by(IngredientEntry.ingredient_id)
        .subquery()
    )
    exits = (
        select(IngredientExit.ingredient_id, func.sum(IngredientExit.quantity).label("total"))
        .group_by(IngredientExit.ingredient_id)
        .subquery()
    )
    current_stock = func.coalesce(entries.c.total, 0.0) - func.coalesce(exits.c.total, 0.0)
    return (
        select(Ingredient, current_stock.label("current_stock"))
        .outerjoin(entries, entries.c.ingredient_id == Ingredient.id)
        .outerjoin(exits, exits.c.ingredient_id == Ingredient.id)
    )


def _to_ingredient_read(ingredient: Ingredient, current_stock: float) -> IngredientRead:
    return IngredientRead(
        id=ingredient.id,
        name=ingredient.name,
        sku=ingredient.sku,
        unit=ingredient.unit,
        category=ingredient.category,
        country=ingredient.country,
        current_stock=round(float(current_stock), STOCK_DECIMALS),
    )


def list_ingredients(session: Session, country: Country | None = None) -> list[IngredientRead]:
    """Todos los ingredientes con su stock, por ID; `country` filtra por mercado (regla 3)."""
    query = _stock_query().order_by(col(Ingredient.id))
    if country is not None:
        query = query.where(Ingredient.country == country.value)
    return [_to_ingredient_read(ingredient, stock) for ingredient, stock in session.exec(query).all()]


def get_ingredient(session: Session, ingredient_id: int) -> IngredientRead:
    row = session.exec(_stock_query().where(Ingredient.id == ingredient_id)).first()
    if row is None:
        raise ingredient_not_found(ingredient_id)
    return _to_ingredient_read(*row)


def current_stock_of(session: Session, ingredient_id: int) -> float:
    """Stock actual de un ingrediente: suma de entradas menos suma de salidas, en SQL."""
    entered = session.exec(
        select(func.coalesce(func.sum(IngredientEntry.quantity), 0.0)).where(
            IngredientEntry.ingredient_id == ingredient_id
        )
    ).one()
    exited = session.exec(
        select(func.coalesce(func.sum(IngredientExit.quantity), 0.0)).where(IngredientExit.ingredient_id == ingredient_id)
    ).one()
    return round(float(entered) - float(exited), STOCK_DECIMALS)


# --- Ingredientes ----------------------------------------------------------------------------


def _sku_exists(session: Session, sku: str) -> bool:
    return session.exec(select(Ingredient.id).where(Ingredient.sku == sku)).first() is not None


def create_ingredient(session: Session, data: IngredientCreate) -> IngredientRead:
    """Crea un ingrediente. Siempre nace con stock 0: solo las entradas lo aumentan."""
    if _sku_exists(session, data.sku):
        raise duplicate_sku(data.sku)
    ingredient = Ingredient(**data.model_dump(mode="json"))
    session.add(ingredient)
    try:
        session.commit()
    except Exception:
        # Otra petición pudo crear el mismo SKU entre la comprobación y el commit: el índice único
        # de la base lo impide. Se responde 409 en ese caso; cualquier otro fallo sigue su curso (500).
        session.rollback()
        if _sku_exists(session, data.sku):
            raise duplicate_sku(data.sku) from None
        raise
    session.refresh(ingredient)
    return _to_ingredient_read(ingredient, 0)


# --- Órdenes ---------------------------------------------------------------------------------


def _summary(ingredient: Ingredient) -> IngredientSummary:
    return IngredientSummary(
        id=ingredient.id, name=ingredient.name, sku=ingredient.sku, unit=ingredient.unit, country=ingredient.country
    )


def _to_entry_read(entry: IngredientEntry, ingredient: Ingredient) -> IngredientEntryRead:
    return IngredientEntryRead(
        id=entry.id,
        ingredient_id=entry.ingredient_id,
        quantity=entry.quantity,
        supplier_name=entry.supplier_name,
        location_id=entry.location_id,
        created_at=entry.created_at,
        user_uuid=entry.user_uuid,
        ingredient=_summary(ingredient),
    )


def _to_exit_read(exit_: IngredientExit, ingredient: Ingredient) -> IngredientExitRead:
    return IngredientExitRead(
        id=exit_.id,
        ingredient_id=exit_.ingredient_id,
        quantity=exit_.quantity,
        reason=exit_.reason,
        location_id=exit_.location_id,
        created_at=exit_.created_at,
        user_uuid=exit_.user_uuid,
        ingredient=_summary(ingredient),
    )


def _existing_ingredient(session: Session, ingredient_id: int, *, lock: bool = False) -> Ingredient:
    query = select(Ingredient).where(Ingredient.id == ingredient_id)
    if lock:
        # SELECT ... FOR UPDATE: dos salidas simultáneas del mismo ingrediente se ejecutan una tras
        # otra, así que ninguna puede usar un stock que la otra ya consumió. SQLite lo ignora.
        query = query.with_for_update()
    ingredient = session.exec(query).first()
    if ingredient is None:
        raise ingredient_not_found(ingredient_id)
    return ingredient


def create_entry(session: Session, data: IngredientEntryCreate, user_uuid: str) -> IngredientEntryRead:
    """Registra una entrega de proveedor: suma stock. `user_uuid` es el del usuario autenticado."""
    ingredient = _existing_ingredient(session, data.ingredient_id)
    entry = IngredientEntry(**data.model_dump(), user_uuid=user_uuid)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return _to_entry_read(entry, ingredient)


def create_exit(session: Session, data: IngredientExitCreate, user_uuid: str) -> IngredientExitRead:
    """Registra un consumo o una merma: resta stock, pero nunca por debajo de 0.

    Comprueba el stock antes de escribir: si no alcanza, lanza 400 y la base no cambia.
    """
    ingredient = _existing_ingredient(session, data.ingredient_id, lock=True)
    available = current_stock_of(session, ingredient.id)
    if round(data.quantity, STOCK_DECIMALS) > available:
        session.rollback()  # Libera el bloqueo de la fila.
        raise insufficient_stock(ingredient.name, available, data.quantity)
    exit_ = IngredientExit(**data.model_dump(mode="json"), user_uuid=user_uuid)
    session.add(exit_)
    session.commit()
    session.refresh(exit_)
    return _to_exit_read(exit_, ingredient)


def list_orders(session: Session) -> OrdersRead:
    """Entradas y salidas con los datos de su ingrediente, de la más reciente a la más antigua.

    Dos consultas en total (una por tabla, cada una con su `join`), haya las órdenes que haya.
    """
    entries = session.exec(
        select(IngredientEntry, Ingredient)
        .join(Ingredient, IngredientEntry.ingredient_id == Ingredient.id)
        .order_by(col(IngredientEntry.created_at).desc(), col(IngredientEntry.id).desc())
    ).all()
    exits = session.exec(
        select(IngredientExit, Ingredient)
        .join(Ingredient, IngredientExit.ingredient_id == Ingredient.id)
        .order_by(col(IngredientExit.created_at).desc(), col(IngredientExit.id).desc())
    ).all()
    return OrdersRead(
        inbound=[_to_entry_read(entry, ingredient) for entry, ingredient in entries],
        outbound=[_to_exit_read(exit_, ingredient) for exit_, ingredient in exits],
    )

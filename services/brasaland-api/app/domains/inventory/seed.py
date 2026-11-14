"""`uv run --env-file .env seed-inventory`: carga en Supabase los datos semilla del briefing.

- **Ingredientes:** los 6 de la tabla del briefing, tal cual.
- **Entradas (4):** 2 de `BRS-BEEF-001` (50 kg y 30 kg) y 1 de otros dos ingredientes, con los
  proveedores que propone el briefing.
- **Salidas (3):** reducen el stock sin llegar a cero; una es de tipo `"waste"`.

Stock resultante: Falda de ternera 52, Costilla de cerdo 32, Chimichurri 20 y el resto 0.

Las órdenes llevan el `user_uuid` de un usuario real de TinyDB: el primer administrador activo
(se crea con `uv run create-admin`). La base de usuarios solo se lee.

Es idempotente: si ya hay ingredientes, no inserta nada. Si inserta, lo hace todo en una única
transacción, así que un fallo no deja una carga a medias.

`location_id` no está asignado a países en el briefing: se usa 1 para los ingredientes de Colombia
y 10 para los de EE. UU., como valores de ejemplo dentro del rango 1–14.
"""

import sys
from dataclasses import dataclass

from sqlmodel import Session, func, select

from app.core.config import ConfigError
from app.core.database import get_engine, init_db
from app.domains.inventory.models import Ingredient, IngredientEntry, IngredientExit
from app.domains.inventory.schemas import IngredientCreate, IngredientEntryCreate, IngredientExitCreate
from app.domains.users.database import AuthStore, get_auth_db_path
from app.domains.users.models import Role

CO_LOCATION_ID = 1
US_LOCATION_ID = 10

INGREDIENTS_SEED = [
    {"name": "Falda de ternera", "sku": "BRS-BEEF-001", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Costilla de cerdo", "sku": "BRS-PORK-001", "unit": "kg", "category": "meat", "country": "US"},
    {"name": "Chimichurri", "sku": "BRS-SAUCE-001", "unit": "litro", "category": "sauce", "country": "CO"},
    {"name": "Salsa BBQ de la casa", "sku": "BRS-SAUCE-002", "unit": "litro", "category": "sauce", "country": "US"},
    {"name": "Yuca", "sku": "BRS-PROD-001", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Caja para llevar (M)", "sku": "BRS-PKG-001", "unit": "unidad", "category": "packaging", "country": "CO"},
]

# Las órdenes referencian el ingrediente por SKU; el ID lo asigna la base al insertarlo.
ENTRIES_SEED = [
    {"sku": "BRS-BEEF-001", "quantity": 50.0, "supplier_name": "Carnes del Valle S.A.", "location_id": CO_LOCATION_ID},
    {"sku": "BRS-BEEF-001", "quantity": 30.0, "supplier_name": "Carnes del Valle S.A.", "location_id": CO_LOCATION_ID},
    {"sku": "BRS-PORK-001", "quantity": 40.0, "supplier_name": "MiamiMeat Co.", "location_id": US_LOCATION_ID},
    {"sku": "BRS-SAUCE-001", "quantity": 20.0, "supplier_name": "Salsas Artesanales Ltda.", "location_id": CO_LOCATION_ID},
]

EXITS_SEED = [
    {"sku": "BRS-BEEF-001", "quantity": 25.0, "reason": "consumption", "location_id": CO_LOCATION_ID},
    {"sku": "BRS-BEEF-001", "quantity": 3.0, "reason": "waste", "location_id": CO_LOCATION_ID},
    {"sku": "BRS-PORK-001", "quantity": 8.0, "reason": "consumption", "location_id": US_LOCATION_ID},
]


@dataclass(frozen=True)
class SeedResult:
    ingredients: int
    entries: int
    exits: int


def find_seed_user_uuid(store: AuthStore) -> str | None:
    """UUID del primer administrador activo de TinyDB (por fecha de alta), o None si no hay ninguno."""
    admins = [user for user in store.users.list() if user.role == Role.ADMIN and user.is_active]
    if not admins:
        return None
    return min(admins, key=lambda user: user.created_at).id


def seed(session: Session, user_uuid: str) -> SeedResult | None:
    """Inserta los datos semilla si no hay ningún ingrediente; devuelve None si ya los había.

    Valida todos los datos con los schemas de la API antes de escribir nada.
    """
    if session.exec(select(func.count()).select_from(Ingredient)).one() > 0:
        return None

    ingredients = [Ingredient(**IngredientCreate(**data).model_dump(mode="json")) for data in INGREDIENTS_SEED]
    session.add_all(ingredients)
    session.flush()  # Asigna los IDs sin cerrar la transacción.
    id_by_sku = {ingredient.sku: ingredient.id for ingredient in ingredients}

    def order_fields(data: dict) -> dict:
        fields = {key: value for key, value in data.items() if key != "sku"}
        return {**fields, "ingredient_id": id_by_sku[data["sku"]]}

    entries = [
        IngredientEntry(**IngredientEntryCreate(**order_fields(data)).model_dump(), user_uuid=user_uuid)
        for data in ENTRIES_SEED
    ]
    exits = [
        IngredientExit(**IngredientExitCreate(**order_fields(data)).model_dump(mode="json"), user_uuid=user_uuid)
        for data in EXITS_SEED
    ]
    session.add_all(entries + exits)
    session.commit()
    return SeedResult(ingredients=len(ingredients), entries=len(entries), exits=len(exits))


def _error(message: str) -> None:
    """Los errores van a stderr; stdout queda para el resultado."""
    print(message, file=sys.stderr)


def main(engine=None, store: AuthStore | None = None) -> int:
    """Devuelve el código de salida del proceso: 0 si termina bien y 1 si hay un error."""
    own_store = store is None
    try:
        if store is None:
            store = AuthStore.from_path(get_auth_db_path())
        user_uuid = find_seed_user_uuid(store)
    except Exception as error:  # noqa: BLE001 — archivo ilegible o JSON corrupto: no se toca Supabase.
        _error(f"No se pudo leer la base de usuarios ({type(error).__name__}). No se insertó nada.")
        return 1
    finally:
        if own_store and store is not None:
            store.close()
    if user_uuid is None:
        _error(
            "No hay ningún administrador activo en la base de usuarios: las órdenes semilla necesitan "
            "el user_uuid de un usuario real. Ejecuta primero `uv run create-admin`."
        )
        return 1

    try:
        engine = engine if engine is not None else get_engine()
        init_db(engine)
        with Session(engine) as session:
            result = seed(session, user_uuid)
    except ConfigError as error:
        _error(f"{error} Añádela a .env y ejecuta `uv run --env-file .env seed-inventory`.")
        return 1
    except Exception as error:  # noqa: BLE001 — conexión rechazada, credenciales, red...
        # Solo el tipo de error: el mensaje del driver puede incluir el host o el usuario de la conexión.
        _error(
            f"No se pudo cargar el inventario en la base de datos ({type(error).__name__}). "
            "Revisa DATABASE_URL y la conexión. La carga es una única transacción: no quedó nada a medias."
        )
        return 1

    if result is None:
        print("El inventario ya tenía ingredientes: no se insertó nada.")
    else:
        print(
            f"Inventario sembrado: {result.ingredients} ingredientes, {result.entries} entradas y "
            f"{result.exits} salidas (user_uuid {user_uuid})."
        )
    return 0

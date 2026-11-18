"""Carga volumen realista para medir el rendimiento de la API (tarea de caching) y lo retira después.

Uso (desde la raíz del repositorio, con el entorno de la API y su .env, que tiene DATABASE_URL):
    uv run --project services/brasaland-api --env-file services/brasaland-api/.env python scripts/seed_volume.py
    uv run --project services/brasaland-api --env-file services/brasaland-api/.env python scripts/seed_volume.py --clear

Qué carga (con una semilla aleatoria fija: dos ejecuciones generan los mismos datos):
- **Inventario (Supabase):** 150 ingredientes (75 de Colombia con nombre en español y 75 de Estados
  Unidos en inglés, en las 6 categorías) y unas 20 000 órdenes de los últimos 12 meses. Las entradas
  son entregas semanales de los proveedores reales del directorio (mismo país y categoría
  equivalente); las salidas son consumos diarios y alguna merma. Se simulan en orden cronológico,
  así que ninguna salida deja el stock en negativo.
- **Incidencias (TinyDB):** 10 000 incidencias de los últimos 12 meses en las 15 sedes, con
  categoría, origen, título y descripción coherentes entre sí. Las antiguas están casi todas
  resueltas o descartadas; las recientes, abiertas o en curso.

Marcas para poder retirarlo todo con --clear sin tocar los datos reales:
- los ingredientes llevan el SKU `VOL-…` (las órdenes se borran a través de su ingrediente);
- cada incidencia queda anotada en `incident_seed_log` con un `source_id` `VOL-…` (las del CSV
  histórico usan `BRS-…`).

Convención solo de esta semilla: los locales 1–9 son de Colombia y los 10–14 de Estados Unidos
(9 y 5 sedes, como en el gestor de incidencias). El inventario todavía no asocia locales a países.

Ejecutarlo con la API parada: las incidencias se escriben en bloque en brasaland-db.json, y la API
no protege ese archivo frente a escrituras de otro proceso.
"""

import argparse
import random
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "brasaland-api"))

from sqlmodel import Session, col, delete, func, select  # noqa: E402
from tinydb import Query, TinyDB  # noqa: E402
from tinydb.table import Document  # noqa: E402

from app.core.database import get_engine, init_db  # noqa: E402
from app.core.storage import get_brasaland_db_path, open_db  # noqa: E402
from app.domains.incidents.incident_repository import INCIDENTS_TABLE, SEED_LOG_TABLE  # noqa: E402
from app.domains.incidents.models import Branch, IncidentCategory, IncidentOrigin, IncidentRecord, IncidentStatus  # noqa: E402
from app.domains.inventory.models import Ingredient, IngredientEntry, IngredientExit  # noqa: E402
from app.domains.inventory.seed import find_seed_user_uuid  # noqa: E402
from app.domains.users.database import AuthStore, get_auth_db_path  # noqa: E402

SKU_PREFIX = "VOL-"
SOURCE_PREFIX = "VOL-"
RANDOM_SEED = 2026
INCIDENT_COUNT = 10_000
DAYS = 365

# --- Inventario ------------------------------------------------------------------------------

# Por categoría: unidad, consumo diario típico de un ingrediente en toda la cadena (en esa unidad)
# y pares (nombre en Colombia, nombre en Estados Unidos).
CATALOG: dict[str, tuple[str, float, list[tuple[str, str]]]] = {
    "meat": ("kg", 6.0, [
        ("Punta de anca", "Picanha"), ("Falda de res", "Beef skirt steak"), ("Costilla de res", "Beef short ribs"),
        ("Lomo de cerdo", "Pork loin"), ("Costilla de cerdo", "Pork ribs"), ("Chorizo santarrosano", "Grilling chorizo"),
        ("Morcilla", "Blood sausage"), ("Pechuga de pollo", "Chicken breast"), ("Muslo de pollo", "Chicken thigh"),
        ("Alitas de pollo", "Chicken wings"), ("Chicharrón", "Pork belly"), ("Solomillo de res", "Beef tenderloin"),
        ("Carne molida", "Ground beef"),
    ]),
    "produce": ("kg", 4.0, [
        ("Papa criolla", "Yellow potato"), ("Yuca", "Cassava"), ("Plátano maduro", "Ripe plantain"),
        ("Plátano verde", "Green plantain"), ("Tomate chonto", "Roma tomato"), ("Cebolla cabezona", "White onion"),
        ("Cebolla larga", "Green onion"), ("Aguacate Hass", "Hass avocado"), ("Limón Tahití", "Persian lime"),
        ("Lechuga crespa", "Green leaf lettuce"), ("Mazorca", "Sweet corn"), ("Cilantro", "Cilantro"),
        ("Ají dulce", "Sweet pepper"),
    ]),
    "sauce": ("litro", 1.5, [
        ("Chimichurri de la casa", "House chimichurri"), ("Ají picante", "Hot pepper sauce"),
        ("Salsa BBQ", "BBQ sauce"), ("Salsa de ajo", "Garlic sauce"), ("Hogao", "Tomato and onion sofrito"),
        ("Guacamole", "Guacamole"), ("Salsa rosada", "Pink sauce"), ("Mayonesa", "Mayonnaise"),
        ("Mostaza", "Mustard"), ("Salsa de tomate", "Ketchup"), ("Vinagreta", "Vinaigrette"),
        ("Aceite de oliva", "Olive oil"),
    ]),
    "beverage": ("unidad", 14.0, [
        ("Gaseosa 350 ml", "Soda can 12 oz"), ("Agua sin gas 600 ml", "Still water 20 oz"),
        ("Agua con gas 600 ml", "Sparkling water 20 oz"), ("Jugo de lulo", "Lulo juice"),
        ("Jugo de maracuyá", "Passion fruit juice"), ("Limonada de coco", "Coconut lemonade"),
        ("Cerveza nacional", "Domestic beer"), ("Cerveza importada", "Imported beer"),
        ("Té helado", "Iced tea"), ("Malta", "Malt soda"), ("Kumis", "Cultured milk drink"),
        ("Avena fría", "Cold oat drink"), ("Café tinto", "Drip coffee"),
    ]),
    "packaging": ("unidad", 25.0, [
        ("Caja para llevar grande", "Large to-go box"), ("Caja para llevar pequeña", "Small to-go box"),
        ("Vaso desechable 12 oz", "12 oz cup"), ("Tapa para vaso", "Cup lid"), ("Bolsa de papel", "Paper bag"),
        ("Servilleta", "Napkin"), ("Cubiertos compostables", "Compostable cutlery"),
        ("Contenedor de salsa", "Sauce cup"), ("Pitillo de papel", "Paper straw"),
        ("Papel aluminio", "Aluminum foil"), ("Bandeja de cartón", "Cardboard tray"),
        ("Etiqueta de pedido", "Order label"),
    ]),
    "cleaning": ("litro", 1.0, [
        ("Desengrasante de parrilla", "Grill degreaser"), ("Detergente líquido", "Liquid detergent"),
        ("Desinfectante de superficies", "Surface sanitizer"), ("Jabón de manos", "Hand soap"),
        ("Limpiavidrios", "Glass cleaner"), ("Hipoclorito", "Bleach"),
        ("Abrillantador de lavavajillas", "Dishwasher rinse aid"), ("Limpiador de pisos", "Floor cleaner"),
        ("Alcohol antiséptico", "Rubbing alcohol"), ("Quitasarro", "Descaler"),
        ("Neutralizador de olores", "Odor neutralizer"), ("Limpiador de acero", "Stainless steel cleaner"),
    ]),
}

# Equivalencias con el directorio de proveedores (las mismas que uis/backoffice/lib/inventory-suppliers.ts).
SUPPLIER_CATEGORY = {
    "meat": "carne",
    "produce": "verduras_y_hortalizas",
    "sauce": "salsas_y_condimentos",
    "beverage": "bebidas",
    "packaging": "packaging",
    "cleaning": "productos_limpieza",
}
SUPPLIER_COUNTRY = {"CO": "Colombia", "US": "USA"}
LOCATIONS = {"CO": list(range(1, 10)), "US": list(range(10, 15))}
# Probabilidad de que una salida sea merma: más alta en lo perecedero.
WASTE_RATE = {"meat": 0.06, "produce": 0.12, "sauce": 0.05, "beverage": 0.01, "packaging": 0.02, "cleaning": 0.01}


@dataclass
class InventoryResult:
    ingredients: int
    entries: int
    exits: int


def supplier_names(db: TinyDB) -> dict[tuple[str, str], list[str]]:
    """Proveedores del directorio por (país del inventario, categoría del inventario).

    Se usan todos, también los suspendidos: el histórico incluye entregas de antes de la suspensión.
    """
    suppliers = db.table("suppliers", cache_size=0).all()
    names: dict[tuple[str, str], list[str]] = {}
    for country, supplier_country in SUPPLIER_COUNTRY.items():
        for category, supplier_category in SUPPLIER_CATEGORY.items():
            names[(country, category)] = sorted(
                s["name"] for s in suppliers
                if s["country"] == supplier_country and supplier_category in s["categories"]
            )
    return names


def build_inventory(rng: random.Random, suppliers: dict[tuple[str, str], list[str]], user_uuid: str, now: datetime):
    """Ingredientes y, por cada uno, sus órdenes simuladas día a día (sin stock negativo)."""
    plan: list[tuple[Ingredient, list[IngredientEntry], list[IngredientExit]]] = []
    for category, (unit, daily, names) in CATALOG.items():
        for country in ("CO", "US"):
            for number, pair in enumerate(names, start=1):
                name = pair[0] if country == "CO" else pair[1]
                ingredient = Ingredient(
                    name=name,
                    sku=f"{SKU_PREFIX}{country}-{category.upper()}-{number:03d}",
                    unit=unit,
                    category=category,
                    country=country,
                )
                vendors = suppliers.get((country, category)) or ["Proveedor sin registrar"]
                # Cada ingrediente tiene su propio ritmo: unos se piden mucho y otros poco.
                scale = rng.uniform(0.4, 1.6)
                delivery_weekday = rng.randrange(7)
                stock = 0.0
                entries: list[IngredientEntry] = []
                exits: list[IngredientExit] = []
                start = now - timedelta(days=DAYS)
                for day in range(DAYS):
                    date = start + timedelta(days=day)
                    # Una entrega a la semana, de algo más de lo que se consume en esos 7 días.
                    if day % 7 == delivery_weekday:
                        quantity = round(daily * scale * 7 * rng.uniform(0.95, 1.25), 1)
                        entries.append(IngredientEntry(
                            quantity=quantity,
                            supplier_name=rng.choice(vendors),
                            location_id=rng.choice(LOCATIONS[country]),
                            created_at=date.replace(hour=rng.randint(6, 9), minute=rng.randrange(60)),
                            user_uuid=user_uuid,
                        ))
                        stock += quantity
                    # Una salida cada 4 días de media, que cubre ~4 días de consumo; solo si queda
                    # stock suficiente (la API tampoco permitiría dejarlo en negativo).
                    if rng.random() < 0.25:
                        is_waste = rng.random() < WASTE_RATE[category]
                        quantity = round(daily * scale * rng.uniform(2.5, 5.5) * (0.3 if is_waste else 1), 1)
                        if quantity <= 0 or quantity > stock:
                            continue
                        exits.append(IngredientExit(
                            quantity=quantity,
                            reason="waste" if is_waste else "consumption",
                            location_id=rng.choice(LOCATIONS[country]),
                            created_at=date.replace(hour=rng.randint(11, 22), minute=rng.randrange(60)),
                            user_uuid=user_uuid,
                        ))
                        stock = round(stock - quantity, 3)
                plan.append((ingredient, entries, exits))
    return plan


def seed_inventory(session: Session, plan) -> InventoryResult | None:
    """Inserta el plan en una sola transacción. None si ya había ingredientes de volumen."""
    if session.exec(select(func.count()).select_from(Ingredient).where(col(Ingredient.sku).startswith(SKU_PREFIX))).one():
        return None
    session.add_all([ingredient for ingredient, _, _ in plan])
    session.flush()  # asigna los id de los ingredientes
    entries = exits = 0
    for ingredient, ingredient_entries, ingredient_exits in plan:
        for order in (*ingredient_entries, *ingredient_exits):
            order.ingredient_id = ingredient.id
        session.add_all(ingredient_entries)
        session.add_all(ingredient_exits)
        entries += len(ingredient_entries)
        exits += len(ingredient_exits)
    session.commit()
    return InventoryResult(ingredients=len(plan), entries=entries, exits=exits)


def clear_inventory(session: Session) -> int:
    """Borra los ingredientes `VOL-…` y sus órdenes en una transacción. Devuelve cuántos ingredientes."""
    ids = select(Ingredient.id).where(col(Ingredient.sku).startswith(SKU_PREFIX))
    count = session.exec(select(func.count()).select_from(ids.subquery())).one()
    session.exec(delete(IngredientEntry).where(col(IngredientEntry.ingredient_id).in_(ids)))
    session.exec(delete(IngredientExit).where(col(IngredientExit.ingredient_id).in_(ids)))
    session.exec(delete(Ingredient).where(col(Ingredient.sku).startswith(SKU_PREFIX)))
    session.commit()
    return count


# --- Incidencias -----------------------------------------------------------------------------

# Peso de cada sede según su volumen (Medellín, la sede original, tiene más locales y más tráfico).
BRANCH_WEIGHTS = {
    Branch.CENTRAL: 3, Branch.MEDELLIN_CENTRO: 10, Branch.MEDELLIN_LAURELES: 9, Branch.MEDELLIN_ENVIGADO: 8,
    Branch.MEDELLIN_BELLO: 6, Branch.MEDELLIN_ITAGUI: 6, Branch.BOGOTA_CHAPINERO: 8, Branch.BOGOTA_USAQUEN: 7,
    Branch.CALI_GRANADA: 6, Branch.BARRANQUILLA_NORTE: 5, Branch.MIAMI_DORAL: 7, Branch.MIAMI_HIALEAH: 6,
    Branch.MIAMI_KENDALL: 5, Branch.ORLANDO_INTERNATIONAL: 5, Branch.FORT_LAUDERDALE: 4,
}

# Por categoría: peso, orígenes posibles y plantillas (título, descripción). {sede} y {detalle} se
# rellenan al generar.
INCIDENT_TEMPLATES: dict[IncidentCategory, tuple[int, list[IncidentOrigin], list[tuple[str, str]]]] = {
    IncidentCategory.CUSTOMER_COMPLAINT: (30, [IncidentOrigin.CUSTOMER], [
        ("Carne servida fuera del término pedido", "El cliente pidió {detalle} y llegó a la mesa en otro término. Se repuso el plato en {sede}."),
        ("Tiempo de espera excesivo", "Una mesa esperó más de 40 minutos por {detalle} en hora pico en {sede}."),
        ("Plato frío al servir", "El cliente reporta que {detalle} llegó frío. Se revisa la ventana de despacho de {sede}."),
        ("Cobro incorrecto en la cuenta", "La cuenta incluía {detalle} que la mesa no pidió. Se corrigió en caja en {sede}."),
    ]),
    IncidentCategory.EQUIPMENT_FAILURE: (16, [IncidentOrigin.BRANCH, IncidentOrigin.INTERNAL], [
        ("Parrilla principal sin temperatura", "La parrilla no pasa de 180 °C durante {detalle}. Se pidió revisión técnica en {sede}."),
        ("Cuarto frío por encima de 5 °C", "El termómetro del cuarto frío marcó 7 °C durante {detalle}. Se trasladó la carne en {sede}."),
        ("Extractor de humo detenido", "El extractor se detuvo durante {detalle}; la cocina de {sede} operó con una sola línea."),
        ("Freidora con fuga de aceite", "La freidora pierde aceite por la válvula de drenaje desde {detalle} en {sede}."),
    ]),
    IncidentCategory.SUPPLY_ISSUE: (16, [IncidentOrigin.BRANCH, IncidentOrigin.INTERNAL], [
        ("Entrega de carne incompleta", "Llegó la mitad de la punta de anca pedida para {detalle}. {sede} ajustó el menú del día."),
        ("Producto recibido fuera de especificación", "El lote de verduras de {detalle} llegó maltratado y se devolvió al proveedor en {sede}."),
        ("Desabastecimiento de bebidas", "{sede} se quedó sin gaseosa durante {detalle} por un pedido no confirmado."),
        ("Cambio de precio sin aviso", "La factura de {detalle} trae un precio mayor al acordado. Compras lo revisa con {sede}."),
    ]),
    IncidentCategory.STAFF_ISSUE: (9, [IncidentOrigin.INTERNAL, IncidentOrigin.BRANCH], [
        ("Turno sin cubrir", "Faltaron dos personas en cocina durante {detalle} en {sede}; se movió personal de sala."),
        ("Personal nuevo sin inducción", "Un auxiliar empezó en {sede} sin la inducción de seguridad alimentaria durante {detalle}."),
        ("Retraso en la apertura", "{sede} abrió 30 minutos tarde durante {detalle} porque no llegó quien tenía las llaves."),
    ]),
    IncidentCategory.FACILITY_ISSUE: (8, [IncidentOrigin.BRANCH], [
        ("Fuga de agua en el baño de clientes", "Se detectó una fuga en el baño de clientes de {sede} durante {detalle}; se cerró el acceso."),
        ("Aire acondicionado del salón averiado", "El aire del salón de {sede} dejó de enfriar durante {detalle}."),
        ("Iluminación de la terraza apagada", "La terraza de {sede} quedó sin luz durante {detalle}; se reubicaron mesas."),
    ]),
    IncidentCategory.POS_SYSTEM: (9, [IncidentOrigin.BRANCH, IncidentOrigin.INTERNAL], [
        ("Datáfono sin conexión", "Los pagos con tarjeta fallaron durante {detalle} en {sede}; solo se aceptó efectivo."),
        ("Comandas que no llegan a cocina", "El POS de {sede} dejó de enviar comandas a la impresora de cocina durante {detalle}."),
        ("Cierre de caja con descuadre", "El cierre de {detalle} en {sede} no cuadra con el reporte del POS."),
    ]),
    IncidentCategory.DELIVERY_ISSUE: (8, [IncidentOrigin.CUSTOMER, IncidentOrigin.BRANCH], [
        ("Pedido a domicilio incompleto", "El cliente recibió el pedido de {detalle} sin las bebidas. Se reenvió desde {sede}."),
        ("Domicilio entregado tarde", "Un domicilio de {detalle} llegó con más de una hora de retraso desde {sede}."),
        ("Pedido entregado en otra dirección", "El repartidor dejó el pedido de {detalle} en una dirección equivocada; {sede} lo repuso."),
    ]),
    IncidentCategory.OTHER: (4, [IncidentOrigin.INTERNAL, IncidentOrigin.CUSTOMER], [
        ("Objeto olvidado por un cliente", "Un cliente dejó sus pertenencias en {sede} durante {detalle}; se guardaron en caja."),
        ("Reclamo en redes sociales", "Una publicación sobre {sede} durante {detalle} pide respuesta del equipo de marketing."),
    ]),
}

DETAILS = [
    "el almuerzo", "la cena del viernes", "el turno de la noche", "el brunch del domingo", "un evento corporativo",
    "la hora pico del mediodía", "el cierre", "la apertura", "un partido de fútbol", "un pedido grande",
]


def incident_status(rng: random.Random, age_days: int) -> IncidentStatus:
    """Estado según la antigüedad: lo reciente sigue abierto; lo antiguo, casi todo cerrado."""
    if age_days < 7:
        weights = (55, 30, 12, 3)
    elif age_days < 30:
        weights = (20, 25, 45, 10)
    else:
        weights = (3, 2, 80, 15)
    return rng.choices(
        (IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED, IncidentStatus.DISCARDED), weights
    )[0]


def branch_label(branch: Branch) -> str:
    return "la oficina central" if branch is Branch.CENTRAL else branch.value.replace("_", " ").title()


def build_incidents(rng: random.Random, count: int, now: datetime) -> list[tuple[IncidentRecord, datetime]]:
    categories = list(INCIDENT_TEMPLATES)
    category_weights = [INCIDENT_TEMPLATES[category][0] for category in categories]
    branches = list(BRANCH_WEIGHTS)
    branch_weights = list(BRANCH_WEIGHTS.values())
    incidents = []
    for _ in range(count):
        category = rng.choices(categories, category_weights)[0]
        _, origins, templates = INCIDENT_TEMPLATES[category]
        branch = rng.choices(branches, branch_weights)[0]
        # Más incidencias en los meses recientes: la cadena crece.
        age_days = int(DAYS * (rng.random() ** 1.4))
        created_at = (now - timedelta(days=age_days)).replace(hour=rng.randint(8, 23), minute=rng.randrange(60))
        if created_at > now:  # una incidencia de hoy no puede tener una hora futura
            created_at -= timedelta(days=1)
        title, description = rng.choice(templates)
        record = IncidentRecord(
            title=title,
            description=description.format(sede=branch_label(branch), detalle=rng.choice(DETAILS)),
            category=category,
            origin=rng.choice(origins),
            branch=branch,
            status=incident_status(rng, age_days),
        )
        incidents.append((record, created_at))
    return incidents


def seed_incidents(db: TinyDB, incidents: list[tuple[IncidentRecord, datetime]]) -> int | None:
    """Inserta en bloque (una sola escritura del archivo por tabla). None si ya estaban cargadas."""
    table = db.table(INCIDENTS_TABLE, cache_size=0)
    seed_log = db.table(SEED_LOG_TABLE, cache_size=0)
    if seed_log.contains(Query().source_id.test(lambda value: value.startswith(SOURCE_PREFIX))):
        return None
    next_id = max((document.doc_id for document in table.all()), default=0) + 1
    next_log_id = max((document.doc_id for document in seed_log.all()), default=0) + 1
    documents, log_documents = [], []
    for offset, (record, created_at) in enumerate(incidents):
        data = record.model_dump(mode="json")
        data["created_at"] = data["updated_at"] = created_at.isoformat()
        documents.append(Document(data, doc_id=next_id + offset))
        log_documents.append(Document(
            {"source_id": f"{SOURCE_PREFIX}{offset + 1:06d}", "incident_id": next_id + offset},
            doc_id=next_log_id + offset,
        ))
    table.insert_multiple(documents)
    seed_log.insert_multiple(log_documents)
    return len(documents)


def clear_incidents(db: TinyDB) -> int:
    """Borra las incidencias anotadas con `VOL-…` en el log y sus anotaciones."""
    seed_log = db.table(SEED_LOG_TABLE, cache_size=0)
    marked = seed_log.search(Query().source_id.test(lambda value: value.startswith(SOURCE_PREFIX)))
    ids = [document["incident_id"] for document in marked]
    if ids:
        db.table(INCIDENTS_TABLE, cache_size=0).remove(doc_ids=ids)
        seed_log.remove(doc_ids=[document.doc_id for document in marked])
    return len(ids)


# --- Programa --------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Carga o retira el volumen de prueba de la tarea de caching.")
    parser.add_argument("--clear", action="store_true", help="retira todo lo cargado por este script")
    args = parser.parse_args(argv)

    db_path = get_brasaland_db_path()
    db = open_db(db_path)
    engine = get_engine()
    try:
        if args.clear:
            with Session(engine) as session:
                ingredients = clear_inventory(session)
            incidents = clear_incidents(db)
            print(f"Retirados {ingredients} ingredientes VOL- (con sus órdenes) y {incidents} incidencias de {db_path}.")
            return 0

        store = AuthStore.from_path(get_auth_db_path())
        try:
            user_uuid = find_seed_user_uuid(store)
        finally:
            store.close()
        if user_uuid is None:
            print("Error: no hay ningún administrador activo (ejecuta `uv run create-admin`).", file=sys.stderr)
            return 1

        rng = random.Random(RANDOM_SEED)
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        init_db(engine)
        with Session(engine) as session:
            inventory = seed_inventory(session, build_inventory(rng, supplier_names(db), user_uuid, now))
        if inventory is None:
            print("Inventario: ya había ingredientes VOL-, no se insertó nada.")
        else:
            print(f"Inventario: {inventory.ingredients} ingredientes, {inventory.entries} entradas y {inventory.exits} salidas.")

        inserted = seed_incidents(db, build_incidents(rng, INCIDENT_COUNT, now))
        if inserted is None:
            print("Incidencias: ya estaban cargadas, no se insertó nada.")
        else:
            print(f"Incidencias: {inserted} insertadas en {db_path}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

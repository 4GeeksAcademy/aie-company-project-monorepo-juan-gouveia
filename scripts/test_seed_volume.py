"""Pruebas del seeder de volumen (scripts/seed_volume.py).

No tocan Supabase ni el archivo real: el inventario usa un SQLite temporal y las incidencias un
TinyDB temporal. Se ejecutan con el entorno de la API, desde la raíz del repositorio:
    uv run --project services/brasaland-api python -m unittest scripts/test_seed_volume.py
"""

import random
import sys
import tempfile
import unittest
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import seed_volume as seed  # noqa: E402
from sqlmodel import Session, create_engine, func, select  # noqa: E402

from app.core.database import init_db  # noqa: E402
from app.core.storage import open_db  # noqa: E402
from app.domains.incidents.incident_repository import IncidentRepository  # noqa: E402
from app.domains.incidents.models import IncidentCreate  # noqa: E402
from app.domains.inventory.models import Ingredient, IngredientEntry, IngredientExit  # noqa: E402

NOW = datetime(2026, 11, 18, tzinfo=UTC)
USER = "00000000-0000-4000-8000-000000000000"
SUPPLIERS = {(country, category): [f"Proveedor {country} {category}"] for country in ("CO", "US") for category in seed.CATALOG}


def build_plan():
    return seed.build_inventory(random.Random(seed.RANDOM_SEED), SUPPLIERS, USER, NOW)


class BuildInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = build_plan()

    def test_genera_150_ingredientes_con_sku_unico_y_marcado(self):
        skus = [ingredient.sku for ingredient, _, _ in self.plan]
        self.assertEqual(len(skus), 150)
        self.assertEqual(len(set(skus)), 150)
        self.assertTrue(all(sku.startswith(seed.SKU_PREFIX) for sku in skus))

    def test_mitad_de_cada_pais_y_las_seis_categorias(self):
        by_country = defaultdict(set)
        for ingredient, _, _ in self.plan:
            by_country[ingredient.country].add(ingredient.category)
        self.assertEqual({country: len(categories) for country, categories in by_country.items()}, {"CO": 6, "US": 6})
        self.assertEqual(sum(1 for ingredient, _, _ in self.plan if ingredient.country == "CO"), 75)

    def test_unas_veinte_mil_ordenes(self):
        total = sum(len(entries) + len(exits) for _, entries, exits in self.plan)
        self.assertGreater(total, 18_000)
        self.assertLess(total, 24_000)

    def test_ninguna_salida_deja_el_stock_en_negativo(self):
        for ingredient, entries, exits in self.plan:
            stock = 0.0
            for order in sorted((*entries, *exits), key=lambda order: order.created_at):
                stock += order.quantity if isinstance(order, IngredientEntry) else -order.quantity
                self.assertGreaterEqual(round(stock, 3), 0, ingredient.sku)

    def test_ordenes_coherentes_con_el_pais_y_el_proveedor(self):
        for ingredient, entries, exits in self.plan:
            for order in (*entries, *exits):
                self.assertIn(order.location_id, seed.LOCATIONS[ingredient.country])
                self.assertEqual(order.user_uuid, USER)
                self.assertGreater(order.quantity, 0)
            for entry in entries:
                self.assertEqual(entry.supplier_name, f"Proveedor {ingredient.country} {ingredient.category}")
            for order_exit in exits:
                self.assertIn(order_exit.reason, ("consumption", "waste"))

    def test_es_determinista(self):
        first = [(i.sku, len(e), len(x)) for i, e, x in self.plan]
        second = [(i.sku, len(e), len(x)) for i, e, x in build_plan()]
        self.assertEqual(first, second)


class InventoryDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine(f"sqlite:///{Path(self.tmp.name) / 'inventory.db'}")
        init_db(self.engine)
        with Session(self.engine) as session:
            real = Ingredient(name="Falda de ternera", sku="BRS-BEEF-001", unit="kg", category="meat", country="CO")
            session.add(real)
            session.flush()
            session.add(IngredientEntry(ingredient_id=real.id, quantity=10, supplier_name="Real", location_id=1, user_uuid=USER))
            session.commit()

    def tearDown(self):
        self.engine.dispose()
        self.tmp.cleanup()

    def count(self, model) -> int:
        with Session(self.engine) as session:
            return session.exec(select(func.count()).select_from(model)).one()

    def test_carga_y_es_idempotente(self):
        plan = build_plan()
        with Session(self.engine) as session:
            result = seed.seed_inventory(session, plan)
        self.assertEqual(result.ingredients, 150)
        self.assertEqual(self.count(Ingredient), 151)
        self.assertEqual(self.count(IngredientEntry), result.entries + 1)
        self.assertEqual(self.count(IngredientExit), result.exits)
        with Session(self.engine) as session:
            self.assertIsNone(seed.seed_inventory(session, build_plan()))
        self.assertEqual(self.count(Ingredient), 151)

    def test_clear_retira_solo_lo_marcado(self):
        with Session(self.engine) as session:
            seed.seed_inventory(session, build_plan())
        with Session(self.engine) as session:
            self.assertEqual(seed.clear_inventory(session), 150)
        self.assertEqual(self.count(Ingredient), 1)
        self.assertEqual(self.count(IngredientEntry), 1)
        self.assertEqual(self.count(IngredientExit), 0)


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "brasaland-db.json"
        repository = IncidentRepository.from_path(self.path)
        repository.create(IncidentCreate(
            title="Incidencia real", description="No debe tocarse", category="other", origin="internal", branch="central",
        ))
        repository.close()

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, count=500):
        return seed.build_incidents(random.Random(seed.RANDOM_SEED), count, NOW)

    def test_incidencias_validas_y_estado_segun_antiguedad(self):
        incidents = self.build(2000)
        recent = [record.status for record, created_at in incidents if (NOW - created_at).days < 7]
        old = [record.status for record, created_at in incidents if (NOW - created_at).days >= 30]
        self.assertGreater(recent.count("open") / len(recent), 0.4)
        self.assertGreater(old.count("resolved") / len(old), 0.7)
        for record, created_at in incidents:
            self.assertLessEqual(created_at, NOW)
            self.assertIn(record.origin, seed.INCIDENT_TEMPLATES[record.category][1])

    def test_carga_en_bloque_es_idempotente_y_clear_respeta_las_reales(self):
        db = open_db(self.path)
        try:
            self.assertEqual(seed.seed_incidents(db, self.build()), 500)
            self.assertIsNone(seed.seed_incidents(db, self.build()))
        finally:
            db.close()

        repository = IncidentRepository.from_path(self.path)
        self.assertEqual(repository.summary().total, 501)
        repository.close()

        db = open_db(self.path)
        try:
            self.assertEqual(seed.clear_incidents(db), 500)
        finally:
            db.close()
        repository = IncidentRepository.from_path(self.path)
        [remaining] = repository.list()
        self.assertEqual(remaining.title, "Incidencia real")
        repository.close()


if __name__ == "__main__":
    unittest.main()

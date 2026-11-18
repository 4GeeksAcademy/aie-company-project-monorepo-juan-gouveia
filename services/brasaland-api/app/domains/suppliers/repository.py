"""Acceso a los proveedores guardados en TinyDB.

Es la única pieza que conoce TinyDB: el router y el seeder trabajan con modelos Pydantic.
"""

# Las anotaciones se evalúan en diferido: dentro de la clase, `list` es el método y no el tipo.
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from tinydb import TinyDB
from tinydb.table import Document

from app.core.storage import lock_for
from app.domains.suppliers.database import SUPPLIERS_TABLE, open_db
from app.domains.suppliers.exceptions import DuplicateSupplierError
from app.domains.suppliers.models import Category, Country, Supplier, SupplierCreate, SupplierStatus


def normalize_name(name: str) -> str:
    """Clave para comparar nombres: sin espacios extremos y sin distinguir mayúsculas."""
    return name.strip().casefold()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SupplierRepository:
    def __init__(self, db: TinyDB, lock: RLock | None = None):
        self._db = db
        # Sin caché de consultas: así se ven también los cambios de `uv run seed` hechos desde otro proceso.
        self._table = db.table(SUPPLIERS_TABLE, cache_size=0)
        # TinyDB no es seguro entre hilos, y FastAPI ejecuta los endpoints síncronos en un pool.
        # El bloqueo es el del archivo: lo comparte el gestor de incidencias, que escribe en el mismo.
        self._lock = lock or RLock()

    @classmethod
    def from_path(cls, path: Path) -> "SupplierRepository":
        return cls(open_db(path), lock_for(path))

    def close(self) -> None:
        self._db.close()

    # --- Lectura ---------------------------------------------------------------------------

    def list(self, country: Country | None = None, category: Category | None = None) -> list[Supplier]:
        """Todos los proveedores, por ID; los filtros se combinan (por ejemplo, carne en USA)."""
        with self._lock:
            documents = self._table.all()
        suppliers = [self._to_supplier(document) for document in documents]
        if country is not None:
            suppliers = [supplier for supplier in suppliers if supplier.country == country]
        if category is not None:
            suppliers = [supplier for supplier in suppliers if category in supplier.categories]
        return sorted(suppliers, key=lambda supplier: supplier.id)

    def get(self, supplier_id: int) -> Supplier | None:
        with self._lock:
            document = self._table.get(doc_id=supplier_id)
        return None if document is None else self._to_supplier(document)

    def find_by_name(self, name: str) -> Supplier | None:
        with self._lock:
            document = self._find_document_by_name(name)
        return None if document is None else self._to_supplier(document)

    def count(self) -> int:
        with self._lock:
            return len(self._table)

    def is_empty(self) -> bool:
        return self.count() == 0

    # --- Escritura -------------------------------------------------------------------------

    def create(self, data: SupplierCreate) -> Supplier:
        """Guarda un proveedor nuevo; `updated_at` registra la fecha de su tarifa inicial."""
        record = data.model_dump(mode="json")
        record["updated_at"] = utc_now().isoformat()
        with self._lock:
            documents = self._table.all()
            if self._find_document_by_name(data.name, documents) is not None:
                raise DuplicateSupplierError(data.name)
            # El ID se calcula con lo que hay en el archivo, como hace TinyDB, pero sin su caché:
            # así no choca con inserciones hechas desde otro proceso (por ejemplo, `uv run seed`).
            supplier_id = max((document.doc_id for document in documents), default=0) + 1
            self._table.insert(Document(record, doc_id=supplier_id))
            document = self._table.get(doc_id=supplier_id)
        return self._to_supplier(document)

    def update_rate(self, supplier_id: int, rate_per_unit: float) -> Supplier | None:
        """Cambia la tarifa y registra el timestamp exacto del cambio (auditoría de precios)."""
        return self._update(supplier_id, {"rate_per_unit": rate_per_unit, "updated_at": utc_now().isoformat()})

    def update_status(self, supplier_id: int, status: SupplierStatus) -> Supplier | None:
        """Activa o suspende. No toca `updated_at`, que es la fecha de la última tarifa."""
        # SupplierStatus(...) también rechaza un texto que no sea un estado del briefing.
        return self._update(supplier_id, {"status": SupplierStatus(status).value})

    def delete(self, supplier_id: int) -> Supplier | None:
        """Elimina y devuelve el proveedor; None si no existe."""
        with self._lock:
            document = self._table.get(doc_id=supplier_id)
            if document is None:
                return None
            self._table.remove(doc_ids=[supplier_id])
        return self._to_supplier(document)

    # --- Internos --------------------------------------------------------------------------

    def _update(self, supplier_id: int, changes: dict) -> Supplier | None:
        with self._lock:
            if not self._table.contains(doc_id=supplier_id):
                return None
            self._table.update(changes, doc_ids=[supplier_id])
            document = self._table.get(doc_id=supplier_id)
        return self._to_supplier(document)

    def _find_document_by_name(self, name: str, documents: list[Document] | None = None) -> Document | None:
        key = normalize_name(name)
        candidates = self._table.all() if documents is None else documents
        return next((document for document in candidates if normalize_name(document["name"]) == key), None)

    @staticmethod
    def _to_supplier(document: Document) -> Supplier:
        return Supplier(id=document.doc_id, **document)

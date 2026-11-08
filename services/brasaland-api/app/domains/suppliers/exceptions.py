"""Errores del dominio de proveedores. El router los traduce a respuestas HTTP."""


class DuplicateSupplierError(Exception):
    """Ya existe un proveedor con ese nombre (sin distinguir mayúsculas ni espacios extremos)."""

    def __init__(self, name: str):
        super().__init__(name)
        self.name = name

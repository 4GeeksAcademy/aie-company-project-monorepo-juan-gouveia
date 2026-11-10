"""Utilidades de la batería unitaria de proveedores (no son fixtures)."""


def supplier_data(**changes) -> dict:
    """Datos válidos de un proveedor de Colombia; `changes` sustituye o añade campos."""
    return {
        "name": "Carnes del Valle",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 18500.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "compras@carnesdelvalle.co",
        "notes": "Entrega martes y viernes",
        **changes,
    }

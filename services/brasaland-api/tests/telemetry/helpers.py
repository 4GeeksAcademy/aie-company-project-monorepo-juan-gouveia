"""Datos de prueba de la telemetría."""

from copy import deepcopy
from uuid import uuid4

# Evento válido con el envelope completo del plan y las propiedades de su esquema (allowlist).
EVENT = {
    "eventId": "5b2e8f4a-1c3d-4e6f-9a7b-8c9d0e1f2a3b",
    "timestamp": "2026-11-19T10:15:30.123Z",
    "sessionId": "0f8e7d6c-5b4a-4392-8170-6e5d4c3b2a19",
    "userId": "d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2",
    "event_type": "inbound_order_created",
    "schemaVersion": "1.0.0",
    "requestId": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "properties": {
        "order_id": 7824,
        "location_id": 3,
        "country": "CO",
        "product_id": 12,
        "product_category": "proteína",
        "quantity": 18.5,
        "unit": "kg",
        "currency": "COP",
        "supplier_id": 2,
        "unit_cost": 38500,
    },
    "source": "browser",
    "environment": "development",
}

# Propiedades válidas (las del ejemplo de cada esquema) de los eventos que usan las pruebas.
PROPERTIES = {
    "inbound_order_created": EVENT["properties"],
    "stock_waste_registered": {
        "order_id": 13319,
        "location_id": 3,
        "country": "CO",
        "product_id": 12,
        "product_category": "proteína",
        "quantity": 1.2,
        "unit": "kg",
        "currency": "COP",
        "reason": "expired",
        "stock_after": 30.4,
    },
    "page_viewed": {
        "route": "/inventario/ordenes",
        "previous_route": "/inventario/ingredientes",
        "navigation_type": "client",
        "user_role": "manager",
    },
    "login_failed": {"failure_reason": "invalid_credentials"},
    "frontend_error_captured": {
        "route": "/gestor-incidencias",
        "error_name": "TypeError",
        "message_sanitized": "Cannot read properties of undefined (reading 'status')",
        "error_fingerprint": "e7f6c011776e8db7",
        "source": "error_boundary",
    },
    "supplier_created": {"supplier_id": 9, "country": "US", "categories": ["carne"], "currency": "USD", "status": "active"},
}


def make_event(event_type: str = "page_viewed", **changes) -> dict:
    """Un evento válido del tipo pedido, con un eventId nuevo; `changes` sustituye campos del envelope."""
    data = deepcopy(EVENT)
    data.update(eventId=str(uuid4()), event_type=event_type, properties=deepcopy(PROPERTIES[event_type]))
    if event_type == "login_failed":
        data["schemaVersion"] = "2.0.0"
    data.update(changes)
    return data

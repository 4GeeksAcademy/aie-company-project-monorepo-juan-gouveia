"""Datos válidos de partida para las pruebas de inventario; cada prueba cambia solo lo que comprueba."""

USER_UUID = "8f14e45f-ceea-467f-a0e6-1b2c3d4e5f60"


def ingredient_data(**changes) -> dict:
    data = {
        "name": "Falda de ternera",
        "sku": "BRS-BEEF-001",
        "unit": "kg",
        "category": "meat",
        "country": "CO",
    }
    return {**data, **changes}


def entry_data(**changes) -> dict:
    data = {"ingredient_id": 1, "quantity": 50.0, "supplier_name": "Carnes del Valle S.A.", "unit_cost": 38500.0, "location_id": 1}
    return {**data, **changes}


def exit_data(**changes) -> dict:
    data = {"ingredient_id": 1, "quantity": 5.0, "reason": "consumption", "location_id": 1}
    # Una merma necesita su motivo (brecha B6): si la prueba no lo indica, se usa "expired".
    if changes.get("reason") == "waste" and "waste_reason" not in changes:
        data["waste_reason"] = "expired"
    return {**data, **changes}

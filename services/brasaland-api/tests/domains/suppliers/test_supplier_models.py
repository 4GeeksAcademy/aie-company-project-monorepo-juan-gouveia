"""Modelo de proveedor: campos y valores exactos del briefing, y rechazo de entradas inválidas."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.errors import describe_validation_errors, register_error_handlers
from app.domains.suppliers.models import (
    VALID_CATEGORIES,
    VALID_STATUSES,
    RateUpdate,
    StatusUpdate,
    Supplier,
    SupplierCreate,
)


def valid_payload(**changes):
    payload = {
        "name": "Carnes del Valle S.A.S.",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 28500.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "ventas@carnesdelvalle.co",
        "notes": "Proveedor principal de res y cerdo para Medellín.",
    }
    payload.update(changes)
    return payload


def error_fields(error: ValidationError) -> set[str]:
    return {item["field"] for item in describe_validation_errors(error.errors())}


# --- Valores del briefing ---------------------------------------------------------------


def test_valid_categories_match_briefing():
    assert VALID_CATEGORIES == [
        "carne",
        "verduras_y_hortalizas",
        "salsas_y_condimentos",
        "bebidas",
        "packaging",
        "productos_limpieza",
        "lacteos",
        "carbon_y_combustible",
    ]


def test_valid_statuses_match_briefing():
    assert VALID_STATUSES == ["active", "suspended"]


def test_supplier_fields_match_briefing():
    assert list(Supplier.model_fields) == [
        "name",
        "country",
        "categories",
        "rate_per_unit",
        "currency",
        "status",
        "contact_email",
        "notes",
        "id",
        "updated_at",
    ]


def test_valid_supplier_is_accepted_and_serializes_plain_values():
    supplier = SupplierCreate(**valid_payload())
    assert supplier.model_dump(mode="json") == valid_payload()


def test_optional_fields_can_be_omitted():
    payload = valid_payload()
    del payload["contact_email"], payload["notes"]
    supplier = SupplierCreate(**payload)
    assert supplier.contact_email is None and supplier.notes is None


def test_usa_supplier_with_usd_and_several_categories():
    supplier = SupplierCreate(
        **valid_payload(country="USA", currency="USD", categories=["salsas_y_condimentos", "bebidas"], rate_per_unit=4.5)
    )
    assert supplier.currency == "USD"


def test_integer_rate_is_accepted():
    assert SupplierCreate(**valid_payload(rate_per_unit=890)).rate_per_unit == 890.0


def test_name_and_notes_are_trimmed_and_empty_notes_become_none():
    supplier = SupplierCreate(**valid_payload(name="  CarboCo  ", notes="   "))
    assert supplier.name == "CarboCo" and supplier.notes is None


# --- Rechazos: estado, tarifa, país, moneda y categorías -------------------------------


@pytest.mark.parametrize("status", ["deleted", "Active", "ACTIVE", "", None])
def test_status_outside_allowed_values_is_rejected(status):
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**valid_payload(status=status))
    assert error_fields(error.value) == {"status"}


@pytest.mark.parametrize("rate", [0, 0.0, -1, -28500.0])
def test_zero_or_negative_rate_is_rejected(rate):
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**valid_payload(rate_per_unit=rate))
    assert error_fields(error.value) == {"rate_per_unit"}


@pytest.mark.parametrize("rate", ["28500", True, float("nan"), float("inf"), None])
def test_non_numeric_rate_is_rejected(rate):
    with pytest.raises(ValidationError):
        SupplierCreate(**valid_payload(rate_per_unit=rate))


def test_missing_country_is_rejected():
    payload = valid_payload()
    del payload["country"]
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**payload)
    assert error_fields(error.value) == {"country"}


@pytest.mark.parametrize("country", ["Colombía", "colombia", "US", "Mexico"])
def test_unknown_country_is_rejected(country):
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**valid_payload(country=country))
    assert error_fields(error.value) == {"country"}


@pytest.mark.parametrize(("country", "currency"), [("Colombia", "USD"), ("USA", "COP")])
def test_currency_must_match_country(country, currency):
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**valid_payload(country=country, currency=currency))
    [detail] = describe_validation_errors(error.value.errors())
    assert detail["field"] == "currency"
    assert country in detail["message"]


@pytest.mark.parametrize("categories", [[], ["carnes"], ["carne", "carne"], "carne"])
def test_invalid_categories_are_rejected(categories):
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**valid_payload(categories=categories))
    assert {field.split(".")[0] for field in error_fields(error.value)} == {"categories"}


def test_empty_name_is_rejected():
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**valid_payload(name="   "))
    assert error_fields(error.value) == {"name"}


def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**valid_payload(contact_email="ventas-en-carnes"))
    assert error_fields(error.value) == {"contact_email"}


# --- Campos generados por el sistema ------------------------------------------------------


@pytest.mark.parametrize("field", ["updated_at", "id", "unknown"])
def test_system_or_unknown_fields_sent_by_client_are_rejected(field):
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**valid_payload(**{field: "2026-11-03T10:00:00Z"}))
    assert error_fields(error.value) == {field}


def test_rate_update_validates_rate_and_forbids_extra_fields():
    assert RateUpdate(rate_per_unit=29000).rate_per_unit == 29000.0
    with pytest.raises(ValidationError):
        RateUpdate(rate_per_unit=0)
    with pytest.raises(ValidationError):
        RateUpdate(rate_per_unit=29000, updated_at="2026-11-03T10:00:00Z")


def test_status_update_only_accepts_briefing_statuses():
    assert StatusUpdate(status="suspended").status == "suspended"
    with pytest.raises(ValidationError):
        StatusUpdate(status="inactive")


# --- Formato de los errores 422 ----------------------------------------------------------


def test_validation_messages_are_in_spanish():
    with pytest.raises(ValidationError) as error:
        SupplierCreate(**valid_payload(status="deleted", rate_per_unit=0, updated_at="x"))
    messages = {item["field"]: item["message"] for item in describe_validation_errors(error.value.errors())}
    assert messages == {
        "status": "Debe ser uno de estos valores: 'active' o 'suspended'.",
        "rate_per_unit": "Debe ser mayor que 0.",
        "updated_at": "Este campo no está permitido; lo genera el sistema o no existe.",
    }


def test_api_responds_422_with_details_before_running_the_endpoint():
    app = FastAPI()
    register_error_handlers(app)
    calls = []

    @app.post("/suppliers")
    def create(supplier: SupplierCreate):
        calls.append(supplier)
        return {}

    response = TestClient(app).post("/suppliers", json=valid_payload(status="deleted"))
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert error["message"] == "La petición no es válida. Revisa: status."
    assert error["details"] == [{"field": "status", "message": "Debe ser uno de estos valores: 'active' o 'suspended'."}]
    assert calls == []

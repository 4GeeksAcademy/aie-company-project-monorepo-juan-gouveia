"""Catálogo de locales: la migración 004 y `GET /api/v1/locations`."""

import logging

from app.domains.incidents.models import Branch
from app.domains.locations.models import LOCATIONS_METADATA
from tests.locations.helpers import migration_rows

# --- La migración 004 -----------------------------------------------------------------------------


def test_the_migration_has_the_fourteen_locations_in_order():
    assert [row["id"] for row in migration_rows()] == list(range(1, 15))


def test_the_codes_are_the_briefing_branches_in_order_without_central():
    # Los locales son las sedes del briefing del gestor de incidencias, en el orden de su tabla.
    branches = [branch.value for branch in Branch if branch is not Branch.CENTRAL]

    assert [row["code"] for row in migration_rows()] == branches


def test_every_incident_branch_is_a_location_or_central():
    codes = {row["code"] for row in migration_rows()}

    assert {branch.value for branch in Branch} == codes | {Branch.CENTRAL.value}


def test_locations_1_to_9_are_in_colombia_and_10_to_14_in_florida():
    rows = migration_rows()

    assert {(row["country"], row["currency"]) for row in rows[:9]} == {("CO", "COP")}
    assert {(row["country"], row["currency"]) for row in rows[9:]} == {("US", "USD")}


def test_every_location_has_a_display_name_and_a_city():
    assert all(row["name"].strip() and row["city"].strip() for row in migration_rows())
    assert migration_rows()[10]["name"] == "Miami Hialeah"


# --- GET /api/v1/locations ------------------------------------------------------------------------


def test_lists_the_fourteen_locations_ordered_by_id(client):
    response = client.get("/api/v1/locations")

    assert response.status_code == 200
    assert response.json() == migration_rows()


def test_the_second_request_comes_from_the_cache(client):
    first = client.get("/api/v1/locations")
    second = client.get("/api/v1/locations")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert second.json() == first.json()


def test_requires_a_token(api):
    response = api.get("/api/v1/locations")

    assert response.status_code == 401


def test_without_the_table_answers_503_and_asks_for_the_migration(client, inventory_engine, caplog):
    LOCATIONS_METADATA.drop_all(inventory_engine)

    with caplog.at_level(logging.ERROR, logger="api.locations"):
        response = client.get("/api/v1/locations")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "locations_unavailable"
    assert "004_locations.sql" in caplog.text


def test_a_failure_is_not_cached(client, inventory_engine):
    LOCATIONS_METADATA.drop_all(inventory_engine)
    assert client.get("/api/v1/locations").status_code == 503

    LOCATIONS_METADATA.create_all(inventory_engine)
    response = client.get("/api/v1/locations")

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"

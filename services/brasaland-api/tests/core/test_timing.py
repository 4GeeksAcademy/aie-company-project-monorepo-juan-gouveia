"""Middleware de timing: una línea por petición con método, ruta, estado, duración e id de la petición."""

import logging
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import register_error_handlers
from app.core.timing import logger, register_timing_middleware

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
LINE = re.compile(rf"^(GET|POST|PUT|PATCH|DELETE) (\S+) → (\d{{3}}) \| \d+\.\dms \| ({UUID})$")


def timing_lines(caplog) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "api.timing"]


def test_registra_una_linea_por_peticion_con_el_formato_del_briefing(api, caplog):
    caplog.set_level(logging.INFO, logger="api.timing")

    api.get("/health")

    [line] = timing_lines(caplog)
    match = LINE.match(line)
    assert match, line
    assert match.groups()[:3] == ("GET", "/health", "200")


def test_registra_tambien_las_respuestas_de_error(api, caplog):
    caplog.set_level(logging.INFO, logger="api.timing")

    api.get("/api/v1/inventory/products")

    [line] = timing_lines(caplog)
    assert line.startswith("GET /api/v1/inventory/products → 401 | ")


def test_registra_la_ruta_sin_la_query_string(api, caplog):
    caplog.set_level(logging.INFO, logger="api.timing")

    api.get("/health?country=CO")

    [line] = timing_lines(caplog)
    assert line.startswith("GET /health → 200 | ")


def test_un_error_no_controlado_se_registra_como_500(caplog):
    caplog.set_level(logging.INFO, logger="api.timing")
    app = FastAPI()
    register_error_handlers(app)
    register_timing_middleware(app)

    @app.get("/falla")
    def falla():
        raise RuntimeError("fallo inesperado")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/falla")

    assert response.status_code == 500
    [line] = timing_lines(caplog)
    assert line.startswith("GET /falla → 500 | ")


def test_registrarlo_varias_veces_no_duplica_el_handler_de_consola():
    handlers = list(logger.handlers)

    register_timing_middleware(FastAPI())

    assert logger.handlers == handlers
    assert len(handlers) == 1


# --- X-Request-Id (correlación de la telemetría) ---------------------------------------------------

REQUEST_ID = "0f8e7d6c-5b4a-4392-8170-6e5d4c3b2a19"


def test_reutiliza_el_x_request_id_recibido_y_lo_devuelve(api, caplog):
    caplog.set_level(logging.INFO, logger="api.timing")

    response = api.get("/health", headers={"X-Request-Id": REQUEST_ID})

    assert response.headers["X-Request-Id"] == REQUEST_ID
    [line] = timing_lines(caplog)
    assert line.endswith(f"| {REQUEST_ID}")


def test_normaliza_el_x_request_id_en_minusculas(api):
    response = api.get("/health", headers={"X-Request-Id": REQUEST_ID.upper()})

    assert response.headers["X-Request-Id"] == REQUEST_ID


def test_crea_un_x_request_id_si_falta(api, caplog):
    caplog.set_level(logging.INFO, logger="api.timing")

    response = api.get("/health")

    request_id = response.headers["X-Request-Id"]
    assert re.fullmatch(UUID, request_id)
    [line] = timing_lines(caplog)
    assert line.endswith(f"| {request_id}")


def test_sustituye_un_x_request_id_que_no_es_un_uuid(api, caplog):
    caplog.set_level(logging.INFO, logger="api.timing")

    response = api.get("/health", headers={"X-Request-Id": "<script>alert(1)</script>"})

    assert re.fullmatch(UUID, response.headers["X-Request-Id"])
    [line] = timing_lines(caplog)
    assert "script" not in line


def test_tambien_devuelve_el_x_request_id_en_las_respuestas_de_error(api):
    response = api.get("/api/v1/inventory/products", headers={"X-Request-Id": REQUEST_ID})

    assert response.status_code == 401
    assert response.headers["X-Request-Id"] == REQUEST_ID

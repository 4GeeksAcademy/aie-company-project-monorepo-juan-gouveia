"""Middleware de timing: una línea por petición con método, ruta, estado y duración."""

import logging
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import register_error_handlers
from app.core.timing import logger, register_timing_middleware

LINE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE) (\S+) → (\d{3}) \| \d+\.\dms$")


def timing_lines(caplog) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "api.timing"]


def test_registra_una_linea_por_peticion_con_el_formato_del_briefing(api, caplog):
    caplog.set_level(logging.INFO, logger="api.timing")

    api.get("/health")

    [line] = timing_lines(caplog)
    match = LINE.match(line)
    assert match, line
    assert match.groups() == ("GET", "/health", "200")


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

"""TTLCache: expiración, invalidación y la carrera entre una carga y una escritura."""

import pytest

from app.core.cache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def cache(clock):
    return TTLCache[str](ttl_seconds=60, clock=clock)


def test_la_primera_lectura_carga_y_la_segunda_sale_de_la_cache(cache):
    calls = []

    def load():
        calls.append(1)
        return "valor"

    assert cache.get_or_load("k", load) == ("valor", False)
    assert cache.get_or_load("k", load) == ("valor", True)
    assert len(calls) == 1


def test_cada_clave_se_guarda_por_separado(cache):
    cache.get_or_load("CO", lambda: "colombia")

    assert cache.get_or_load("US", lambda: "usa") == ("usa", False)
    assert cache.get("CO") == "colombia"


def test_el_valor_expira_al_cumplirse_el_ttl(cache, clock):
    cache.get_or_load("k", lambda: "viejo")

    clock.now += 59.9
    assert cache.get("k") == "viejo"
    clock.now += 0.1
    assert cache.get("k") is None
    assert cache.get_or_load("k", lambda: "nuevo") == ("nuevo", False)


def test_invalidate_vacia_todas_las_claves(cache):
    cache.get_or_load("a", lambda: "1")
    cache.get_or_load("b", lambda: "2")

    cache.invalidate()

    assert cache.get("a") is None
    assert cache.get("b") is None


def test_una_carga_que_se_cruza_con_una_invalidacion_no_guarda_su_resultado(cache):
    # Una petición lee la base, otra escribe e invalida antes de que la primera guarde: lo leído ya
    # es obsoleto y no debe quedarse en la caché durante todo el TTL.
    def load_racing_a_write():
        cache.invalidate()
        return "leído antes de la escritura"

    assert cache.get_or_load("k", load_racing_a_write) == ("leído antes de la escritura", False)
    assert cache.get("k") is None


def test_un_error_al_cargar_no_guarda_nada(cache):
    def failing_load():
        raise RuntimeError("la base no responde")

    with pytest.raises(RuntimeError):
        cache.get_or_load("k", failing_load)
    assert cache.get("k") is None


@pytest.mark.parametrize("ttl", [0, -1])
def test_exige_un_ttl_positivo(ttl):
    with pytest.raises(ValueError):
        TTLCache(ttl_seconds=ttl)

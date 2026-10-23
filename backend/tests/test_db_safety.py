import pytest

from app.core.db import assert_distinct_test_database


def test_rechaza_cuando_test_y_produccion_son_la_misma_url():
    """No autorizar una base de desarrollo/producción como destino de integración."""
    misma = "postgresql://u:p@host/Findlab?sslmode=require"
    with pytest.raises(RuntimeError, match="misma"):
        assert_distinct_test_database(misma, misma)


def test_rechaza_ignorando_espacios_alrededor():
    url = "postgresql://u:p@host/Findlab?sslmode=require"
    with pytest.raises(RuntimeError):
        assert_distinct_test_database(f" {url} ", url)


def test_acepta_urls_distintas():
    assert_distinct_test_database(
        "postgresql://u:p@prod-host/Findlab?sslmode=require",
        "postgresql://u:p@test-host/Findlab_test?sslmode=require",
    ) is None


def test_no_reclama_si_alguna_esta_vacia():
    # Sin DATABASE_URL_TEST el fixture `engine` ya hace pytest.skip aparte; esta función no debe fallar antes.
    assert assert_distinct_test_database("", "postgresql://u:p@host/db") is None
    assert assert_distinct_test_database("postgresql://u:p@host/db", "") is None

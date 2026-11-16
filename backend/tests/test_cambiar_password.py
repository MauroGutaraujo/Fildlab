import pytest

from app.core.security import verify_password
from app.scripts.cambiar_password import cambiar_password
from app.scripts.crear_usuarios_iniciales import USUARIOS_INICIALES, obtener_password


async def test_cambiar_password_reemplaza_el_hash(db, crear_usuario):
    u = await crear_usuario(email="g@fildlab.pe", password="clave-anterior-123")
    await cambiar_password(db, "g@fildlab.pe", "clave-nueva-larga-456")
    assert verify_password("clave-nueva-larga-456", u.password_hash)
    assert not verify_password("clave-anterior-123", u.password_hash)


async def test_cambiar_password_rechaza_clave_corta(db, crear_usuario):
    await crear_usuario(email="t@fildlab.pe")
    with pytest.raises(ValueError):
        await cambiar_password(db, "t@fildlab.pe", "corta")


async def test_cambiar_password_usuario_inexistente(db):
    with pytest.raises(LookupError):
        await cambiar_password(db, "nadie@fildlab.pe", "clave-nueva-larga-456")


def test_usuarios_iniciales_no_guardan_contrasenas():
    assert all("password" not in u for u in USUARIOS_INICIALES)


def test_obtener_password_lee_entorno_y_valida_longitud(monkeypatch):
    monkeypatch.setenv("GERENCIA_PASSWORD", "una-clave-de-entorno-larga")
    assert obtener_password("GERENCIA_PASSWORD", "g@fildlab.pe") == "una-clave-de-entorno-larga"
    monkeypatch.setenv("GERENCIA_PASSWORD", "corta")
    with pytest.raises(ValueError):
        obtener_password("GERENCIA_PASSWORD", "g@fildlab.pe")

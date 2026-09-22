from sqlalchemy import select

from app.core.security import verify_password
from app.models.usuario import Usuario
from app.scripts.crear_gerente import asegurar_gerente


async def test_asegurar_gerente_crea_y_es_idempotente(db):
    u1 = await asegurar_gerente(db, "Elva", "gerente@fildlab.pe", "una-clave-larga-1")
    u2 = await asegurar_gerente(db, "Elva", "gerente@fildlab.pe", "otra-distinta")
    assert u1.id == u2.id
    assert u1.rol == "GERENCIA"
    assert verify_password("una-clave-larga-1", u2.password_hash)  # no se pisa
    total = (await db.execute(select(Usuario).where(Usuario.email == "gerente@fildlab.pe"))).scalars().all()
    assert len(total) == 1


async def test_asegurar_gerente_rechaza_clave_corta(db):
    import pytest

    with pytest.raises(ValueError):
        await asegurar_gerente(db, "Elva", "g@fildlab.pe", "corta")

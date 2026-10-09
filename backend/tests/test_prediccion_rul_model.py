from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul


async def _equipo(db, crear_cliente, serie="EQ-TEST-01"):
    await crear_cliente("20612493821")
    e = Equipo(serie=serie, cliente_ruc="20612493821", tipo_sistema="FILTRO",
              fecha_instalacion=date(2026, 1, 1), parametros_nominales={})
    db.add(e)
    await db.flush()
    return e


async def test_crear_prediccion_valida(db, crear_cliente):
    await _equipo(db, crear_cliente)
    p = PrediccionRul(equipo_serie="EQ-TEST-01", dias_vida_util_remanente=45, nivel_alerta="AMARILLO")
    db.add(p)
    await db.flush()
    assert (await db.get(PrediccionRul, "EQ-TEST-01")).nivel_alerta == "AMARILLO"


async def test_nivel_alerta_invalido_viola_check_constraint(db, crear_cliente):
    await _equipo(db, crear_cliente)
    db.add(PrediccionRul(equipo_serie="EQ-TEST-01", dias_vida_util_remanente=10, nivel_alerta="INVENTADO"))
    with pytest.raises(IntegrityError):
        await db.flush()

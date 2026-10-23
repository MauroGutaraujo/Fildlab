import os
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.db import make_engine
from test_migraciones_preia import migrar


async def test_supervision_legada_desconocida_y_downgrade_protegido(engine):
    esquema=f"test_{uuid4().hex}"
    eng=make_engine(os.environ["DATABASE_URL_TEST"],schema=esquema)
    try:
        async with eng.begin() as c:
            await c.execute(text(f'CREATE SCHEMA "{esquema}"'))
            await c.run_sync(migrar,"20261022_modelo_rul")
            await c.execute(text("""INSERT INTO ejecuciones_rul(id,iniciado_en,estado,version_calculo,version_dataset,politica_alerta,
                entorno,vigencia_horas,total,estimadas,abstenciones) VALUES (:id,now(),'EN_CURSO','COX_INSTALACION_V3',
                'WEIBULL_CENSURA_V2','RUL_30_90_V1','{}',48,0,0,0)"""),{"id":uuid4()})
            await c.run_sync(migrar,"head")
            assert (await c.execute(text("SELECT limite_en,latido_en,esperados,procesados FROM ejecuciones_rul"))).one()==(None,None,None,None)
            await c.execute(text("UPDATE ejecuciones_rul SET limite_en=now()+interval '10 minutes',latido_en=now(),esperados=0,procesados=0"))
            with pytest.raises(RuntimeError,match="supervisión"):
                await c.run_sync(migrar,"20261022_modelo_rul",bajar=True)
            assert await c.scalar(text("SELECT esperados FROM ejecuciones_rul"))==0
            await c.execute(text("DELETE FROM ejecuciones_rul"))
            await c.run_sync(migrar,"20261022_modelo_rul",bajar=True)
            await c.run_sync(migrar,"head")
    finally:
        async with eng.begin() as c:
            await c.execute(text(f'DROP SCHEMA IF EXISTS "{esquema}" CASCADE'))
        await eng.dispose()

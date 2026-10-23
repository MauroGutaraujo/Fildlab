import os
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.db import make_engine
from test_migraciones_preia import migrar


async def test_downgrade_no_borra_ejecuciones_nuevas(engine):
    esquema = f"test_{uuid4().hex}"
    aislado = make_engine(os.environ["DATABASE_URL_TEST"], schema=esquema)
    try:
        async with aislado.begin() as c:
            await c.execute(text(f'CREATE SCHEMA "{esquema}"'))
            await c.run_sync(migrar, "head")
            await c.execute(text("""INSERT INTO ejecuciones_rul(id,iniciado_en,estado,version_calculo,version_dataset,
                politica_alerta,entorno,vigencia_horas,total,estimadas,abstenciones)
                VALUES (:id,now(),'EN_CURSO','COX_INSTALACION_V3','WEIBULL_CENSURA_V2','RUL_30_90_V1','{}',48,0,0,0)"""), {"id":uuid4()})
            assert (await c.execute(text("SELECT modelo_sha256,entorno_modelo FROM ejecuciones_rul"))).one()==(None,None)
            await c.execute(text("UPDATE ejecuciones_rul SET modelo_sha256=:sha,entorno_modelo='{}'"),{"sha":"a"*64})
            with pytest.raises(RuntimeError,match="identidad de modelos"):
                await c.run_sync(migrar,"20261022_historial_rul",bajar=True)
            assert await c.scalar(text("SELECT modelo_sha256 FROM ejecuciones_rul"))=="a"*64
            await c.execute(text("UPDATE ejecuciones_rul SET modelo_sha256=NULL,entorno_modelo=NULL"))
            with pytest.raises(RuntimeError, match="historial RUL"):
                await c.run_sync(migrar, "20261022_componentes", bajar=True)
            assert await c.scalar(text("SELECT count(*) FROM ejecuciones_rul")) == 1
            await c.execute(text("DELETE FROM ejecuciones_rul"))
            await c.run_sync(migrar, "20261022_componentes", bajar=True)
            await c.run_sync(migrar, "head")
    finally:
        async with aislado.begin() as c:
            await c.execute(text(f'DROP SCHEMA IF EXISTS "{esquema}" CASCADE'))
        await aislado.dispose()

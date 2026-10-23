from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.supervision_rul import PoliticaSupervision
from app.services.supervision_rul import evaluar_supervision

AHORA=datetime(2026,10,23,10,tzinfo=timezone.utc)  # 05:00 Lima: termina gracia cron.


def corrida(**cambios):
    d=dict(id=uuid4(),estado="COMPLETADA",iniciado_en=AHORA-timedelta(days=1,hours=2),finalizado_en=AHORA-timedelta(days=1,hours=2)+timedelta(minutes=1),
        limite_en=None,latido_en=None,esperados=1,procesados=1,total=1,error_codigo=None)
    return SimpleNamespace(**(d|cambios))


def evaluar(**cambios):
    c=corrida()
    return evaluar_supervision(ahora=AHORA,reciente=c,exitosa=c,fallida=None,activas=[],cantidad_activas=0,
        total_equipos=1,sin_evaluar=0,resultados_exito=1,politica=PoliticaSupervision(),**cambios)


def codigos(salida): return {a["codigo"] for a in salida["avisos"]}


def test_gracia_cron_en_dia_lima_justo_antes_y_en_limite():
    c=corrida()
    args=dict(reciente=c,exitosa=c,fallida=None,activas=[],cantidad_activas=0,total_equipos=1,sin_evaluar=0,resultados_exito=1,politica=PoliticaSupervision())
    antes=evaluar_supervision(ahora=AHORA-timedelta(seconds=1),**args)
    despues=evaluar_supervision(ahora=AHORA,**args)
    assert "ACTUALIZACION_DIARIA_AUSENTE" not in codigos(antes)
    assert "ACTUALIZACION_DIARIA_AUSENTE" in codigos(despues)


@pytest.mark.parametrize("desfase,plazo,codigo", [(89,60,"EJECUCION_ACTIVA"),(90,60,"ACTIVIDAD_NO_CONFIRMADA"),(20,-1,"PLAZO_SUPERADO")])
def test_senal_y_plazo_fronteras(desfase,plazo,codigo):
    c=corrida(estado="EN_CURSO",iniciado_en=AHORA-timedelta(minutes=3),finalizado_en=None,
        latido_en=AHORA-timedelta(seconds=desfase),limite_en=AHORA+timedelta(seconds=plazo))
    salida=evaluar_supervision(ahora=AHORA,reciente=c,exitosa=None,fallida=None,activas=[c],cantidad_activas=1,
        total_equipos=1,sin_evaluar=1,resultados_exito=0,politica=PoliticaSupervision())
    assert codigo in codigos(salida)
    assert c.estado=="EN_CURSO"  # Lectura no decide que el proceso murió.


def test_fallo_se_resuelve_con_exito_posterior_pero_omision_no_lo_oculta():
    fallo=corrida(estado="FALLIDA",iniciado_en=AHORA-timedelta(hours=1),error_codigo="MODELO_INVALIDO")
    omision=corrida(estado="OMITIDA_CONCURRENCIA",iniciado_en=AHORA)
    args=dict(ahora=AHORA,reciente=omision,fallida=fallo,activas=[],cantidad_activas=0,total_equipos=1,sin_evaluar=0,resultados_exito=1,politica=PoliticaSupervision())
    assert "EJECUCION_FALLIDA" in codigos(evaluar_supervision(exitosa=corrida(),**args))
    assert "EJECUCION_FALLIDA" not in codigos(evaluar_supervision(exitosa=corrida(iniciado_en=AHORA-timedelta(minutes=5),finalizado_en=AHORA),**args))


def test_cobertura_del_exito_incoherente_genera_aviso():
    c=corrida(iniciado_en=AHORA-timedelta(hours=1),finalizado_en=AHORA,total=1,esperados=2,procesados=1)
    salida=evaluar_supervision(ahora=AHORA,reciente=c,exitosa=c,fallida=None,activas=[],cantidad_activas=0,
        total_equipos=3,sin_evaluar=1,resultados_exito=1,politica=PoliticaSupervision())
    assert "RESULTADOS_INCOMPLETOS" in codigos(salida)


def test_sin_equipos_no_es_una_falla_por_ausencia_de_ejecuciones():
    s=evaluar_supervision(ahora=AHORA,reciente=None,exitosa=None,fallida=None,activas=[],cantidad_activas=0,
        total_equipos=0,sin_evaluar=0,resultados_exito=0,politica=PoliticaSupervision())
    assert s["estado"]=="SIN_EQUIPOS" and not s["avisos"]


async def test_supervision_solo_gerencia_y_nunca_confirma_normal_si_no_hay_ejecuciones(client,gerente_h,tecnico_h,db,crear_cliente):
    from test_rul_historial import preparar
    await preparar(db,crear_cliente)
    assert (await client.get("/api/v1/equipos/supervision-rul")).status_code==401
    assert (await client.get("/api/v1/equipos/supervision-rul",headers=tecnico_h)).status_code==403
    r=await client.get("/api/v1/equipos/supervision-rul",headers=gerente_h)
    assert r.status_code==200 and r.json()["estado"]=="ATENCION"
    assert "SIN_EJECUCIONES" in codigos(r.json())

from datetime import date, datetime, timedelta, timezone

import pytest

from app.schemas.prediccion_rul import PrediccionRulOut

AHORA = datetime(2026, 10, 23, 2, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def reloj(monkeypatch):
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return AHORA.astimezone(tz)
    monkeypatch.setattr("app.schemas.prediccion_rul.datetime", Reloj)


def entrada(**cambios):
    return dict(equipo_serie="EQ-1", dias_vida_util_remanente=100, nivel_alerta="VERDE",
                version_calculo="COX_INSTALACION_V3", actualizado_en=AHORA - timedelta(hours=24),
                fecha_referencia=date(2026, 1, 1), tipo_referencia="FILTRO",
                ejecucion_id="00000000-0000-0000-0000-000000000001",
                vence_en=AHORA + timedelta(hours=24), **cambios)


@pytest.mark.parametrize("segundos,estado,dias", [(1,"ESTIMADA",100),(0,"VENCIDA",None),(-1,"VENCIDA",None)])
def test_vence_en_frontera_sin_publicar_cifra_ni_color(segundos, estado, dias):
    datos = entrada()
    datos["vence_en"] = AHORA + timedelta(seconds=segundos)
    salida = PrediccionRulOut.model_validate(datos)
    assert salida.estado_estimacion == estado
    assert salida.dias_vida_util_remanente == dias
    if dias is None:
        assert salida.nivel_alerta is None
        # FastAPI puede volver a validar el objeto de respuesta.
        assert PrediccionRulOut.model_validate(salida).estado_estimacion == "VENCIDA"


@pytest.mark.parametrize("campo", ["vence_en", "tipo_referencia", "ejecucion_id"])
def test_resultado_sin_procedencia_requiere_recalculo(campo):
    datos = entrada()
    datos[campo] = None
    salida = PrediccionRulOut.model_validate(datos)
    assert salida.estado_estimacion == "REQUIERE_RECALCULO"
    assert salida.dias_vida_util_remanente is None and salida.nivel_alerta is None


def test_calculo_con_reloj_futuro_no_parece_actual():
    datos = entrada()
    datos["actualizado_en"] = AHORA + timedelta(seconds=1)
    salida = PrediccionRulOut.model_validate(datos)
    assert salida.estado_estimacion == "REQUIERE_RECALCULO"
    assert salida.dias_vida_util_remanente is None


def test_abstencion_vencida_tambien_requiere_nueva_evaluacion():
    datos = entrada()
    datos.update(dias_vida_util_remanente=None, nivel_alerta=None,
                 motivo_no_estimable="EDAD_FUERA_SOPORTE", vence_en=AHORA)
    assert PrediccionRulOut.model_validate(datos).estado_estimacion == "VENCIDA"

import json
import subprocess
import sys

import pytest


def test_comparacion_reproducible_con_baselines_y_verdad_solo_simulada():
    from app.ml.diagnostico_simulacion import diagnosticar_simulacion
    a = diagnosticar_simulacion(n_por_tipo=100, semillas=(42,))
    b = diagnosticar_simulacion(n_por_tipo=100, semillas=(42,))
    assert a == b
    assert a["validacion_real"] is False
    assert a["version_dataset"] == "WEIBULL_CENSURA_V2"
    assert a["ensayos"][0]["filas"] == 300
    assert a["ensayos"][0]["advertencias_cox"] == []
    tipos = a["ensayos"][0]["tipos"]
    assert set(tipos) == {"FILTRO", "ABLANDADOR", "OSMOSIS_INVERSA"}
    for tipo in tipos.values():
        assert tipo["masa_inicio_censura"] == 0
        assert tipo["fallas_tempranas"] > 0
        assert 0 < tipo["proporcion_eventos"] < 1
        assert set(tipo["candidatos"]) == {"COX", "KAPLAN_MEIER", "WEIBULL"}
        for resultado in tipo["candidatos"].values():
            assert resultado["advertencias"] == []
            assert resultado["mediana_dias"] > 0
            assert resultado["horizontes_evaluados"] == 3
            assert 0 <= resultado["error_curva_simulada"] < .15
    # La salida se puede compartir sin NaN/Infinity no estándar.
    json.dumps(a, allow_nan=False)


def test_diagnostico_no_cuenta_semillas_repetidas_como_evidencia_independiente():
    from app.ml.diagnostico_simulacion import diagnosticar_simulacion
    with pytest.raises(ValueError):
        diagnosticar_simulacion(semillas=(42, 42))


def test_cli_exporta_json_sin_requerir_credenciales_de_base(tmp_path):
    destino = tmp_path / "comparacion.json"
    subprocess.run([sys.executable, "-m", "app.ml.diagnostico_simulacion", "--n-por-tipo", "100",
                    "--semillas", "42", "--salida", str(destino)], check=True, capture_output=True)
    contenido = json.loads(destino.read_text(encoding="utf-8"))
    assert contenido["validacion_real"] is False
    assert len(contenido["ensayos"]) == 1
    assert contenido["ensayos"][0]["filas"] == 300

import hashlib
import json
import subprocess
import sys
from datetime import date, timedelta

import pytest

from app.ml.artefacto_rul import ModeloInvalido, cargar_modelo, exportar_modelo
from app.ml.modelo_rul import ParametrosImposibles, ajustar_modelo, calificar_equipo
from ml_helpers import dataset_estable


def huella(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def publicado(tmp_path):
    path = tmp_path / "modelo.json"
    exportar_modelo(dataset_estable(), path)
    return path


@pytest.mark.parametrize("tipo", ["FILTRO","ABLANDADOR","OSMOSIS_INVERSA"])
@pytest.mark.parametrize("edad", [0,29,30,89,90,179,180])
def test_roundtrip_preserva_calculo_y_abstencion(publicado, tipo, edad):
    original = ajustar_modelo(dataset_estable())
    modelo = cargar_modelo(publicado, huella(publicado))
    inicio = date(2026,1,1)
    def salida(m):
        try: return calificar_equipo(m,tipo,inicio,inicio+timedelta(days=edad))
        except ParametrosImposibles as e: return e.motivo
    assert salida(modelo) == salida(original)
    assert modelo.sha256 == huella(publicado)


def test_subprocess_carga_sin_entrenar(publicado):
    codigo = """from datetime import date
from app.ml.artefacto_rul import cargar_modelo
from app.ml.modelo_rul import calificar_equipo
import app.ml.modelo_rul as m
m.ajustar_modelo=lambda *_: (_ for _ in ()).throw(RuntimeError('no entrenar'))
import sys,json
print(json.dumps(calificar_equipo(cargar_modelo(sys.argv[1],sys.argv[2]),'FILTRO',date(2026,1,1),date(2026,1,1))))
"""
    r=subprocess.run([sys.executable,"-c",codigo,str(publicado),huella(publicado)],capture_output=True,text=True,check=True)
    assert json.loads(r.stdout) == {"dias_vida_util_remanente":80,"nivel_alerta":"AMARILLO"}


def test_no_sobrescribe_archivo_existente(publicado):
    antes=publicado.read_bytes()
    with pytest.raises(FileExistsError): exportar_modelo(dataset_estable(),publicado)
    assert publicado.read_bytes()==antes


def test_sha_incorrecto_rechaza(publicado):
    with pytest.raises(ModeloInvalido): cargar_modelo(publicado,"0"*64)


@pytest.mark.parametrize("defecto", ["version","curva","nan","entorno","extra","tipo_ausente","duplicado",
    "soporte_previo","formato_ausente","origen_ausente","resumen_negativo","resumen_eventos","resumen_extra","numero_texto"])
def test_json_con_sha_correcto_pero_contrato_invalido_rechaza(publicado,defecto):
    d=json.loads(publicado.read_text())
    if defecto=="version": d["version_calculo"]="OTRA"
    if defecto=="curva": d["curvas"]["FILTRO"]["supervivencia"][1]=1.1
    if defecto=="nan": d["curvas"]["FILTRO"]["tiempos"][0]=float('nan')
    if defecto=="entorno": d["entorno"]["numpy"]="0.0.0"
    if defecto=="extra": d["script"]="ejecutar algo"
    if defecto=="tipo_ausente": del d["curvas"]["FILTRO"]
    if defecto=="duplicado": d["curvas"]["FILTRO"]["tiempos"][1]=d["curvas"]["FILTRO"]["tiempos"][0]
    if defecto=="soporte_previo": d["curvas"]["FILTRO"]["soporte"]=d["curvas"]["FILTRO"]["tiempos"][0]/2
    if defecto=="formato_ausente": del d["formato"]
    if defecto=="origen_ausente": del d["origen"]
    if defecto=="resumen_negativo": d["resumen"]={"filas":-5,"eventos":0}
    if defecto=="resumen_eventos": d["resumen"]={"filas":5,"eventos":6}
    if defecto=="resumen_extra": d["resumen"]["arbitrary"]=1
    if defecto=="numero_texto": d["curvas"]["FILTRO"]["supervivencia"][0]=str(d["curvas"]["FILTRO"]["supervivencia"][0])
    publicado.write_text(json.dumps(d),encoding="utf-8")
    with pytest.raises(ModeloInvalido): cargar_modelo(publicado,huella(publicado))


def test_ajuste_inestable_no_se_publica(tmp_path):
    from app.ml.dataset_sintetico import generar_dataset, SUPUESTOS_SIMULACION
    df=generar_dataset()
    for tipo,p in SUPUESTOS_SIMULACION.items():
        filas=df.tipo_sistema==tipo
        df.loc[filas,"duracion_dias"]=df.loc[filas,"duracion_dias"].clip(lower=p["censura_desde_dias"])
    path=tmp_path/"inestable.json"
    with pytest.raises(ModeloInvalido): exportar_modelo(df,path)
    assert not path.exists()


def test_dependencia_numerica_transitiva_incompatible_rechaza(publicado,monkeypatch):
    from importlib.metadata import version
    monkeypatch.setattr("app.ml.artefacto_rul.version",lambda nombre: "0.0.0" if nombre=="scipy" else version(nombre),raising=False)
    with pytest.raises(ModeloInvalido): cargar_modelo(publicado,huella(publicado))

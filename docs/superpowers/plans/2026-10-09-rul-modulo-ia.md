# Módulo 4.2 — Inteligencia Artificial (RUL y Supervivencia) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calcular y mostrar una estimación de Vida Útil Remanente (RUL) por equipo, con alertas de falla crítica, vía un pipeline de supervivencia (Kaplan-Meier/Cox PH) aislado de la API, ejecutado como batch programado en GitHub Actions hacia `predicciones_rul` en Neon.

**Architecture:** Un paquete Python nuevo `backend/app/ml/` (nunca importado por `app/api/` ni `app/main.py`) genera un dataset sintético calibrado, ajusta un Cox PH, y califica cada equipo real por antigüedad + tipo de sistema. El resultado se escribe en una tabla nueva (`predicciones_rul`) vía upsert idempotente. Un workflow de GitHub Actions (cron nocturno + disparo manual) corre el script en el runner gratuito de GitHub. Un endpoint de solo lectura expone las predicciones; `EquiposPage.tsx` las muestra como badges y un panel de alertas ROJO.

**Tech Stack:** `lifelines` (Cox PH), `pandas`/`numpy` (dataset sintético), SQLAlchemy async + Alembic (tabla nueva), GitHub Actions (batch), React + TanStack Query (frontend) — sin dependencias nuevas de pago.

**Spec:** `docs/superpowers/specs/2026-10-09-rul-modulo-ia-design.md`

## Global Constraints

- El paquete `backend/app/ml/` nunca se importa desde `backend/app/api/` ni desde `backend/app/main.py` — aislamiento total de la API transaccional.
- Dataset de entrenamiento 100% sintético, semilla fija (determinístico), regenerado en memoria en cada corrida — nunca persistido en una tabla.
- "Falla crítica" = tiempo-hasta-evento muestreado de una Weibull calibrada por `tipo_sistema` (umbral de calidad de agua), nunca una intervención `CORRECTIVO` simulada.
- Covariables reales para calificar un equipo: únicamente `días en servicio` (`hoy - fecha_instalacion`) y `tipo_sistema` — nunca se intenta parsear lecturas reales de `actas_inmutables.payload_raw`.
- Curvas de supervivencia calibradas a las condiciones de agua de Trujillo (SEDALIB): OSMOSIS_INVERSA mediana 545 días (270–1095), ABLANDADOR mediana 1460 días (730–2920), FILTRO mediana 120 días (60–270). 70% evento / 30% censurado.
- Umbrales de `nivel_alerta` sobre `dias_vida_util_remanente`: ROJO si <30, AMARILLO si 30–90, VERDE si >90.
- El batch corre exclusivamente en el runner gratuito de GitHub Actions (cron nocturno 08:00 UTC = 03:00 Lima, + `workflow_dispatch` manual) — nunca en el contenedor de Render (512 MB / 0.1 vCPU). Las dependencias de ML viven en un extra `[ml]` de `pyproject.toml` que el Dockerfile de producción no instala.
- Equipo con `tipo_sistema` no reconocido o `fecha_instalacion` futura se omite con un log `WARN`, nunca tumba la corrida completa (REQ-19).
- Upsert idempotente (`ON CONFLICT (equipo_serie) DO UPDATE`) dentro de una única transacción por corrida — si algo falla a mitad de camino, nada cambia en `predicciones_rul`.
- El endpoint de lectura usa el mismo patrón de acceso que `backend/app/api/v1/equipos.py` hoy: `Depends(get_current_user)` sin restricción de rol (GERENCIA y TECNICO leen igual).
- Sin UI de administración para ajustar umbrales/calibración — viven como constantes documentadas en código.

## Review Focus

- **Orden de rutas en el router:** `GET /equipos/predicciones-rul` debe declararse ANTES de `GET /equipos/{serie}` en el archivo, o Starlette la interpreta como `serie="predicciones-rul"` y nunca llega al endpoint real (coincide con la primera ruta registrada que matchea).
- **`tipo_sistema` no reconocido en el batch:** aunque hoy hay un CHECK constraint en `equipos`, el batch debe omitir defensivamente (no asumir) cualquier valor fuera de `TIPOS_SISTEMA`, sin lanzar una excepción que tumbe la corrida completa.
- **Sesión de base de datos inyectable en `correr_batch()`:** sin un parámetro `session` opcional que permita a las pruebas reutilizar la sesión transaccional del fixture `db`, las pruebas de integración crearían su propio engine y escribirían fuera de la transacción de rollback del fixture, contaminando la base de pruebas compartida entre ejecuciones.
- **Identity map de SQLAlchemy tras una escritura con `text()` crudo:** una prueba de idempotencia que no invalida el caché de objetos ya cargados (`session.expire_all()`) antes de releer puede devolver el mismo objeto Python sin haber verificado nada real en la base.
- **El `useQuery` de predicciones en el frontend no debe bloquear ni romper la tabla de equipos:** si la petición falla (403, red) o no está mockeada en una prueba existente que no la espera, el equipo debe mostrar un badge "Sin evaluar" — nunca una pantalla en blanco ni una excepción no capturada que tumbe el render de toda la página.

---

## Backend

### Task 1: Tabla `predicciones_rul` (modelo + migración)

**Files:**
- Create: `backend/app/models/prediccion_rul.py`
- Modify: `backend/app/models/__init__.py:9` (registrar el import)
- Create: `backend/alembic/versions/<hash>_predicciones_rul.py` (vía `alembic revision --autogenerate`)
- Test: `backend/tests/test_prediccion_rul_model.py`

**Interfaces:**
- Produces: `app.models.prediccion_rul.PrediccionRul` (tabla `predicciones_rul`, PK `equipo_serie`) — consumido por los Tasks 4 y 5.

- [ ] **Step 1: Escribir la prueba que falla**

`backend/tests/test_prediccion_rul_model.py`:
```python
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
```

- [ ] **Step 2: Correr la prueba para verificar que falla**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_prediccion_rul_model.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.models.prediccion_rul'`).

- [ ] **Step 3: Crear el modelo**

`backend/app/models/prediccion_rul.py`:
```python
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class PrediccionRul(Base):
    __tablename__ = "predicciones_rul"
    __table_args__ = (
        CheckConstraint("nivel_alerta IN ('VERDE', 'AMARILLO', 'ROJO')", name="predicciones_rul_nivel_check"),
    )

    equipo_serie: Mapped[str] = mapped_column(String(50), ForeignKey("equipos.serie"), primary_key=True)
    dias_vida_util_remanente: Mapped[int] = mapped_column(Integer)
    nivel_alerta: Mapped[str] = mapped_column(String(20))
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
```

Modify `backend/app/models/__init__.py:9`:
```python
from app.models import cliente, contrato, equipo, orden, prediccion_rul, repuesto, usuario, venta  # noqa: E402,F401
```
(orden alfabético ya respetado, `prediccion_rul` entre `orden` y `repuesto`).

- [ ] **Step 4: Correr la prueba para verificar que pasa**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_prediccion_rul_model.py -v`
Expected: PASS (2 tests) — el fixture `db`/`engine` de `conftest.py` usa `Base.metadata.create_all`, que ya incluye la tabla nueva en cuanto el import de Step 3 está en su lugar.

- [ ] **Step 5: Generar la migración Alembic**

Run (desde `backend/`, con el venv activo):
```powershell
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "tabla predicciones_rul"
```
Abre el archivo generado en `backend/alembic/versions/` y confirma que:
- `down_revision` apunta a `'194ec320cb67'` (la única migración existente).
- Solo crea la tabla `predicciones_rul` (una sola `op.create_table(...)`) — si Alembic detecta cualquier otro cambio no relacionado, es una señal de que el modelo de otro archivo quedó mal importado; investiga antes de continuar.

No se ejecuta `alembic upgrade head` contra Neon en este plan — el usuario lo corre manualmente contra producción cuando decida desplegar, con el mismo criterio que la migración inicial de Fase 3.1.

- [ ] **Step 6: Correr toda la suite de backend para confirmar que nada se rompió**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde, más los 2 nuevos.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/prediccion_rul.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_prediccion_rul_model.py
git commit -m "feat: tabla predicciones_rul (modelo + migracion)"
```

---

### Task 2: Dataset sintético calibrado (`app/ml/dataset_sintetico.py`)

**Files:**
- Create: `backend/app/ml/__init__.py` (vacío)
- Create: `backend/app/ml/dataset_sintetico.py`
- Test: `backend/tests/test_ml_dataset_sintetico.py`

**Interfaces:**
- Consumes: nada del resto del backend (módulo autocontenido).
- Produces: `CALIBRACION: dict`, `generar_dataset(n_por_tipo: int, semilla: int) -> pd.DataFrame` con columnas `duracion_dias`, `evento`, `tipo_sistema` — consumido por el Task 3.

- [ ] **Step 1: Instalar las dependencias de ML en el entorno local**

Run: `cd backend && .venv/Scripts/python.exe -m pip install pandas numpy lifelines scikit-learn`
(Se agregan formalmente a `pyproject.toml` en el Task 6; esto solo las pone disponibles en el venv local para escribir y correr las pruebas de este task y los siguientes.)

- [ ] **Step 2: Escribir la prueba que falla**

`backend/tests/test_ml_dataset_sintetico.py`:
```python
import pandas as pd

from app.ml.dataset_sintetico import CALIBRACION, generar_dataset


def test_misma_semilla_mismo_dataset():
    a = generar_dataset(n_por_tipo=50, semilla=123)
    b = generar_dataset(n_por_tipo=50, semilla=123)
    pd.testing.assert_frame_equal(a, b)


def test_duraciones_dentro_del_rango_por_tipo():
    df = generar_dataset(n_por_tipo=200, semilla=7)
    for tipo, cal in CALIBRACION.items():
        sub = df[df["tipo_sistema"] == tipo]
        assert sub["duracion_dias"].min() >= cal["min_dias"]
        assert sub["duracion_dias"].max() <= cal["max_dias"]


def test_proporcion_evento_censurado_aproximada():
    df = generar_dataset(n_por_tipo=2000, semilla=7)
    proporcion = df["evento"].mean()
    assert 0.60 <= proporcion <= 0.80
```

- [ ] **Step 3: Correr la prueba para verificar que falla**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_ml_dataset_sintetico.py -v`
Expected: FAIL (no existe `app.ml.dataset_sintetico`).

- [ ] **Step 4: Crear el paquete y el generador**

`backend/app/ml/__init__.py`: archivo vacío.

`backend/app/ml/dataset_sintetico.py`:
```python
import numpy as np
import pandas as pd

# Vida util mediana y rango por tipo_sistema, calibrados con literatura de tratamiento
# de agua y ajustados a las condiciones de Trujillo (SEDALIB: agua mas dura y con mas
# turbidez estacional que el promedio generico internacional). Ajustable si hay cifras
# mas precisas de campo — documentado aqui, no enterrado en numeros magicos.
CALIBRACION = {
    "OSMOSIS_INVERSA": {"mediana_dias": 545, "min_dias": 270, "max_dias": 1095},
    "ABLANDADOR": {"mediana_dias": 1460, "min_dias": 730, "max_dias": 2920},
    "FILTRO": {"mediana_dias": 120, "min_dias": 60, "max_dias": 270},
}
PROPORCION_EVENTO = 0.70  # 70% falla (evento observado), 30% censurado
SEMILLA = 20261009


def generar_dataset(n_por_tipo: int = 500, semilla: int = SEMILLA) -> pd.DataFrame:
    """Genera un dataset sintetico de supervivencia: una fila por unidad simulada,
    con columnas duracion_dias, evento (1=fallo, 0=censurado), tipo_sistema.
    Deterministico: misma semilla -> mismo dataset, siempre."""
    rng = np.random.default_rng(semilla)
    filas = []
    for tipo, cal in CALIBRACION.items():
        forma = 1.5  # forma de Weibull calibrada para que la mediana caiga en mediana_dias
        escala = cal["mediana_dias"] / (np.log(2) ** (1 / forma))
        duraciones = rng.weibull(forma, n_por_tipo) * escala
        duraciones = np.clip(duraciones, cal["min_dias"], cal["max_dias"])
        eventos = rng.random(n_por_tipo) < PROPORCION_EVENTO
        for d, e in zip(duraciones, eventos):
            filas.append({"duracion_dias": float(d), "evento": int(e), "tipo_sistema": tipo})
    return pd.DataFrame(filas)
```

- [ ] **Step 5: Correr la prueba para verificar que pasa**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_ml_dataset_sintetico.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/ml/__init__.py backend/app/ml/dataset_sintetico.py backend/tests/test_ml_dataset_sintetico.py
git commit -m "feat: generador de dataset sintetico calibrado para el Modulo RUL"
```

---

### Task 3: Modelo de supervivencia (`app/ml/modelo_rul.py`)

**Files:**
- Create: `backend/app/ml/modelo_rul.py`
- Test: `backend/tests/test_ml_modelo_rul.py`

**Interfaces:**
- Consumes: `app.ml.dataset_sintetico.generar_dataset` (Task 2).
- Produces: `ajustar_modelo(dataset) -> CoxPHFitter`, `nivel_alerta(dias_restantes: float) -> str`, `calificar_equipo(cph, tipo_sistema, fecha_instalacion, hoy) -> dict`, `ParametrosImposibles` — consumidos por el Task 4.

- [ ] **Step 1: Escribir la prueba que falla**

`backend/tests/test_ml_modelo_rul.py`:
```python
from datetime import date, timedelta

import pytest

from app.ml.dataset_sintetico import generar_dataset
from app.ml.modelo_rul import ParametrosImposibles, ajustar_modelo, calificar_equipo, nivel_alerta


@pytest.fixture(scope="module")
def modelo():
    return ajustar_modelo(generar_dataset(n_por_tipo=500, semilla=42))


def test_nivel_alerta_umbrales():
    assert nivel_alerta(29) == "ROJO"
    assert nivel_alerta(30) == "AMARILLO"
    assert nivel_alerta(89) == "AMARILLO"
    assert nivel_alerta(90) == "VERDE"
    assert nivel_alerta(200) == "VERDE"


def test_calificar_equipo_fecha_futura_lanza_parametros_imposibles(modelo):
    hoy = date(2026, 1, 1)
    futura = hoy + timedelta(days=5)
    with pytest.raises(ParametrosImposibles):
        calificar_equipo(modelo, "FILTRO", futura, hoy)


def test_calificar_equipo_recien_instalado_cerca_de_la_vida_util_mediana(modelo):
    hoy = date(2026, 1, 1)
    r = calificar_equipo(modelo, "OSMOSIS_INVERSA", hoy, hoy)  # instalado hoy mismo
    assert 300 <= r["dias_vida_util_remanente"] <= 800
    assert r["nivel_alerta"] in ("VERDE", "AMARILLO", "ROJO")


def test_calificar_equipo_antiguo_tiene_menos_dias_restantes_que_uno_nuevo(modelo):
    hoy = date(2026, 1, 1)
    nuevo = calificar_equipo(modelo, "FILTRO", hoy, hoy)
    antiguo = calificar_equipo(modelo, "FILTRO", hoy - timedelta(days=100), hoy)
    assert antiguo["dias_vida_util_remanente"] < nuevo["dias_vida_util_remanente"]
```

- [ ] **Step 2: Correr la prueba para verificar que falla**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_ml_modelo_rul.py -v`
Expected: FAIL (no existe `app.ml.modelo_rul`).

- [ ] **Step 3: Implementar el modelo**

`backend/app/ml/modelo_rul.py`:
```python
from datetime import date

import pandas as pd
from lifelines import CoxPHFitter

UMBRAL_ROJO_DIAS = 30
UMBRAL_AMARILLO_DIAS = 90


class ParametrosImposibles(Exception):
    pass


def ajustar_modelo(dataset: pd.DataFrame) -> CoxPHFitter:
    df = pd.get_dummies(dataset, columns=["tipo_sistema"], drop_first=True)
    cph = CoxPHFitter()
    cph.fit(df, duration_col="duracion_dias", event_col="evento")
    return cph


def nivel_alerta(dias_restantes: float) -> str:
    if dias_restantes < UMBRAL_ROJO_DIAS:
        return "ROJO"
    if dias_restantes < UMBRAL_AMARILLO_DIAS:
        return "AMARILLO"
    return "VERDE"


def calificar_equipo(cph: CoxPHFitter, tipo_sistema: str, fecha_instalacion: date, hoy: date) -> dict:
    """Devuelve {dias_vida_util_remanente, nivel_alerta} para un equipo real.
    Lanza ParametrosImposibles si fecha_instalacion es invalida (REQ-19)."""
    dias_en_servicio = (hoy - fecha_instalacion).days
    if dias_en_servicio < 0:
        raise ParametrosImposibles(f"fecha_instalacion futura: {fecha_instalacion}")

    fila = pd.DataFrame([{"tipo_sistema": tipo_sistema}])
    fila = pd.get_dummies(fila, columns=["tipo_sistema"], drop_first=True)
    fila = fila.reindex(columns=cph.params_.index, fill_value=0)

    vida_util_total = float(cph.predict_median(fila).iloc[0])
    dias_restantes = max(0.0, vida_util_total - dias_en_servicio)
    return {"dias_vida_util_remanente": round(dias_restantes), "nivel_alerta": nivel_alerta(dias_restantes)}
```

- [ ] **Step 4: Correr la prueba para verificar que pasa**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_ml_modelo_rul.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/ml/modelo_rul.py backend/tests/test_ml_modelo_rul.py
git commit -m "feat: ajuste Cox PH y calificacion de equipos para el Modulo RUL"
```

---

### Task 4: Script de batch (`app/ml/batch_predicciones.py`)

**Files:**
- Create: `backend/app/ml/batch_predicciones.py`
- Test: `backend/tests/test_ml_batch_predicciones.py`

**Interfaces:**
- Consumes: `app.ml.dataset_sintetico.generar_dataset` (Task 2), `app.ml.modelo_rul.{ajustar_modelo, calificar_equipo, ParametrosImposibles}` (Task 3), `app.models.equipo.{Equipo, TIPOS_SISTEMA}`, `app.core.db.make_engine`.
- Produces: `correr_batch(session: AsyncSession | None = None) -> None` — punto de entrada único, usado por el workflow de GitHub Actions (Task 6, sin `session`) y por las pruebas de este task (con la sesión del fixture `db`).

- [ ] **Step 1: Escribir la prueba que falla**

`backend/tests/test_ml_batch_predicciones.py`:
```python
from datetime import date, timedelta

from sqlalchemy import func, select

from app.ml.batch_predicciones import correr_batch
from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul


async def _equipo(db, crear_cliente, *, serie, tipo_sistema, fecha_instalacion, ruc="20612493821"):
    await crear_cliente(ruc)
    e = Equipo(serie=serie, cliente_ruc=ruc, tipo_sistema=tipo_sistema,
              fecha_instalacion=fecha_instalacion, parametros_nominales={})
    db.add(e)
    await db.flush()
    return e


async def test_batch_puebla_predicciones_para_equipos_calificables(db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-1", tipo_sistema="OSMOSIS_INVERSA", fecha_instalacion=date(2025, 1, 1))
    await _equipo(db, crear_cliente, serie="EQ-2", tipo_sistema="FILTRO", fecha_instalacion=date(2026, 1, 1))
    await db.commit()

    await correr_batch(session=db)

    filas = (await db.execute(select(PrediccionRul))).scalars().all()
    assert {f.equipo_serie for f in filas} == {"EQ-1", "EQ-2"}


async def test_batch_omite_equipo_con_fecha_futura(db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-FUTURO", tipo_sistema="FILTRO",
                 fecha_instalacion=date.today() + timedelta(days=10))
    await db.commit()

    await correr_batch(session=db)

    assert (await db.get(PrediccionRul, "EQ-FUTURO")) is None


async def test_batch_es_idempotente(db, crear_cliente):
    await _equipo(db, crear_cliente, serie="EQ-1", tipo_sistema="ABLANDADOR", fecha_instalacion=date(2024, 1, 1))
    await db.commit()

    await correr_batch(session=db)
    db.expire_all()
    primera = await db.get(PrediccionRul, "EQ-1")
    dias_primera = primera.dias_vida_util_remanente

    await correr_batch(session=db)
    db.expire_all()
    segunda = await db.get(PrediccionRul, "EQ-1")

    assert segunda.dias_vida_util_remanente == dias_primera
    total = (await db.execute(select(func.count()).select_from(PrediccionRul))).scalar()
    assert total == 1


async def test_batch_sin_equipos_no_falla(db):
    await correr_batch(session=db)
    total = (await db.execute(select(func.count()).select_from(PrediccionRul))).scalar()
    assert total == 0


async def test_batch_omite_tipo_sistema_no_reconocido(db, crear_cliente, monkeypatch):
    """El CHECK constraint de la BD ya impide guardar un tipo_sistema invalido en equipos —
    esta prueba parchea la lista de tipos reconocidos del propio modulo batch para forzar
    la rama defensiva (REQ-19) sin depender de poder insertar un dato realmente imposible."""
    await _equipo(db, crear_cliente, serie="EQ-FILTRO", tipo_sistema="FILTRO", fecha_instalacion=date(2026, 1, 1))
    await db.commit()

    monkeypatch.setattr("app.ml.batch_predicciones.TIPOS_SISTEMA", ("OSMOSIS_INVERSA", "ABLANDADOR"))
    await correr_batch(session=db)

    assert (await db.get(PrediccionRul, "EQ-FILTRO")) is None
```

- [ ] **Step 2: Correr la prueba para verificar que falla**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_ml_batch_predicciones.py -v`
Expected: FAIL (no existe `app.ml.batch_predicciones`).

- [ ] **Step 3: Implementar el script de batch**

`backend/app/ml/batch_predicciones.py`:
```python
import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.db import make_engine
from app.ml.dataset_sintetico import generar_dataset
from app.ml.modelo_rul import ParametrosImposibles, ajustar_modelo, calificar_equipo
from app.models.equipo import TIPOS_SISTEMA, Equipo

_UPSERT_SQL = text(
    """
    INSERT INTO predicciones_rul (equipo_serie, dias_vida_util_remanente, nivel_alerta, actualizado_en)
    VALUES (:serie, :dias, :nivel, now())
    ON CONFLICT (equipo_serie) DO UPDATE
    SET dias_vida_util_remanente = EXCLUDED.dias_vida_util_remanente,
        nivel_alerta = EXCLUDED.nivel_alerta,
        actualizado_en = EXCLUDED.actualizado_en
    """
)


async def _ejecutar(session: AsyncSession) -> None:
    dataset = generar_dataset()
    cph = ajustar_modelo(dataset)

    equipos = (await session.execute(select(Equipo))).scalars().all()
    hoy = datetime.now(timezone.utc).date()

    resultados = []
    for e in equipos:
        if e.tipo_sistema not in TIPOS_SISTEMA:
            print(f"WARN: equipo {e.serie} omitido — tipo_sistema desconocido: {e.tipo_sistema}")
            continue
        try:
            r = calificar_equipo(cph, e.tipo_sistema, e.fecha_instalacion, hoy)
        except ParametrosImposibles as exc:
            print(f"WARN: equipo {e.serie} omitido — {exc}")
            continue
        resultados.append((e.serie, r["dias_vida_util_remanente"], r["nivel_alerta"]))

    if not resultados:
        print("No hay equipos reales para calificar.")
        await session.commit()
        return

    for serie, dias, nivel in resultados:
        await session.execute(_UPSERT_SQL, {"serie": serie, "dias": dias, "nivel": nivel})
    await session.commit()
    print(f"OK: {len(resultados)} equipos calificados.")


async def correr_batch(session: AsyncSession | None = None) -> None:
    """Punto de entrada. Sin `session` (uso real/CLI): crea su propio engine desde
    DATABASE_URL del entorno. Con `session` (pruebas): reutiliza esa sesión
    transaccional directamente, sin crear un engine nuevo — así las pruebas de
    integracion quedan aisladas por el rollback del fixture `db`, en vez de escribir
    fuera de esa transaccion y contaminar la base de pruebas compartida."""
    if session is not None:
        await _ejecutar(session)
        return

    engine: AsyncEngine = make_engine(os.environ["DATABASE_URL"])
    try:
        async with AsyncSession(engine, expire_on_commit=False) as s:
            await _ejecutar(s)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(correr_batch())
```

- [ ] **Step 4: Correr la prueba para verificar que pasa**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_ml_batch_predicciones.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Correr toda la suite de backend**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests en verde.

- [ ] **Step 6: Commit**

```bash
git add backend/app/ml/batch_predicciones.py backend/tests/test_ml_batch_predicciones.py
git commit -m "feat: script de batch idempotente para poblar predicciones_rul"
```

---

### Task 5: Endpoints de lectura (`/equipos/predicciones-rul`, `/equipos/{serie}/prediccion-rul`)

**Files:**
- Create: `backend/app/schemas/prediccion_rul.py`
- Modify: `backend/app/api/v1/equipos.py`
- Test: `backend/tests/test_predicciones_rul_endpoint.py`

**Interfaces:**
- Consumes: `app.models.prediccion_rul.PrediccionRul` (Task 1).
- Produces: `GET /api/v1/equipos/predicciones-rul` (lista) y `GET /api/v1/equipos/{serie}/prediccion-rul` (una) — consumidos por el Task 7 (frontend).

- [ ] **Step 1: Escribir la prueba que falla**

`backend/tests/test_predicciones_rul_endpoint.py`:
```python
from datetime import date

from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul


async def _equipo_con_prediccion(db, crear_cliente, *, serie="EQ-1", nivel="ROJO"):
    await crear_cliente("20612493821")
    db.add(Equipo(serie=serie, cliente_ruc="20612493821", tipo_sistema="FILTRO",
                  fecha_instalacion=date(2026, 1, 1), parametros_nominales={}))
    await db.flush()
    db.add(PrediccionRul(equipo_serie=serie, dias_vida_util_remanente=5, nivel_alerta=nivel))
    await db.flush()


async def test_listar_predicciones_gerencia_y_tecnico(client, gerente_h, tecnico_h, db, crear_cliente):
    await _equipo_con_prediccion(db, crear_cliente)
    await db.commit()

    r1 = await client.get("/api/v1/equipos/predicciones-rul", headers=gerente_h)
    r2 = await client.get("/api/v1/equipos/predicciones-rul", headers=tecnico_h)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()[0]["equipo_serie"] == "EQ-1"
    assert r1.json()[0]["nivel_alerta"] == "ROJO"


async def test_listar_predicciones_sin_token_401(client):
    assert (await client.get("/api/v1/equipos/predicciones-rul")).status_code == 401


async def test_leer_prediccion_de_un_equipo(client, gerente_h, db, crear_cliente):
    await _equipo_con_prediccion(db, crear_cliente, serie="EQ-2", nivel="VERDE")
    await db.commit()

    r = await client.get("/api/v1/equipos/EQ-2/prediccion-rul", headers=gerente_h)
    assert r.status_code == 200
    assert r.json()["nivel_alerta"] == "VERDE"


async def test_leer_prediccion_equipo_inexistente_404(client, gerente_h):
    r = await client.get("/api/v1/equipos/NO-EXISTE/prediccion-rul", headers=gerente_h)
    assert r.status_code == 404
    assert r.json()["detail"] == "Equipo no encontrado"


async def test_leer_prediccion_equipo_sin_evaluar_404(client, gerente_h, db, crear_cliente):
    await crear_cliente("20612493821")
    db.add(Equipo(serie="EQ-SIN-EVALUAR", cliente_ruc="20612493821", tipo_sistema="FILTRO",
                  fecha_instalacion=date(2026, 1, 1), parametros_nominales={}))
    await db.commit()

    r = await client.get("/api/v1/equipos/EQ-SIN-EVALUAR/prediccion-rul", headers=gerente_h)
    assert r.status_code == 404
    assert r.json()["detail"] == "Aún no hay predicción RUL para este equipo"
```

- [ ] **Step 2: Correr la prueba para verificar que falla**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_predicciones_rul_endpoint.py -v`
Expected: FAIL (404 en rutas que no existen todavía).

- [ ] **Step 3: Crear el esquema de salida**

`backend/app/schemas/prediccion_rul.py`:
```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

NivelAlerta = Literal["VERDE", "AMARILLO", "ROJO"]


class PrediccionRulOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipo_serie: str
    dias_vida_util_remanente: int
    nivel_alerta: NivelAlerta
    actualizado_en: datetime
```

- [ ] **Step 4: Agregar las rutas a `backend/app/api/v1/equipos.py`**

Modifica los imports al tope del archivo:
```python
from app.models.equipo import Equipo
from app.models.prediccion_rul import PrediccionRul
from app.schemas.equipo import EquipoIn, EquipoOut, EquipoUpdate
from app.schemas.prediccion_rul import PrediccionRulOut
```

**Inserta las dos rutas nuevas justo después de la función `_obtener` y ANTES de `@router.get("", response_model=list[EquipoOut])`** (el orden importa: `/predicciones-rul` debe quedar registrada antes de `/{serie}`, o Starlette la interpretaría como `serie="predicciones-rul"`):
```python
@router.get("/predicciones-rul", response_model=list[PrediccionRulOut])
async def listar_predicciones_rul(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(PrediccionRul))).scalars().all()


@router.get("/{serie}/prediccion-rul", response_model=PrediccionRulOut)
async def leer_prediccion_rul(serie: str, session: AsyncSession = Depends(get_session)):
    await _obtener(session, serie)
    prediccion = await session.get(PrediccionRul, serie)
    if prediccion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aún no hay predicción RUL para este equipo")
    return prediccion
```

- [ ] **Step 5: Correr la prueba para verificar que pasa**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_predicciones_rul_endpoint.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Correr toda la suite de backend**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests en verde (confirma en particular que `GET /equipos/{serie}` y `GET /equipos` existentes siguen funcionando sin chocar con las rutas nuevas).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/prediccion_rul.py backend/app/api/v1/equipos.py backend/tests/test_predicciones_rul_endpoint.py
git commit -m "feat: endpoints de lectura de predicciones RUL"
```

---

### Task 6: Dependencia `[ml]` y workflow de GitHub Actions

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `.github/workflows/rul-batch.yml`

**Interfaces:**
- Produces: extra `ml` instalable (`pip install -e ".[ml]"`), y el primer workflow de GitHub Actions del repo — no consumido por ningún otro task (es el punto de entrada operativo final del módulo).

- [ ] **Step 1: Agregar el extra `[ml]` a `backend/pyproject.toml`**

```toml
[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "httpx>=0.27"]
ml = ["lifelines>=0.27", "scikit-learn>=1.4", "pandas>=2.2", "numpy>=1.26"]
```

- [ ] **Step 2: Verificar que el extra instala limpio en un entorno nuevo**

Run (PowerShell, puede usar el mismo venv ya que las dependencias ya están instaladas del Task 2 Step 1 — esto solo confirma que `pyproject.toml` las declara correctamente):
```powershell
cd backend
.venv\Scripts\python.exe -m pip install -e ".[dev,ml]"
```
Expected: instala sin errores (ya estaban presentes, pip las reconoce como satisfechas).

- [ ] **Step 3: Crear el workflow de GitHub Actions**

`.github/workflows/rul-batch.yml`:
```yaml
name: Batch de predicciones RUL

on:
  schedule:
    - cron: "0 8 * * *"  # 03:00 hora de Lima (UTC-5) = 08:00 UTC
  workflow_dispatch: {}

jobs:
  predecir:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Instalar dependencias
        working-directory: backend
        run: pip install -e ".[ml]"
      - name: Correr el batch de predicciones RUL
        working-directory: backend
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL_PROD }}
        run: python -m app.ml.batch_predicciones
```

- [ ] **Step 4: Validar la sintaxis del YAML**

Run: `cd "/c/Users/Mauro/Proyectos/Fildlab" && python -c "import yaml; yaml.safe_load(open('.github/workflows/rul-batch.yml'))"`
Expected: no lanza ninguna excepción (YAML válido). Si Python no tiene `pyyaml` instalado globalmente, usa el venv de `backend` (`cd backend && .venv/Scripts/python.exe -c "..."`) o valida pegando el contenido en cualquier validador de YAML online — el objetivo es solo descartar errores de indentación antes de hacer push.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml .github/workflows/rul-batch.yml
git commit -m "feat: dependencia [ml] y workflow de GitHub Actions para el batch RUL"
```

- [ ] **Step 6 (manual del usuario, no automatizable desde este entorno — declarado, no escondido):**

Después de hacer push:
1. En GitHub → Settings → Secrets and variables → Actions, crear el secret `DATABASE_URL_PROD` con la cadena de conexión `-pooler` de la rama `main` de Neon (la misma usada en `Render` para `DATABASE_URL`).
2. Ir a la pestaña Actions → "Batch de predicciones RUL" → "Run workflow" (disparo manual) una vez.
3. Confirmar en el dashboard de Neon (tabla `predicciones_rul`) que se poblaron filas para los equipos reales existentes.

---

## Frontend

### Task 7: Badges de RUL y panel de alertas en `EquiposPage.tsx`

**Files:**
- Modify: `frontend/src/features/equipos/EquiposPage.tsx`
- Modify: `frontend/src/features/equipos/EquiposPage.test.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/equipos/predicciones-rul` (Task 5).
- Produces: nada consumido por otro task — es el último task del plan.

- [ ] **Step 1: Escribir las pruebas que fallan**

Reescribe `frontend/src/features/equipos/EquiposPage.test.tsx` completo con este contenido (agrega el mock de `predicciones-rul` a cada `mockApi(...)` existente, y 3 pruebas nuevas al final):

```tsx
import { describe, expect, it } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EquiposPage } from "./EquiposPage";
import { mockApi, renderWithProviders } from "../../test/utils";

// REQ-03: los 8 parámetros de referencia (TDS entrada/post-membrana/producto final,
// pH, conductividad, resistividad, litros de red y litros de agua pura).
const PARAMS_REQ03 = {
  tds_entrada_ppm: 350,
  tds_post_membrana_ppm: 8,
  tds_producto_final_ppm: 5,
  ph: 7.0,
  conductividad_us_cm: 15,
  resistividad_mohm_cm: 1.2,
  litros_consumidos_red: 500,
  litros_agua_pura: 420,
};

const EQUIPO = {
  serie: "RO-2026-0001",
  cliente_ruc: "20612493821",
  contrato_id: null,
  tipo_sistema: "OSMOSIS_INVERSA",
  fecha_instalacion: "2026-01-15",
  parametros_nominales: PARAMS_REQ03,
};

const SIN_PREDICCIONES = { path: "/api/v1/equipos/predicciones-rul", body: [] };

const posts = (f: ReturnType<typeof mockApi>) =>
  f.mock.calls.filter(([, i]) => (i as RequestInit | undefined)?.method === "POST");

const LABELS_PARAMS: Record<keyof typeof PARAMS_REQ03, RegExp> = {
  tds_entrada_ppm: /tds entrada/i,
  tds_post_membrana_ppm: /tds post-membrana/i,
  tds_producto_final_ppm: /tds producto final/i,
  ph: /^ph$/i,
  conductividad_us_cm: /conductividad/i,
  resistividad_mohm_cm: /resistividad/i,
  litros_consumidos_red: /litros consumidos/i,
  litros_agua_pura: /litros de agua pura/i,
};

async function llenar(
  o: { serie?: string; ruc?: string; fecha?: string; params?: Partial<typeof PARAMS_REQ03>; tipo?: string } = {},
) {
  await userEvent.type(screen.getByLabelText("Serie"), o.serie ?? "RO-1");
  await userEvent.type(screen.getByLabelText(/RUC del cliente/i), o.ruc ?? "20612493821");
  if (o.tipo) await userEvent.selectOptions(screen.getByLabelText("Tipo de sistema"), o.tipo);
  fireEvent.change(screen.getByLabelText(/fecha de instalación/i), { target: { value: o.fecha ?? "2026-01-15" } });
  const valores = { ...PARAMS_REQ03, ...o.params };
  for (const [campo, regex] of Object.entries(LABELS_PARAMS)) {
    fireEvent.change(screen.getByLabelText(regex), { target: { value: String(valores[campo as keyof typeof PARAMS_REQ03]) } });
  }
}

describe("EquiposPage", () => {
  it("lista equipos con su tipo legible y parámetros", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />, { rol: "TECNICO" });
    expect(await screen.findByText("RO-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Ósmosis inversa")).toBeInTheDocument();
    expect(screen.getByText(/tds_entrada_ppm/)).toBeInTheDocument();
  });

  it("TECNICO no ve acciones de escritura", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />, { rol: "TECNICO" });
    await screen.findByText("RO-2026-0001");
    expect(screen.queryByRole("button", { name: /nuevo equipo/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
  });

  it("lista vacía muestra «Sin datos disponibles»", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("Sin datos disponibles")).toBeInTheDocument();
  });

  it("ofrece los tres tipos de sistema", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    const opciones = Array.from((screen.getByLabelText("Tipo de sistema") as HTMLSelectElement).options).map((o) => o.value);
    expect(opciones).toEqual(["OSMOSIS_INVERSA", "ABLANDADOR", "FILTRO"]);
  });

  it("crea un equipo con el body que espera la API", async () => {
    const f = mockApi([
      { path: "/api/v1/equipos", body: [] },
      SIN_PREDICCIONES,
      { method: "POST", path: "/api/v1/equipos", status: 201, body: EQUIPO },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar({ tipo: "ABLANDADOR" });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /nuevo equipo/i });
    expect(JSON.parse((posts(f)[0][1] as RequestInit).body as string)).toEqual({
      serie: "RO-1",
      cliente_ruc: "20612493821",
      tipo_sistema: "ABLANDADOR",
      fecha_instalacion: "2026-01-15",
      parametros_nominales: PARAMS_REQ03,
    });
  });

  it("parámetros nominales: un campo vacío se rechaza", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    fireEvent.change(screen.getByLabelText(/tds entrada/i), { target: { value: "" } });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/valor numérico/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("parámetros nominales: un texto no numérico se rechaza", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    fireEvent.change(screen.getByLabelText(/conductividad/i), { target: { value: "abc" } });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/valor numérico/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("parámetros nominales: pH fuera de 0-14 se rechaza", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar({ params: { ph: 15 } });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/valor máximo es 14/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("rechaza serie vacía, RUC inválido y fecha futura", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar({ serie: " ", ruc: "123", fecha: "2999-01-01" });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/serie es obligatoria/i)).toBeInTheDocument();
    expect(screen.getByText(/exactamente 11 dígitos/i)).toBeInTheDocument();
    expect(screen.getByText(/no puede ser futura/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("muestra el 409 de serie duplicada", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [] },
      SIN_PREDICCIONES,
      { method: "POST", path: "/api/v1/equipos", status: 409, body: { detail: "Ya existe un equipo con esa serie" } },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ya existe un equipo con esa serie");
  });

  it("equipo sin predicción muestra el badge «Sin evaluar»", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("Sin evaluar")).toBeInTheDocument();
  });

  it("equipo con predicción ROJO muestra el badge y el panel de alertas", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", body: [{ equipo_serie: "RO-2026-0001", dias_vida_util_remanente: 12, nivel_alerta: "ROJO" }] },
    ]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText(/rojo/i)).toBeInTheDocument();
    expect(screen.getByText(/riesgo crítico/i)).toBeInTheDocument();
    expect(screen.getByText(/RO-2026-0001 — 12 días restantes/i)).toBeInTheDocument();
  });

  it("sin equipos en ROJO no muestra el panel de alertas", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", body: [{ equipo_serie: "RO-2026-0001", dias_vida_util_remanente: 200, nivel_alerta: "VERDE" }] },
    ]);
    renderWithProviders(<EquiposPage />);
    await screen.findByText(/verde/i);
    expect(screen.queryByText(/riesgo crítico/i)).not.toBeInTheDocument();
  });

  it("si falla la consulta de predicciones, la tabla de equipos igual se renderiza", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", status: 500, body: { detail: "Error interno" } },
    ]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("RO-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Sin evaluar")).toBeInTheDocument();
    expect(screen.queryByText(/riesgo crítico/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Correr las pruebas para verificar que fallan**

Run: `cd frontend && npm.cmd test -- --run src/features/equipos/EquiposPage.test.tsx`
Expected: fallan las 4 pruebas nuevas (no existe el badge ni el panel); las demás pueden fallar también por el mock `SIN_PREDICCIONES` sin consumidor — verifica que los mensajes de fallo apuntan a elementos que todavía no existen, no a errores de sintaxis.

- [ ] **Step 3: Implementar el badge y el panel en `EquiposPage.tsx`**

Agrega al tope del archivo, junto a los demás tipos:
```tsx
type NivelAlerta = "VERDE" | "AMARILLO" | "ROJO";
type PrediccionRul = { equipo_serie: string; dias_vida_util_remanente: number; nivel_alerta: NivelAlerta };

const COLORES_ALERTA: Record<NivelAlerta, string> = {
  VERDE: "bg-emerald-50 text-emerald-700 border-emerald-200",
  AMARILLO: "bg-amber-50 text-amber-700 border-amber-200",
  ROJO: "bg-red-50 text-red-700 border-red-200",
};

function BadgeAlerta({ prediccion }: { prediccion: PrediccionRul | undefined }) {
  if (!prediccion) {
    return (
      <span className="inline-block rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-500">
        Sin evaluar
      </span>
    );
  }
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-semibold ${COLORES_ALERTA[prediccion.nivel_alerta]}`}>
      {prediccion.nivel_alerta} · {prediccion.dias_vida_util_remanente} días
    </span>
  );
}
```

Dentro del componente `EquiposPage`, junto al `useQuery` de equipos:
```tsx
const predicciones = useQuery({
  queryKey: ["equipos", "predicciones-rul"],
  queryFn: () => apiFetch<PrediccionRul[]>("/equipos/predicciones-rul"),
});
const prediccionPorSerie = new Map((predicciones.data ?? []).map((p) => [p.equipo_serie, p]));
const enRiesgo = (predicciones.data ?? []).filter((p) => p.nivel_alerta === "ROJO");
```

Justo antes del `<DataTable`, agrega el panel de alertas:
```tsx
{enRiesgo.length > 0 && (
  <div className="mb-4 rounded-2xl border border-red-200 bg-red-50/60 p-4">
    <h2 className="text-sm font-bold text-red-800 mb-1">Equipos en riesgo crítico de falla</h2>
    <ul className="text-sm text-red-700 list-disc list-inside">
      {enRiesgo.map((p) => (
        <li key={p.equipo_serie}>{p.equipo_serie} — {p.dias_vida_util_remanente} días restantes</li>
      ))}
    </ul>
  </div>
)}
```

Agrega la columna al arreglo `columns` del `DataTable` (al final, después de "Parámetros nominales"):
```tsx
{ header: "RUL", cell: (e) => <BadgeAlerta prediccion={prediccionPorSerie.get(e.serie)} /> },
```

- [ ] **Step 4: Correr las pruebas para verificar que pasan**

Run: `cd frontend && npm.cmd test -- --run src/features/equipos/EquiposPage.test.tsx`
Expected: PASS (14 tests: 10 existentes + 4 nuevas).

- [ ] **Step 5: Correr toda la suite de frontend**

Run: `cd frontend && npm.cmd test -- --run`
Expected: todos los tests en verde.

- [ ] **Step 6: Build de producción**

Run: `cd frontend && npm.cmd run build`
Expected: compila limpio, sin errores de TypeScript.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/equipos/EquiposPage.tsx frontend/src/features/equipos/EquiposPage.test.tsx
git commit -m "feat: badges de nivel de alerta RUL y panel de equipos en riesgo"
```

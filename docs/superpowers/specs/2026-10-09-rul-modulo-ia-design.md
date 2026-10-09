# Módulo 4.2 — Inteligencia Artificial (RUL y Supervivencia): Diseño

**Estado:** Aprobado por el usuario en brainstorming (2026-10-09). Listo para `writing-plans`.

## 1. Propósito y alcance

Dar a Gerencia (y a los técnicos de campo, como consumidores de solo lectura) una estimación de Vida Útil Remanente (RUL) por equipo, con alertas preventivas de falla crítica, calculada mediante análisis de supervivencia (Kaplan-Meier + Cox PH) aislado por completo de la API transaccional, ejecutado como rutina batch programada en GitHub Actions hacia la tabla `predicciones_rul` en Neon.

**Cubre del EDT:**
- 4.2.1 Preparación y depuración de historiales técnicos
- 4.2.2 Pipeline de supervivencia (lifelines / Cox PH)
- 4.2.3 Aislamiento batch en GitHub Actions hacia tabla predicciones
- 4.2.4 Visualización de alertas de falla crítica en web

**No cubre:**
- 4.3 (verificación de calidad general / ISO 25010) — fase separada.
- Captura de lecturas de agua reales como columnas estructuradas en Postgres — hoy solo existen como JSON dentro de `actas_inmutables.payload_raw`, y extraerlas/normalizarlas queda fuera de alcance de este módulo (ver sección 2, punto 2).
- Reentrenamiento automático disparado por volumen de datos reales — el modelo usa dataset sintético en esta fase; migrar a datos reales es trabajo futuro explícitamente fuera de este spec.
- Cualquier UI de administración para ajustar manualmente los umbrales de alerta o los parámetros de calibración — viven como constantes documentadas en código, no configurables desde la web.

## 2. Contexto y decisiones de diseño confirmadas con el usuario

1. **Estado real de los datos (relevado antes de diseñar):** `ordenes_servicio` tiene 6 filas en Neon (dato de demo, no producción). Las 8 lecturas de agua por orden nunca se persisten en columnas estructuradas — solo existen como JSON opaco dentro de `actas_inmutables.payload_raw` (parte de la cadena de hash inmutable, RN-04). `equipos` no tiene ningún campo de reemplazo/falla/baja. `tipo_intervencion` en `ordenes_servicio` solo toma `PREVENTIVO`/`CORRECTIVO` en la práctica (sin CHECK constraint). `predicciones_rul` no existe aún ni como modelo SQLAlchemy ni como migración — toda la Fase 4.2 está sin construir. No existe `.github/workflows/` — este es el primer workflow del repo.
2. **Fuente del dataset de entrenamiento:** sintético, calibrado con rangos de vida útil de literatura de tratamiento de agua **ajustados a las condiciones de Trujillo** (agua SEDALIB más dura y con más turbidez estacional que el promedio genérico internacional — ver tabla en sección 4.1). Las 6 órdenes reales y los `parametros_nominales` reales de cada equipo sirven como contexto/ancla, no como el dataset principal de entrenamiento.
3. **Definición de "falla crítica":** cruce de un umbral de calidad de agua clínicamente relevante (no una intervención `CORRECTIVO` simulada). El generador sintético muestrea directamente un tiempo-hasta-el-evento desde una distribución Weibull calibrada por `tipo_sistema`, sin simular series de tiempo día a día de TDS/pH/conductividad.
4. **Disparo del batch:** cron nocturno (GitHub Actions `schedule`) + disparo manual (`workflow_dispatch`), ambos corriendo en el runner gratuito de GitHub — nunca en el contenedor de Render (512 MB / 0.1 vCPU).
5. **Persistencia del dataset sintético:** efímero — se regenera en memoria en cada corrida con una semilla fija (determinístico, reproducible), sin tabla nueva para guardarlo.
6. **Covariables para calificar equipos reales:** solo `días en servicio` (hoy − `fecha_instalacion`) y `tipo_sistema` (para estratificar la curva base). Intentar extraer lecturas reales del `payload_raw` como covariable adicional queda fuera de alcance — con 6 órdenes repartidas entre 14 equipos, el beneficio es marginal frente a la complejidad de parsear JSON por equipo.

## 3. Arquitectura — Paquete de ML aislado (`backend/app/ml/`)

Este paquete **nunca se importa desde `app/api/` ni desde `app/main.py`** — es código batch independiente, ejecutado solo por el workflow de GitHub Actions vía `python -m app.ml.batch_predicciones`. Esto garantiza el aislamiento de la API transaccional que exige `CLAUDE.md`.

### 3.1 `backend/app/ml/dataset_sintetico.py`

```python
import numpy as np
import pandas as pd

# Vida util mediana y rango por tipo_sistema, calibrados con literatura de tratamiento
# de agua y ajustados a las condiciones de Trujillo (SEDALIB: agua mas dura y con mas
# turbidez estacional que el promedio generico internacional). Documentado aqui, no
# enterrado en numeros magicos — ajustable si hay cifras mas precisas de campo.
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
    Determinístico: misma semilla -> mismo dataset, siempre."""
    rng = np.random.default_rng(semilla)
    filas = []
    for tipo, cal in CALIBRACION.items():
        # Forma de Weibull calibrada para que la mediana caiga en mediana_dias
        forma = 1.5
        escala = cal["mediana_dias"] / (np.log(2) ** (1 / forma))
        duraciones = rng.weibull(forma, n_por_tipo) * escala
        duraciones = np.clip(duraciones, cal["min_dias"], cal["max_dias"])
        eventos = rng.random(n_por_tipo) < PROPORCION_EVENTO
        for d, e in zip(duraciones, eventos):
            filas.append({"duracion_dias": float(d), "evento": int(e), "tipo_sistema": tipo})
    return pd.DataFrame(filas)
```

### 3.2 `backend/app/ml/modelo_rul.py`

```python
from datetime import date

import pandas as pd
from lifelines import CoxPHFitter

UMBRAL_ROJO_DIAS = 30
UMBRAL_AMARILLO_DIAS = 90


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
    """Devuelve {dias_vida_util_remanente, nivel_alerta} para un equipo real,
    o lanza ParametrosImposibles si fecha_instalacion es invalida (REQ-19)."""
    dias_en_servicio = (hoy - fecha_instalacion).days
    if dias_en_servicio < 0:
        raise ParametrosImposibles(f"fecha_instalacion futura: {fecha_instalacion}")
    # mediana de supervivencia del estrato correspondiente, vida util total esperada
    fila = pd.DataFrame([{"tipo_sistema": tipo_sistema}])
    fila = pd.get_dummies(fila, columns=["tipo_sistema"], drop_first=True)
    fila = fila.reindex(columns=cph.params_.index, fill_value=0)
    vida_util_total = cph.predict_median(fila).iloc[0]
    dias_restantes = max(0.0, float(vida_util_total) - dias_en_servicio)
    return {"dias_vida_util_remanente": round(dias_restantes), "nivel_alerta": nivel_alerta(dias_restantes)}


class ParametrosImposibles(Exception):
    pass
```

### 3.3 `backend/app/ml/batch_predicciones.py`

```python
import asyncio
from datetime import date, timezone, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine  # motor async ya existente, reutilizado tal cual
from app.ml.dataset_sintetico import generar_dataset
from app.ml.modelo_rul import ParametrosImposibles, ajustar_modelo, calificar_equipo
from app.models.equipo import Equipo

TIPOS_RECONOCIDOS = {"OSMOSIS_INVERSA", "ABLANDADOR", "FILTRO"}


async def correr_batch() -> None:
    dataset = generar_dataset()
    cph = ajustar_modelo(dataset)

    engine = get_engine()
    async with AsyncSession(engine) as session:
        equipos = (await session.execute(select(Equipo))).scalars().all()
        hoy = datetime.now(timezone.utc).date()
        resultados = []
        for e in equipos:
            if e.tipo_sistema not in TIPOS_RECONOCIDOS:
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
            await session.execute(
                text(
                    """
                    INSERT INTO predicciones_rul (equipo_serie, dias_vida_util_remanente, nivel_alerta, actualizado_en)
                    VALUES (:serie, :dias, :nivel, now())
                    ON CONFLICT (equipo_serie) DO UPDATE
                    SET dias_vida_util_remanente = EXCLUDED.dias_vida_util_remanente,
                        nivel_alerta = EXCLUDED.nivel_alerta,
                        actualizado_en = EXCLUDED.actualizado_en
                    """
                ),
                {"serie": serie, "dias": dias, "nivel": nivel},
            )
        await session.commit()
        print(f"OK: {len(resultados)} equipos calificados.")


if __name__ == "__main__":
    asyncio.run(correr_batch())
```

(`app.core.db` necesita exponer `get_engine()` si hoy solo expone `get_session`/`make_engine` para FastAPI — el plan de implementación decide el ajuste exacto sin romper los usos existentes.)

### 3.4 Tabla nueva — `backend/app/models/prediccion_rul.py` + migración Alembic

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
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

Migración Alembic estándar (`alembic revision --autogenerate`), igual al patrón ya usado en `194ec320cb67_esquema_inicial_fase_3_1.py`.

### 3.5 `.github/workflows/rul-batch.yml`

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
      - run: pip install -e ./backend[ml]
      - run: python -m app.ml.batch_predicciones
        working-directory: backend
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL_PROD }}
```

`DATABASE_URL_PROD` es un secret nuevo de GitHub Actions (la cadena de conexión `-pooler` de la rama `main` de Neon) — nunca se pega en el repo ni en esta sesión; el plan de implementación lo documenta como paso manual del usuario, igual que se hizo con las variables de entorno de Render en la Fase 3.3.

`pip install -e ./backend[ml]` implica un extra `ml` nuevo en `backend/pyproject.toml` (`lifelines`, `scikit-learn`, `pandas`, `numpy`) separado de las dependencias core de la API — así el contenedor de Render (que solo instala las dependencias base) nunca carga estas librerías pesadas.

### 3.6 Backend — endpoint de lectura

`backend/app/api/v1/equipos.py` (extensión del router existente, mismo patrón de acceso que el resto del archivo — `Depends(get_current_user)`, sin restricción de rol, igual que las demás rutas GET de equipos):

```python
@router.get("/{serie}/prediccion-rul", response_model=PrediccionRulOut)
async def leer_prediccion_rul(serie: str, session: AsyncSession = Depends(get_session)):
    if await session.get(Equipo, serie) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
    prediccion = await session.get(PrediccionRul, serie)
    if prediccion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aún no hay predicción RUL para este equipo")
    return prediccion
```

## 4. Arquitectura — Frontend

- `EquiposPage.tsx`: columna nueva en la tabla (`DataTable`) con un badge de `nivel_alerta` (🟢/🟡/🔴), obtenido vía un `useQuery` adicional por fila o — más simple y consistente con el resto del código — un único `GET /api/v1/equipos` que ya trae todo, **y una consulta separada por equipo visible** solo si el usuario expande detalle (el plan de implementación decide el mecanismo exacto de carga para no disparar N llamadas por fila en una tabla grande). Equipo sin predicción aún (el batch nunca corrió para él) muestra un badge neutro "Sin evaluar", no un error.
- Panel/banner separado arriba de la tabla: lista solo los equipos en 🔴 ROJO, con su propio estado vacío ("Sin datos disponibles" si no hay ninguno en riesgo) — REQ-18, para que la alerta de falla crítica no se pierda entre filas de una tabla larga.

## 5. Manejo de errores

- **Workflow:** cualquier excepción no capturada en `correr_batch()` propaga y el job de GitHub Actions falla explícitamente (exit ≠ 0) — nunca se escribe un resultado parcial silencioso.
- **Por equipo (REQ-19):** `tipo_sistema` no reconocido o `fecha_instalacion` futura → se omite con `WARN` en el log, el resto de equipos se sigue calificando.
- **Transacción única:** todo el upsert de la corrida se confirma en un solo `commit()` al final — si algo falla a mitad de camino, nada cambia en `predicciones_rul`.
- **`equipos` vacía o sin equipos calificables:** la corrida termina exitosamente con cero filas escritas y un mensaje de log, no es un error.
- **Idempotencia:** `ON CONFLICT (equipo_serie) DO UPDATE` — correr el batch más de una vez el mismo día es seguro.
- **Endpoint:** equipo inexistente → 404 "Equipo no encontrado"; equipo real sin predicción aún → 404 "Aún no hay predicción RUL para este equipo" (nunca 500, nunca un valor inventado).

## 6. Pruebas

### 6.1 Backend — `backend/tests/test_ml_dataset_sintetico.py`
- Misma semilla → mismo dataset (determinismo, comparación fila a fila o por hash).
- Duraciones muestreadas caen dentro de `[min_dias, max_dias]` del `tipo_sistema` correspondiente.
- Proporción de eventos/censurados ≈ 70/30 dentro de una tolerancia razonable sobre una muestra grande.

### 6.2 Backend — `backend/tests/test_ml_modelo_rul.py`
- `ajustar_modelo()` no lanza excepción contra el dataset sintético generado por defecto.
- `nivel_alerta()`: <30 → ROJO, exactamente 30 → AMARILLO (corte no incluido en ROJO), 30–90 → AMARILLO, exactamente 90 → VERDE, >90 → VERDE.
- `calificar_equipo()` con `fecha_instalacion` futura lanza `ParametrosImposibles`.
- `calificar_equipo()` con antigüedad 0 (recién instalado) devuelve `dias_vida_util_remanente` cercano a la vida útil mediana completa del tipo.

### 6.3 Backend — `backend/tests/test_ml_batch_predicciones.py` (contra la BD de prueba, fixtures de `conftest.py`)
- Con 2–3 equipos reales de tipos distintos, `correr_batch()` puebla `predicciones_rul` con una fila por equipo calificable.
- Un equipo con `fecha_instalacion` futura se omite (no aparece en `predicciones_rul`), el resto sí.
- Correr `correr_batch()` dos veces seguidas actualiza las filas existentes (mismo `equipo_serie`, `actualizado_en` más reciente), no duplica.
- Sin ningún equipo en la tabla `equipos` → corrida exitosa, `predicciones_rul` sigue vacía.

### 6.4 Backend — migración
- `alembic upgrade head` crea `predicciones_rul` con el `CHECK` de `nivel_alerta` correcto (inserción con un valor fuera de la lista falla a nivel de BD).

### 6.5 Backend — `backend/tests/test_predicciones_rul.py` (endpoint)
- GERENCIA y TECNICO → 200 para un equipo con predicción existente.
- Sin token → 401.
- Equipo inexistente → 404 "Equipo no encontrado".
- Equipo real sin fila en `predicciones_rul` → 404 "Aún no hay predicción RUL para este equipo".

### 6.6 Frontend — `EquiposPage.test.tsx`
- Equipo con predicción muestra el badge del color correcto según `nivel_alerta`.
- Equipo sin predicción muestra el badge neutro "Sin evaluar", no rompe el render.
- Panel de alertas ROJO: lista solo los equipos en ROJO; vacío cuando ninguno está en ROJO.

### 6.7 GitHub Actions (manual, declarado explícitamente)
- Tras el primer merge, disparar `workflow_dispatch` una vez manualmente y confirmar en Neon que `predicciones_rul` se pobló — no se finge cobertura automatizada que no existe en este entorno (mismo criterio que el Dockerfile de la Fase 3.3).

## 7. Puntos que este spec resuelve explícitamente

- El módulo de IA corre como paquete Python aislado (`app/ml/`), nunca importado por la API — la separación la garantiza la estructura de imports, no solo una convención documentada.
- El dataset de entrenamiento es sintético por decisión explícita, dado que hoy existen 6 órdenes reales (dato de demo) y ninguna lectura de agua estructurada en Postgres — declarado como limitación de alcance, no escondido.
- Las curvas de supervivencia están calibradas a las condiciones de agua de Trujillo (SEDALIB), no a un promedio genérico internacional, con los números documentados como constantes ajustables en código.
- "Falla crítica" es un umbral de calidad de agua (vía el tiempo-hasta-evento muestreado), no una intervención `CORRECTIVO` simulada.
- El batch nunca corre en el contenedor de Render (0.1 vCPU/512 MB) — corre en el runner gratuito de GitHub Actions, con sus propias dependencias (`lifelines`/`scikit-learn`/`pandas`/`numpy`) aisladas en un extra `[ml]` que el Dockerfile de producción no instala.
- Tolerancia a anomalías (REQ-19): un equipo con datos imposibles se omite y se loguea, nunca tumba la corrida completa.
- Idempotencia y atomicidad: `ON CONFLICT DO UPDATE` + una sola transacción por corrida — nunca hay un estado parcial visible en `predicciones_rul`.

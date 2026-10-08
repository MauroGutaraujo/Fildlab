# Módulo 4.1 — Business Intelligence (Rentabilidad y SLA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar a Gerencia dos endpoints analíticos (rentabilidad por contrato, cumplimiento de SLA) y un tablero web con Apache ECharts que los visualiza, sobre datos que ya existen hoy en Neon.

**Architecture:** Dos endpoints GET de solo lectura en un router nuevo `backend/app/api/v1/analytics.py` (GERENCIA-only), con toda la agregación hecha en SQL vía un servicio nuevo `backend/app/services/analytics.py` (nunca cargando filas crudas a memoria Python). En el frontend, una página nueva `frontend/src/features/bi/BiPage.tsx` con un selector de mes (`<input type="month">`) que alimenta dos componentes de gráfico independientes (`TableroRentabilidad`, `TableroSla`), cada uno con su propio loading/error/vacío, usando `echarts/core` + `echarts-for-react/lib/core` con imports modulares.

**Tech Stack:** FastAPI + SQLAlchemy async (backend, sin dependencias nuevas), React + TanStack Query + `echarts` + `echarts-for-react` (frontend, dos dependencias nuevas).

**Spec:** `docs/superpowers/specs/2026-10-02-bi-modulo-analytics-design.md`

## Global Constraints

- Presupuesto S/. 0.00: sin dependencias de pago, sin servicios nuevos — solo las dos dependencias npm `echarts` y `echarts-for-react` (ambas open-source).
- Ambos endpoints van bajo `dependencies=[Depends(require_role("GERENCIA"))]` a nivel de router — nunca accesibles para TECNICO (RN-01).
- Toda agregación (`SUM`, `GROUP BY`, `COUNT`) ocurre en SQL vía SQLAlchemy — nunca se traen filas crudas de `movimientos_inventario` u `ordenes_servicio` a Python para sumarlas ahí (límite de 512 MB RAM / 0.1 vCPU de Render).
- Costo de repuestos: solo órdenes con `estado = 'LIQUIDADA'`, atribuidas por mes de `fecha_creacion_cliente` (mes de servicio, no de liquidación).
- SLA: sobre **todas** las órdenes del mes (`fecha_creacion_cliente`), sin filtrar por `estado`.
- Sin componente de horas de mano de obra en el margen (no existe ese campo en el esquema) — margen = ingreso contractual − costo de repuestos.
- `periodo` siempre formato `YYYY-MM` (mes calendario), validado con un patrón Pydantic — nunca rango libre.
- El backend **nunca** devuelve 404 por ausencia de datos — siempre 200 con listas vacías y `pct_cumplimiento`/`margen_pct` en `null` si no se puede calcular (evita división entre cero).
- Texto exacto del estado vacío en el frontend: `"Sin datos disponibles para el periodo"` (REQ-16).
- Sin migración de Alembic: los dos endpoints son de solo lectura sobre tablas que ya existen (`contratos`, `ordenes_servicio`, `movimientos_inventario`, `repuestos`, `clientes`) — no se crea ni se altera ninguna tabla.
- `echarts`/`echarts-for-react` se importan de forma modular (`echarts/core` + solo los charts/componentes usados) — nunca el bundle completo de `echarts`.
- En Windows, todo comando de Node se ejecuta con `npm.cmd` (no `npm`).

## Review Focus

- **Orden sin `tiempo_respuesta_horas`** (aún no medida, columna `NULL`): no debe aparecer en `ordenes_fuera_sla` ni romper el cálculo de `pct_cumplimiento` — debe seguir contando solo en `total_ordenes`.
- **Orden con `tiempo_respuesta_horas` exactamente igual a `sla_horas_max_respuesta`** del contrato: debe contar como cumplida (el corte es estrictamente `>`, no `>=`), no debe aparecer en `ordenes_fuera_sla`.
- **Contrato cuyo rango no se solapa con el mes pedido** (terminó antes de que empezara el mes, o empieza después de que termine): no debe aparecer en la lista de `/analytics/rentabilidad` para ese periodo.
- **`periodo` mal formado** (`"2026-13"`, `"abc"`, cadena vacía, o el parámetro ausente): debe responder 422, nunca 500 ni una fecha inventada.
- **Orden `LIQUIDADA` de un contrato distinto consumiendo el mismo código de repuesto en el mismo mes**: el costo de cada contrato debe quedar separado por el `GROUP BY OrdenServicio.contrato_id`, nunca mezclado entre contratos.

---

## Backend

### Task 1: Endpoint de rentabilidad por contrato

**Files:**
- Create: `backend/app/schemas/analytics.py`
- Create: `backend/app/services/analytics.py`
- Create: `backend/app/api/v1/analytics.py`
- Modify: `backend/app/main.py` (registrar el router nuevo)
- Test: `backend/tests/test_analytics.py`

**Interfaces:**
- Consumes: `app.core.db.get_session`, `app.core.deps.require_role` (ya existen), modelos `Contrato`, `Cliente`, `OrdenServicio`, `MovimientoInventario`, `Repuesto` (ya existen, sin cambios).
- Produces: `app.services.analytics.rentabilidad_por_contrato(session, periodo) -> list[dict]` y `app.services.analytics._rango_mes(periodo) -> tuple[datetime, datetime]` — Task 2 (SLA) reutiliza `_rango_mes`. Ruta `GET /api/v1/analytics/rentabilidad?periodo=YYYY-MM`.

- [ ] **Step 1: Escribir el archivo de esquemas**

`backend/app/schemas/analytics.py`:
```python
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

# YYYY-MM, mes 01-12 — mismo mecanismo que app/schemas/common.py:Ruc
Periodo = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]


class ContratoRentabilidadOut(BaseModel):
    contrato_id: int
    cliente_ruc: str
    razon_social: str
    ingreso_soles: Decimal
    costo_repuestos_soles: Decimal
    margen_soles: Decimal
    margen_pct: float | None


class RentabilidadOut(BaseModel):
    periodo: str
    contratos: list[ContratoRentabilidadOut]


class OrdenFueraSlaOut(BaseModel):
    orden_id: UUID
    equipo_serie: str | None
    razon_social: str
    tiempo_respuesta_horas: Decimal
    sla_horas_max_respuesta: int


class SlaOut(BaseModel):
    periodo: str
    total_ordenes: int
    ordenes_fuera_sla: list[OrdenFueraSlaOut]
    pct_cumplimiento: float | None
```

(`OrdenFueraSlaOut`/`SlaOut` se definen aquí mismo aunque los use el Task 2, para no tocar este archivo dos veces.)

- [ ] **Step 2: Escribir la prueba que falla, para rentabilidad**

`backend/tests/test_analytics.py` (archivo nuevo — primera tanda de pruebas):
```python
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.contrato import Contrato
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio
from app.models.repuesto import MovimientoInventario, Repuesto


async def _contrato(db, crear_cliente, *, ruc="20612493821", monto="2500.00", sla=4,
                     inicio=date(2026, 1, 1), fin=date(2026, 12, 31)):
    await crear_cliente(ruc)
    c = Contrato(cliente_ruc=ruc, fecha_inicio=inicio, fecha_fin=fin,
                 monto_mensual_soles=Decimal(monto), sla_horas_max_respuesta=sla)
    db.add(c)
    await db.flush()
    return c


async def _orden(db, contrato, crear_usuario, *, estado="LIQUIDADA", fecha, tiempo_respuesta=None):
    tecnico = await crear_usuario("TECNICO")
    serie = f"SER-{uuid.uuid4().hex[:8]}"
    db.add(Equipo(serie=serie, cliente_ruc=contrato.cliente_ruc, contrato_id=contrato.id,
                  tipo_sistema="OSMOSIS_INVERSA", fecha_instalacion=date(2026, 1, 2),
                  parametros_nominales={"presion_psi": 60}))
    await db.flush()
    o = OrdenServicio(id=uuid.uuid4(), contrato_id=contrato.id, equipo_serie=serie, tecnico_id=tecnico.id,
                      tipo_intervencion="PREVENTIVO", estado=estado,
                      fecha_creacion_cliente=fecha, tiempo_respuesta_horas=tiempo_respuesta)
    db.add(o)
    await db.flush()
    return o


async def _consumo(db, orden, usuario_id, *, repuesto_codigo="FILT-05", cantidad=2, costo_unitario="5.00"):
    rep = await db.get(Repuesto, repuesto_codigo)
    if rep is None:
        rep = Repuesto(codigo=repuesto_codigo, descripcion=repuesto_codigo, costo_unitario_soles=Decimal(costo_unitario))
        db.add(rep)
        await db.flush()
    db.add(MovimientoInventario(repuesto_codigo=repuesto_codigo, tipo="SALIDA_ORDEN", cantidad=cantidad,
                                orden_id=orden.id, usuario_id=usuario_id))
    await db.flush()


async def test_rentabilidad_solo_gerencia(client, tecnico_h):
    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=tecnico_h)
    assert r.status_code == 403


async def test_rentabilidad_sin_token_401(client):
    assert (await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09")).status_code == 401


async def test_rentabilidad_periodo_invalido_422(client, gerente_h):
    for periodo in ("2026-13", "abc", "", "2026-9"):
        r = await client.get(f"/api/v1/analytics/rentabilidad?periodo={periodo}", headers=gerente_h)
        assert r.status_code == 422, periodo
    assert (await client.get("/api/v1/analytics/rentabilidad", headers=gerente_h)).status_code == 422


async def test_rentabilidad_sin_contratos_en_el_mes_lista_vacia(client, gerente_h):
    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.status_code == 200
    assert r.json() == {"periodo": "2026-09", "contratos": []}


async def test_rentabilidad_calcula_ingreso_costo_y_margen(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, monto="2500.00")
    orden = await _orden(db, contrato, crear_usuario, estado="LIQUIDADA",
                         fecha=datetime(2026, 9, 15, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id, cantidad=2, costo_unitario="5.00")  # 2 x 5.00 = 10.00
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.status_code == 200
    c = r.json()["contratos"][0]
    assert c["contrato_id"] == contrato.id
    assert c["ingreso_soles"] == "2500.00"
    assert c["costo_repuestos_soles"] == "10.00"
    assert c["margen_soles"] == "2490.00"
    assert c["margen_pct"] == pytest.approx(99.6)


async def test_rentabilidad_orden_comprometida_no_liquidada_no_suma_costo(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente)
    orden = await _orden(db, contrato, crear_usuario, estado="COMPROMETIDA",
                         fecha=datetime(2026, 9, 15, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id)
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    c = r.json()["contratos"][0]
    assert c["costo_repuestos_soles"] == "0.00" or c["costo_repuestos_soles"] == "0"


async def test_rentabilidad_orden_de_otro_mes_no_se_cuenta(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente)
    orden = await _orden(db, contrato, crear_usuario, estado="LIQUIDADA",
                         fecha=datetime(2026, 8, 15, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id)
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    c = r.json()["contratos"][0]
    assert c["costo_repuestos_soles"] in ("0.00", "0")


async def test_rentabilidad_contrato_fuera_de_rango_del_mes_no_aparece(client, gerente_h, db, crear_cliente):
    await _contrato(db, crear_cliente, inicio=date(2025, 1, 1), fin=date(2026, 6, 30))  # termina antes de sept.
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.json()["contratos"] == []


async def test_rentabilidad_dos_contratos_no_mezclan_costos(client, gerente_h, db, crear_cliente, crear_usuario):
    c1 = await _contrato(db, crear_cliente, ruc="20612493821")
    c2 = await _contrato(db, crear_cliente, ruc="20100047218")
    o1 = await _orden(db, c1, crear_usuario, estado="LIQUIDADA", fecha=datetime(2026, 9, 10, tzinfo=timezone.utc))
    o2 = await _orden(db, c2, crear_usuario, estado="LIQUIDADA", fecha=datetime(2026, 9, 11, tzinfo=timezone.utc))
    await _consumo(db, o1, o1.tecnico_id, repuesto_codigo="FILT-05", cantidad=1, costo_unitario="5.00")
    await _consumo(db, o2, o2.tecnico_id, repuesto_codigo="FILT-05", cantidad=3, costo_unitario="5.00")
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    por_id = {c["contrato_id"]: c["costo_repuestos_soles"] for c in r.json()["contratos"]}
    assert por_id[c1.id] == "5.00"
    assert por_id[c2.id] == "15.00"
```

- [ ] **Step 3: Correr las pruebas para verificar que fallan**

Run: `cd backend && python -m pytest tests/test_analytics.py -v`
Expected: FAIL (ModuleNotFoundError / 404, el router no existe todavía).

- [ ] **Step 4: Implementar el servicio**

`backend/app/services/analytics.py`:
```python
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.models.orden import OrdenServicio
from app.models.repuesto import MovimientoInventario, Repuesto


def _rango_mes(periodo: str) -> tuple[datetime, datetime]:
    """periodo ya viene validado como YYYY-MM por el schema Periodo. Devuelve [inicio, fin) en UTC."""
    anio, mes = (int(x) for x in periodo.split("-"))
    inicio = datetime(anio, mes, 1, tzinfo=timezone.utc)
    fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc) if mes == 12 else datetime(anio, mes + 1, 1, tzinfo=timezone.utc)
    return inicio, fin


async def rentabilidad_por_contrato(session: AsyncSession, periodo: str) -> list[dict]:
    inicio, fin = _rango_mes(periodo)

    contratos = (
        await session.execute(
            select(Contrato, Cliente.razon_social)
            .join(Cliente, Cliente.ruc == Contrato.cliente_ruc)
            .where(Contrato.fecha_inicio < fin.date(), Contrato.fecha_fin >= inicio.date())
            .order_by(Contrato.id)
        )
    ).all()

    costos_q = (
        select(
            OrdenServicio.contrato_id,
            func.sum(MovimientoInventario.cantidad * Repuesto.costo_unitario_soles).label("costo"),
        )
        .select_from(MovimientoInventario)
        .join(OrdenServicio, OrdenServicio.id == MovimientoInventario.orden_id)
        .join(Repuesto, Repuesto.codigo == MovimientoInventario.repuesto_codigo)
        .where(
            MovimientoInventario.tipo == "SALIDA_ORDEN",
            OrdenServicio.estado == "LIQUIDADA",
            OrdenServicio.fecha_creacion_cliente >= inicio,
            OrdenServicio.fecha_creacion_cliente < fin,
        )
        .group_by(OrdenServicio.contrato_id)
    )
    costos = {contrato_id: costo for contrato_id, costo in (await session.execute(costos_q)).all()}

    resultado = []
    for contrato, razon_social in contratos:
        ingreso = contrato.monto_mensual_soles
        costo = costos.get(contrato.id) or Decimal("0.00")
        margen = ingreso - costo
        margen_pct = float(margen / ingreso * 100) if ingreso > 0 else None
        resultado.append(
            {
                "contrato_id": contrato.id,
                "cliente_ruc": contrato.cliente_ruc,
                "razon_social": razon_social,
                "ingreso_soles": ingreso,
                "costo_repuestos_soles": costo,
                "margen_soles": margen,
                "margen_pct": margen_pct,
            }
        )
    return resultado
```

- [ ] **Step 5: Implementar el router y registrarlo**

`backend/app/api/v1/analytics.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_role
from app.schemas.analytics import Periodo, RentabilidadOut
from app.services import analytics as svc

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_role("GERENCIA"))])


@router.get("/rentabilidad", response_model=RentabilidadOut)
async def rentabilidad(periodo: Periodo, session: AsyncSession = Depends(get_session)):
    contratos = await svc.rentabilidad_por_contrato(session, periodo)
    return {"periodo": periodo, "contratos": contratos}
```

Modify `backend/app/main.py`:
```python
from app.api.v1 import analytics, auth, clientes, contratos, equipos, health, inventario, liquidacion, ventas
```
(agrega `analytics,` a la lista, orden alfabético ya respetado) y, junto a los demás `include_router`:
```python
app.include_router(analytics.router, prefix="/api/v1")
```

- [ ] **Step 6: Correr las pruebas para verificar que pasan**

Run: `cd backend && python -m pytest tests/test_analytics.py -v`
Expected: PASS (9 tests).

- [ ] **Step 7: Correr toda la suite de backend para confirmar que nada se rompió**

Run: `cd backend && python -m pytest -q`
Expected: todos los tests existentes siguen en verde.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/analytics.py backend/app/services/analytics.py backend/app/api/v1/analytics.py backend/app/main.py backend/tests/test_analytics.py
git commit -m "feat: endpoint de rentabilidad por contrato (/api/v1/analytics/rentabilidad)"
```

---

### Task 2: Endpoint de cumplimiento de SLA

**Files:**
- Modify: `backend/app/services/analytics.py` (agregar `cumplimiento_sla`, reutiliza `_rango_mes` del Task 1)
- Modify: `backend/app/api/v1/analytics.py` (agregar la ruta `/sla`)
- Modify: `backend/tests/test_analytics.py` (agregar las pruebas de SLA al final del archivo)

**Interfaces:**
- Consumes: `app.services.analytics._rango_mes` (del Task 1), modelos `OrdenServicio`, `Contrato`, `Cliente`.
- Produces: `app.services.analytics.cumplimiento_sla(session, periodo) -> dict` con claves `total_ordenes`, `ordenes_fuera_sla`, `pct_cumplimiento`. Ruta `GET /api/v1/analytics/sla?periodo=YYYY-MM`.

- [ ] **Step 1: Agregar las pruebas que fallan, al final de `backend/tests/test_analytics.py`**

```python
async def test_sla_solo_gerencia(client, tecnico_h):
    assert (await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=tecnico_h)).status_code == 403


async def test_sla_periodo_invalido_422(client, gerente_h):
    assert (await client.get("/api/v1/analytics/sla?periodo=no-es-un-mes", headers=gerente_h)).status_code == 422


async def test_sla_sin_ordenes_en_el_mes(client, gerente_h):
    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    assert r.status_code == 200
    assert r.json() == {"periodo": "2026-09", "total_ordenes": 0, "ordenes_fuera_sla": [], "pct_cumplimiento": None}


async def test_sla_orden_que_excede_el_maximo_aparece_en_fuera_de_sla(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, sla=4)
    await _orden(db, contrato, crear_usuario, estado="SINCRONIZADA",
                fecha=datetime(2026, 9, 10, tzinfo=timezone.utc), tiempo_respuesta=Decimal("9.50"))
    await db.commit()

    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    b = r.json()
    assert b["total_ordenes"] == 1
    assert len(b["ordenes_fuera_sla"]) == 1
    assert b["ordenes_fuera_sla"][0]["tiempo_respuesta_horas"] == "9.50"
    assert b["ordenes_fuera_sla"][0]["sla_horas_max_respuesta"] == 4
    assert b["pct_cumplimiento"] == pytest.approx(0.0)


async def test_sla_orden_exactamente_en_el_limite_cuenta_como_cumplida(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, sla=4)
    await _orden(db, contrato, crear_usuario, fecha=datetime(2026, 9, 10, tzinfo=timezone.utc),
                tiempo_respuesta=Decimal("4.00"))
    await db.commit()

    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    b = r.json()
    assert b["ordenes_fuera_sla"] == []
    assert b["pct_cumplimiento"] == pytest.approx(100.0)


async def test_sla_orden_sin_tiempo_de_respuesta_aun_no_rompe_el_calculo(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, sla=4)
    await _orden(db, contrato, crear_usuario, fecha=datetime(2026, 9, 10, tzinfo=timezone.utc), tiempo_respuesta=None)
    await db.commit()

    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    b = r.json()
    assert b["total_ordenes"] == 1
    assert b["ordenes_fuera_sla"] == []
    assert b["pct_cumplimiento"] == pytest.approx(100.0)


async def test_sla_cuenta_ordenes_sin_importar_el_estado(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, sla=4)
    await _orden(db, contrato, crear_usuario, estado="SINCRONIZADA",
                fecha=datetime(2026, 9, 5, tzinfo=timezone.utc), tiempo_respuesta=Decimal("2.00"))
    await _orden(db, contrato, crear_usuario, estado="COMPROMETIDA",
                fecha=datetime(2026, 9, 6, tzinfo=timezone.utc), tiempo_respuesta=Decimal("2.00"))
    await _orden(db, contrato, crear_usuario, estado="LIQUIDADA",
                fecha=datetime(2026, 9, 7, tzinfo=timezone.utc), tiempo_respuesta=Decimal("2.00"))
    await db.commit()

    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    assert r.json()["total_ordenes"] == 3
```

- [ ] **Step 2: Correr las pruebas para verificar que fallan**

Run: `cd backend && python -m pytest tests/test_analytics.py -k sla -v`
Expected: FAIL (404, no existe `/analytics/sla` todavía).

- [ ] **Step 3: Agregar `cumplimiento_sla` a `backend/app/services/analytics.py`**

Agregar al final del archivo (los imports de `select`/`func`/modelos ya están arriba por el Task 1; agrega `Contrato`/`Cliente` si no quedaron importados):
```python
async def cumplimiento_sla(session: AsyncSession, periodo: str) -> dict:
    inicio, fin = _rango_mes(periodo)

    total_ordenes = (
        await session.execute(
            select(func.count())
            .select_from(OrdenServicio)
            .where(OrdenServicio.fecha_creacion_cliente >= inicio, OrdenServicio.fecha_creacion_cliente < fin)
        )
    ).scalar_one()

    filas = (
        await session.execute(
            select(
                OrdenServicio.id,
                OrdenServicio.equipo_serie,
                OrdenServicio.tiempo_respuesta_horas,
                Contrato.sla_horas_max_respuesta,
                Cliente.razon_social,
            )
            .select_from(OrdenServicio)
            .join(Contrato, Contrato.id == OrdenServicio.contrato_id)
            .join(Cliente, Cliente.ruc == Contrato.cliente_ruc)
            .where(
                OrdenServicio.fecha_creacion_cliente >= inicio,
                OrdenServicio.fecha_creacion_cliente < fin,
                OrdenServicio.tiempo_respuesta_horas > Contrato.sla_horas_max_respuesta,
            )
            .order_by(OrdenServicio.fecha_creacion_cliente)
        )
    ).all()

    ordenes_fuera_sla = [
        {
            "orden_id": orden_id,
            "equipo_serie": equipo_serie,
            "razon_social": razon_social,
            "tiempo_respuesta_horas": tiempo,
            "sla_horas_max_respuesta": sla_max,
        }
        for orden_id, equipo_serie, tiempo, sla_max, razon_social in filas
    ]

    pct_cumplimiento = (
        (total_ordenes - len(ordenes_fuera_sla)) / total_ordenes * 100 if total_ordenes > 0 else None
    )

    return {
        "total_ordenes": total_ordenes,
        "ordenes_fuera_sla": ordenes_fuera_sla,
        "pct_cumplimiento": pct_cumplimiento,
    }
```

Al tope del archivo, asegúrate de que estén importados `Contrato` (ya lo está, del Task 1) y `Cliente` (ya lo está).

- [ ] **Step 4: Agregar la ruta a `backend/app/api/v1/analytics.py`**

```python
from app.schemas.analytics import Periodo, RentabilidadOut, SlaOut
```
(cambia el import existente de `RentabilidadOut` para incluir también `SlaOut`) y agrega al final del archivo:
```python
@router.get("/sla", response_model=SlaOut)
async def sla(periodo: Periodo, session: AsyncSession = Depends(get_session)):
    datos = await svc.cumplimiento_sla(session, periodo)
    return {"periodo": periodo, **datos}
```

- [ ] **Step 5: Correr las pruebas para verificar que pasan**

Run: `cd backend && python -m pytest tests/test_analytics.py -v`
Expected: PASS (16 tests en total del archivo).

- [ ] **Step 6: Correr toda la suite de backend**

Run: `cd backend && python -m pytest -q`
Expected: todos los tests en verde, incluidos los existentes de otros módulos.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/analytics.py backend/app/api/v1/analytics.py backend/tests/test_analytics.py
git commit -m "feat: endpoint de cumplimiento de SLA (/api/v1/analytics/sla)"
```

---

## Frontend

### Task 3: Dependencia de ECharts

**Files:**
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: `echarts` y `echarts-for-react` instalados y disponibles para los Tasks 5 y 6.

- [ ] **Step 1: Agregar las dependencias**

En `frontend/package.json`, dentro de `"dependencies"` (orden alfabético, junto a `@tanstack/react-query`):
```json
"dependencies": {
  "@tanstack/react-query": "^5.59.0",
  "echarts": "^5.5.1",
  "echarts-for-react": "^3.0.2",
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^6.27.0"
},
```

- [ ] **Step 2: Instalar**

Run (PowerShell, Windows): `cd frontend; npm.cmd install`
Expected: instala sin errores, `package-lock.json` se actualiza.

- [ ] **Step 3: Verificar que el build sigue limpio**

Run: `cd frontend; npm.cmd run build`
Expected: compila limpio (las dependencias nuevas aún no se usan en ningún archivo, así que esto solo confirma que la instalación no rompió nada).

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: agrega echarts y echarts-for-react para el Modulo BI"
```

---

### Task 4: Página BI — ruta, nav y selector de periodo

**Files:**
- Create: `frontend/src/features/bi/BiPage.tsx`
- Create: `frontend/src/features/bi/BiPage.test.tsx`
- Modify: `frontend/src/App.tsx` (nueva ruta `/bi`, GERENCIA-only)
- Modify: `frontend/src/components/Layout.tsx` (nuevo ícono + entrada en `ENLACES`)

**Interfaces:**
- Consumes: `RequireRole` (`src/auth/RequireRole.tsx`, ya existe), patrón de rutas de `App.tsx` (ya existe).
- Produces: `BiPage` exportado — el Task 7 lo completa agregando `<TableroRentabilidad>`/`<TableroSla>` dentro. Por ahora `BiPage` solo renderiza el título y el selector de periodo, para que esta tarea sea revisable de forma independiente.

- [ ] **Step 1: Escribir la prueba que falla**

`frontend/src/features/bi/BiPage.test.tsx`:
```tsx
import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import { BiPage } from "./BiPage";
import { renderWithProviders } from "../../test/utils";

describe("BiPage", () => {
  it("el selector de periodo arranca en el mes actual", async () => {
    renderWithProviders(<BiPage />);
    const input = screen.getByLabelText("Periodo") as HTMLInputElement;
    const esperado = new Date().toISOString().slice(0, 7);
    expect(input.value).toBe(esperado);
  });

  it("TECNICO no ve el enlace BI en el navbar", async () => {
    const { container } = renderWithProviders(<BiPage />, { rol: "TECNICO" });
    // Esta prueba verifica BiPage en aislamiento; la del navbar completo va en Task de integración (Step 4).
    expect(container).toBeTruthy();
  });
});
```

- [ ] **Step 2: Correr la prueba para verificar que falla**

Run: `cd frontend; npm.cmd test -- --run src/features/bi/BiPage.test.tsx`
Expected: FAIL (no existe `./BiPage`).

- [ ] **Step 3: Crear `frontend/src/features/bi/BiPage.tsx`**

```tsx
import { useState } from "react";

function periodoActual(): string {
  return new Date().toISOString().slice(0, 7);
}

export function BiPage() {
  const [periodo, setPeriodo] = useState(periodoActual());

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Business Intelligence</h1>
        <label className="text-sm font-medium text-slate-700">
          Periodo
          <input
            type="month"
            aria-label="Periodo"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="ml-2 rounded border border-slate-300 px-2 py-1"
          />
        </label>
      </div>
      <div className="grid gap-6">{/* TableroRentabilidad y TableroSla se agregan en el Task 7 */}</div>
    </section>
  );
}
```

- [ ] **Step 4: Correr la prueba para verificar que pasa**

Run: `cd frontend; npm.cmd test -- --run src/features/bi/BiPage.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Agregar la ruta en `frontend/src/App.tsx`**

```tsx
import { BiPage } from "./features/bi/BiPage";
```
(agrégalo junto a los demás imports de `features/`, orden alfabético: después de `ClientesPage`, antes de `ContratosPage`) y, junto a las rutas `ventas`/`liquidacion`:
```tsx
<Route
  path="bi"
  element={
    <RequireRole roles={["GERENCIA"]}>
      <BiPage />
    </RequireRole>
  }
/>
```

- [ ] **Step 6: Agregar el ícono y la entrada de navegación en `frontend/src/components/Layout.tsx`**

Cambia:
```tsx
type IconoId = "clientes" | "contratos" | "equipos" | "inventario" | "ventas" | "liquidacion";
```
por:
```tsx
type IconoId = "clientes" | "contratos" | "equipos" | "inventario" | "ventas" | "liquidacion" | "bi";
```
Agrega una entrada al objeto `ICONOS` (un ícono de gráfico de barras simple):
```tsx
  bi: "M4 19V9m6 10V5m6 14v-7",
```
Y una entrada al final del arreglo `ENLACES`:
```tsx
  { to: "/bi", texto: "BI", icon: "bi", roles: ["GERENCIA"] },
```

- [ ] **Step 7: Prueba de integración — TECNICO no ve el enlace, GERENCIA sí**

Agrega a `frontend/src/components/Layout.test.tsx` si existe; si no existe, créalo:
```tsx
import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { Layout } from "./Layout";
import { renderWithProviders } from "../test/utils";

describe("Layout", () => {
  it("GERENCIA ve el enlace BI en el navbar", () => {
    renderWithProviders(<Layout />, { rol: "GERENCIA" });
    expect(screen.getByRole("link", { name: /bi/i })).toBeInTheDocument();
  });

  it("TECNICO no ve el enlace BI en el navbar", () => {
    renderWithProviders(<Layout />, { rol: "TECNICO" });
    expect(screen.queryByRole("link", { name: /bi/i })).not.toBeInTheDocument();
  });
});
```

Run: `cd frontend; npm.cmd test -- --run src/components/Layout.test.tsx`
Expected: PASS. (Si `Layout.test.tsx` ya existía con otras pruebas, agrega estos dos `it` dentro del `describe` existente en vez de crear el archivo de nuevo — revisa primero con `Read`.)

- [ ] **Step 8: Correr toda la suite de frontend**

Run: `cd frontend; npm.cmd test -- --run`
Expected: todos los tests en verde (los existentes + los nuevos de este task).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/features/bi/BiPage.tsx frontend/src/features/bi/BiPage.test.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx frontend/src/components/Layout.test.tsx
git commit -m "feat: ruta /bi, navegacion y selector de periodo del Modulo BI"
```

---

### Task 5: Tablero de rentabilidad

**Files:**
- Create: `frontend/src/features/bi/echartsSetup.ts`
- Create: `frontend/src/features/bi/TableroRentabilidad.tsx`
- Create: `frontend/src/features/bi/TableroRentabilidad.test.tsx`

**Interfaces:**
- Consumes: `apiFetch` (`src/api/client.ts`), `mensajeDe` (`src/lib/validators.ts`), `echarts` exportado desde `echartsSetup.ts`.
- Produces: `echartsSetup.ts` exporta `echarts` (instancia de `echarts/core` con `BarChart`/`LineChart`/`GaugeChart`/`GridComponent`/`TooltipComponent`/`LegendComponent`/`CanvasRenderer` ya registrados) — el Task 6 (`TableroSla`) reutiliza el mismo archivo, así que `GaugeChart` se registra aquí aunque este componente no lo use todavía. `TableroRentabilidad` exportado, recibe `{ periodo: string }`.

- [ ] **Step 1: Crear el registro compartido de ECharts**

`frontend/src/features/bi/echartsSetup.ts`:
```ts
import * as echarts from "echarts/core";
import { BarChart, GaugeChart, LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, LineChart, GaugeChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

export { echarts };
```

- [ ] **Step 2: Escribir la prueba que falla**

`frontend/src/features/bi/TableroRentabilidad.test.tsx`:
```tsx
import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { TableroRentabilidad } from "./TableroRentabilidad";
import { mockApi, renderWithProviders } from "../../test/utils";

vi.mock("echarts-for-react/lib/core", () => ({
  default: (props: { option: unknown }) => <div data-testid="chart-rentabilidad">{JSON.stringify(props.option)}</div>,
}));

const RESP = {
  periodo: "2026-09",
  contratos: [
    {
      contrato_id: 1,
      cliente_ruc: "20612493821",
      razon_social: "Clínica Test SAC",
      ingreso_soles: "2500.00",
      costo_repuestos_soles: "10.00",
      margen_soles: "2490.00",
      margen_pct: 99.6,
    },
  ],
};

describe("TableroRentabilidad", () => {
  it("muestra el spinner mientras carga", () => {
    mockApi([{ path: "/api/v1/analytics/rentabilidad?periodo=2026-09", body: RESP }]);
    renderWithProviders(<TableroRentabilidad periodo="2026-09" />);
    expect(screen.getByText(/cargando/i)).toBeInTheDocument();
  });

  it("renderiza el gráfico con los datos del contrato", async () => {
    mockApi([{ path: "/api/v1/analytics/rentabilidad?periodo=2026-09", body: RESP }]);
    renderWithProviders(<TableroRentabilidad periodo="2026-09" />);
    const chart = await screen.findByTestId("chart-rentabilidad");
    expect(chart.textContent).toContain("Clínica Test SAC");
    expect(chart.textContent).toContain("2490");
  });

  it("vacío muestra «Sin datos disponibles para el periodo»", async () => {
    mockApi([{ path: "/api/v1/analytics/rentabilidad?periodo=2026-09", body: { periodo: "2026-09", contratos: [] } }]);
    renderWithProviders(<TableroRentabilidad periodo="2026-09" />);
    expect(await screen.findByText("Sin datos disponibles para el periodo")).toBeInTheDocument();
  });

  it("error muestra el mensaje de la API", async () => {
    mockApi([{ path: "/api/v1/analytics/rentabilidad?periodo=2026-09", status: 403, body: { detail: "Permisos insuficientes" } }]);
    renderWithProviders(<TableroRentabilidad periodo="2026-09" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Permisos insuficientes");
  });
});
```

- [ ] **Step 3: Correr la prueba para verificar que falla**

Run: `cd frontend; npm.cmd test -- --run src/features/bi/TableroRentabilidad.test.tsx`
Expected: FAIL (no existe `./TableroRentabilidad`).

- [ ] **Step 4: Implementar el componente**

`frontend/src/features/bi/TableroRentabilidad.tsx`:
```tsx
import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { apiFetch } from "../../api/client";
import { mensajeDe } from "../../lib/validators";
import { echarts } from "./echartsSetup";

type ContratoRentabilidad = {
  contrato_id: number;
  cliente_ruc: string;
  razon_social: string;
  ingreso_soles: string;
  costo_repuestos_soles: string;
  margen_soles: string;
  margen_pct: number | null;
};
type RentabilidadResp = { periodo: string; contratos: ContratoRentabilidad[] };

export function TableroRentabilidad({ periodo }: { periodo: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics", "rentabilidad", periodo],
    queryFn: () => apiFetch<RentabilidadResp>(`/analytics/rentabilidad?periodo=${periodo}`),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div className="flex flex-col items-center gap-2.5">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <p className="text-xs font-semibold text-slate-400">Cargando rentabilidad…</p>
        </div>
      </div>
    );
  }

  const msg = mensajeDe(error);
  if (msg) {
    return (
      <div role="alert" className="rounded-2xl border border-red-200 bg-red-50/80 p-4 text-sm font-medium text-red-800 shadow-xs">
        {msg}
      </div>
    );
  }

  if (!data || data.contratos.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center shadow-xs">
        <p className="text-sm font-medium text-slate-500">Sin datos disponibles para el periodo</p>
      </div>
    );
  }

  const option = {
    tooltip: { trigger: "axis" },
    legend: { data: ["Ingreso", "Costo de repuestos", "Margen %"] },
    xAxis: { type: "category", data: data.contratos.map((c) => c.razon_social) },
    yAxis: [
      { type: "value", name: "S/." },
      { type: "value", name: "%", max: 100 },
    ],
    series: [
      { name: "Ingreso", type: "bar", data: data.contratos.map((c) => Number(c.ingreso_soles)) },
      { name: "Costo de repuestos", type: "bar", data: data.contratos.map((c) => Number(c.costo_repuestos_soles)) },
      { name: "Margen %", type: "line", yAxisIndex: 1, data: data.contratos.map((c) => c.margen_pct) },
    ],
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
      <h2 className="text-base font-bold text-slate-800 mb-2">Rentabilidad por contrato</h2>
      <ReactEChartsCore echarts={echarts} option={option} style={{ height: 360 }} />
    </div>
  );
}
```

- [ ] **Step 5: Correr la prueba para verificar que pasa**

Run: `cd frontend; npm.cmd test -- --run src/features/bi/TableroRentabilidad.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/bi/echartsSetup.ts frontend/src/features/bi/TableroRentabilidad.tsx frontend/src/features/bi/TableroRentabilidad.test.tsx
git commit -m "feat: tablero de rentabilidad por contrato con ECharts"
```

---

### Task 6: Tablero de SLA

**Files:**
- Create: `frontend/src/features/bi/TableroSla.tsx`
- Create: `frontend/src/features/bi/TableroSla.test.tsx`

**Interfaces:**
- Consumes: `apiFetch`, `mensajeDe`, `echarts` (de `echartsSetup.ts`, ya creado en Task 5), `DataTable` (`src/components/DataTable.tsx`, ya existe).
- Produces: `TableroSla` exportado, recibe `{ periodo: string }` — el Task 7 lo monta junto a `TableroRentabilidad` en `BiPage`.

- [ ] **Step 1: Escribir la prueba que falla**

`frontend/src/features/bi/TableroSla.test.tsx`:
```tsx
import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { TableroSla } from "./TableroSla";
import { mockApi, renderWithProviders } from "../../test/utils";

vi.mock("echarts-for-react/lib/core", () => ({
  default: (props: { option: unknown }) => <div data-testid="chart-sla">{JSON.stringify(props.option)}</div>,
}));

describe("TableroSla", () => {
  it("vacío muestra «Sin datos disponibles para el periodo»", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 0, ordenes_fuera_sla: [], pct_cumplimiento: null } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText("Sin datos disponibles para el periodo")).toBeInTheDocument();
  });

  it("100% de cumplimiento no muestra tabla de alertas, sí un mensaje positivo", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 5, ordenes_fuera_sla: [], pct_cumplimiento: 100 } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText(/ninguna orden excedió el sla/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("muestra la tabla de órdenes fuera de SLA", async () => {
    mockApi([{
      path: "/api/v1/analytics/sla?periodo=2026-09",
      body: {
        periodo: "2026-09", total_ordenes: 2, pct_cumplimiento: 50,
        ordenes_fuera_sla: [{
          orden_id: "11111111-1111-1111-1111-111111111111", equipo_serie: "RO-1",
          razon_social: "Clínica Test SAC", tiempo_respuesta_horas: "9.50", sla_horas_max_respuesta: 4,
        }],
      },
    }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText("RO-1")).toBeInTheDocument();
    expect(screen.getByText("Clínica Test SAC")).toBeInTheDocument();
  });

  it("error muestra el mensaje de la API", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", status: 403, body: { detail: "Permisos insuficientes" } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Permisos insuficientes");
  });
});
```

- [ ] **Step 2: Correr la prueba para verificar que falla**

Run: `cd frontend; npm.cmd test -- --run src/features/bi/TableroSla.test.tsx`
Expected: FAIL (no existe `./TableroSla`).

- [ ] **Step 3: Implementar el componente**

`frontend/src/features/bi/TableroSla.tsx`:
```tsx
import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { apiFetch } from "../../api/client";
import { DataTable } from "../../components/DataTable";
import { mensajeDe } from "../../lib/validators";
import { echarts } from "./echartsSetup";

type OrdenFueraSla = {
  orden_id: string;
  equipo_serie: string | null;
  razon_social: string;
  tiempo_respuesta_horas: string;
  sla_horas_max_respuesta: number;
};
type SlaResp = { periodo: string; total_ordenes: number; ordenes_fuera_sla: OrdenFueraSla[]; pct_cumplimiento: number | null };

export function TableroSla({ periodo }: { periodo: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics", "sla", periodo],
    queryFn: () => apiFetch<SlaResp>(`/analytics/sla?periodo=${periodo}`),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div className="flex flex-col items-center gap-2.5">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <p className="text-xs font-semibold text-slate-400">Cargando SLA…</p>
        </div>
      </div>
    );
  }

  const msg = mensajeDe(error);
  if (msg) {
    return (
      <div role="alert" className="rounded-2xl border border-red-200 bg-red-50/80 p-4 text-sm font-medium text-red-800 shadow-xs">
        {msg}
      </div>
    );
  }

  if (!data || data.total_ordenes === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center shadow-xs">
        <p className="text-sm font-medium text-slate-500">Sin datos disponibles para el periodo</p>
      </div>
    );
  }

  const pct = data.pct_cumplimiento ?? 0;
  const option = {
    series: [
      {
        type: "gauge",
        min: 0,
        max: 100,
        axisLine: { lineStyle: { width: 18, color: [[0.98, "#dc2626"], [1, "#16a34a"]] } },
        detail: { formatter: "{value}%", fontSize: 22 },
        data: [{ value: Math.round(pct * 100) / 100, name: "Cumplimiento SLA" }],
      },
    ],
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
      <h2 className="text-base font-bold text-slate-800 mb-2">Cumplimiento de SLA</h2>
      <ReactEChartsCore echarts={echarts} option={option} style={{ height: 280 }} />
      {data.ordenes_fuera_sla.length > 0 ? (
        <DataTable
          rows={data.ordenes_fuera_sla}
          rowKey={(o) => o.orden_id}
          columns={[
            { header: "Equipo", cell: (o) => o.equipo_serie ?? "—" },
            { header: "Cliente", cell: (o) => o.razon_social },
            { header: "Tiempo de respuesta (h)", cell: (o) => o.tiempo_respuesta_horas },
            { header: "SLA máximo (h)", cell: (o) => o.sla_horas_max_respuesta },
          ]}
        />
      ) : (
        <p className="mt-3 text-sm font-medium text-emerald-700">Ninguna orden excedió el SLA en este periodo.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Correr la prueba para verificar que pasa**

Run: `cd frontend; npm.cmd test -- --run src/features/bi/TableroSla.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/bi/TableroSla.tsx frontend/src/features/bi/TableroSla.test.tsx
git commit -m "feat: tablero de cumplimiento de SLA con ECharts"
```

---

### Task 7: Integración final de BiPage y verificación completa

**Files:**
- Modify: `frontend/src/features/bi/BiPage.tsx`
- Modify: `frontend/src/features/bi/BiPage.test.tsx`

**Interfaces:**
- Consumes: `TableroRentabilidad` (Task 5), `TableroSla` (Task 6).
- Produces: `BiPage` completo — no hay más tareas después de esta.

- [ ] **Step 1: Escribir la prueba que falla**

Agregar a `frontend/src/features/bi/BiPage.test.tsx`:
```tsx
import { mockApi } from "../../test/utils";

const RENTA_VACIA = { periodo: expect.any(String), contratos: [] };
const SLA_VACIO = { periodo: expect.any(String), total_ordenes: 0, ordenes_fuera_sla: [], pct_cumplimiento: null };

// dentro del describe("BiPage", ...) ya existente:
it("cambiar el periodo dispara nuevas consultas a ambos endpoints con el periodo correcto", async () => {
  const f = mockApi([
    { path: /\/api\/v1\/analytics\/rentabilidad/, body: { periodo: "2026-09", contratos: [] } },
    { path: /\/api\/v1\/analytics\/sla/, body: { periodo: "2026-09", total_ordenes: 0, ordenes_fuera_sla: [], pct_cumplimiento: null } },
  ]);
  renderWithProviders(<BiPage />);
  const input = screen.getByLabelText("Periodo");
  await userEvent.clear(input);
  await userEvent.type(input, "2026-03");
  await vi.waitFor(() => {
    const urls = f.mock.calls.map(([u]) => String(u));
    expect(urls.some((u) => u.includes("rentabilidad?periodo=2026-03"))).toBe(true);
    expect(urls.some((u) => u.includes("sla?periodo=2026-03"))).toBe(true);
  });
});
```
(agrega también `import userEvent from "@testing-library/user-event";` al tope del archivo si no está, y mockea `echarts-for-react/lib/core` igual que en los Tasks 5/6, con `vi.mock(...)`, antes del `describe`.)

- [ ] **Step 2: Correr la prueba para verificar que falla**

Run: `cd frontend; npm.cmd test -- --run src/features/bi/BiPage.test.tsx`
Expected: FAIL (todavía no se renderizan los tableros, así que no hay nada que dispare la segunda consulta al cambiar el periodo — de hecho puede "pasar" vacíamente; si pasa sin el cambio real, es una señal de que el test necesita el componente montado: continúa al Step 3 de todas formas y vuelve a correr después).

- [ ] **Step 3: Montar los dos tableros en `BiPage.tsx`**

```tsx
import { useState } from "react";
import { TableroRentabilidad } from "./TableroRentabilidad";
import { TableroSla } from "./TableroSla";

function periodoActual(): string {
  return new Date().toISOString().slice(0, 7);
}

export function BiPage() {
  const [periodo, setPeriodo] = useState(periodoActual());

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Business Intelligence</h1>
        <label className="text-sm font-medium text-slate-700">
          Periodo
          <input
            type="month"
            aria-label="Periodo"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="ml-2 rounded border border-slate-300 px-2 py-1"
          />
        </label>
      </div>
      <div className="grid gap-6">
        <TableroRentabilidad periodo={periodo} />
        <TableroSla periodo={periodo} />
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Correr la prueba para verificar que pasa**

Run: `cd frontend; npm.cmd test -- --run src/features/bi/BiPage.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Correr toda la suite de frontend**

Run: `cd frontend; npm.cmd test -- --run`
Expected: todos los tests en verde (existentes + los del Módulo BI).

- [ ] **Step 6: Build de producción**

Run: `cd frontend; npm.cmd run build`
Expected: compila limpio (`tsc --noEmit && vite build`), sin errores de TypeScript.

- [ ] **Step 7: Verificación manual en el navegador (dev server)**

Run: `cd frontend; npm.cmd run dev` y, con el backend corriendo localmente (`cd backend && uvicorn app.main:app --reload`) y sesión de GERENCIA, navegar a `/bi`: confirmar que el selector de mes funciona, que ambos tableros renderizan (o muestran "Sin datos disponibles para el periodo" si la base local está vacía), y que un usuario TECNICO ve "Acceso denegado" al entrar a `/bi` directamente.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/features/bi/BiPage.tsx frontend/src/features/bi/BiPage.test.tsx
git commit -m "feat: integra los tableros de rentabilidad y SLA en BiPage"
```

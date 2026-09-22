# Fase 3.2 – PWA de Campo (Offline-First): Plan de Implementación

> **Para agentes:** SUB-SKILL REQUERIDA: usar superpowers:executing-plans (nativo) o superpowers:subagent-driven-development para ejecutar tarea por tarea. Los pasos usan checkboxes (`- [ ]`).

**Goal:** Entregar `POST /api/v1/ordenes` (sincronización idempotente con hash encadenado) y la PWA `pwa/` (Dexie offline, formulario de cierre con los 8 parámetros de agua, firma DPR=2, GPS, stock móvil local, Outbox de sincronización, sesión de turno de 12h).

**Architecture:** Un endpoint nuevo en el backend existente (transacción atómica, mismo patrón `begin_nested` que ventas/liquidación) más un proyecto Vite independiente (`pwa/`) con Dexie.js como fuente de verdad offline; `ordenesLocal` filtrada por `estado_sync` es el propio Outbox.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy async (todo ya existente) · React 18, Vite, TypeScript, Tailwind, Dexie.js, `@tanstack/react-query`, `react-signature-canvas`, `vite-plugin-pwa`, `fake-indexeddb` + vitest para tests.

**Spec:** `docs/superpowers/specs/2026-09-21-fase-3-2-pwa-campo-design.md` (y `CLAUDE.md` secciones 3, 4, 5, 6, 7).

## Global Constraints

- `POST /api/v1/ordenes` es idempotente por el `id` (UUID) que genera el dispositivo: el mismo `id` dos veces responde 200/201 ambas veces sin duplicar orden, acta ni movimientos.
- La orden se inserta en su estado por defecto `SINCRONIZADA` (nunca `COMPROMETIDA` directamente); lo que RN-03 llama "pasan a Comprometido" lo captura el movimiento `SALIDA_ORDEN`, no `ordenes_servicio.estado`.
- Hash SHA-256 encadenado: `previous_hash` = hash de la última acta del **mismo** `equipo_serie` (por `creado_en` descendente); `NULL` si el equipo no tiene acta previa.
- RN-02: los 8 parámetros de agua (`tds_entrada_ppm`, `tds_post_membrana_ppm`, `tds_producto_final_ppm`, `ph` 0-14, `conductividad_us_cm`, `resistividad_mohm_cm`, `litros_consumidos_red`, `litros_agua_pura`, todos no negativos salvo `ph`≤14) + firma no vacía + GPS + `fecha_creacion_cliente` son obligatorios → 422 si falta cualquiera, sin persistir nada parcial.
- Un técnico solo sincroniza órdenes con su propio `tecnico_id`; Gerencia puede sincronizar en nombre de cualquiera (RN-01 no lo prohíbe explícitamente para órdenes, pero un técnico suplantando a otro sí es una brecha que el spec implica al hablar de autenticación por dispositivo).
- `POST /auth/login` acepta `duracion: "normal" | "turno"`; `"turno"` emite un JWT de 12 horas, sin ampliar privilegios (`rol` sigue viniendo de la BD vía `require_role`); sin `duracion`, sigue siendo 60 min.
- `pwa/` es un proyecto Vite **separado** de `frontend/`, sin paquete compartido: `api/client.ts` y `auth/session.ts` se duplican y adaptan (turno de 12h en IndexedDB, no `sessionStorage`).
- Sin shadcn/ui en `pwa/` — Tailwind puro, prioridad al peso del bundle (RNF-02: <2s en Galaxy A14).
- Stock móvil 100% local en Dexie (`stockMovilLocal`); sin contraparte en el servidor hasta que la orden se sincroniza.
- `ordenesLocal` filtrada por `estado_sync='pendiente'` **es** el Outbox — ninguna tabla de cola separada.
- El Outbox procesa las órdenes pendientes **secuencialmente** (no en paralelo), para no invertir el orden de llegada que determina el encadenado de hash.

## Review Focus

1. Dos sincronizaciones del mismo `id` en carrera (reintento de red tras un éxito que el dispositivo no llegó a ver) → 200/201 en ambas, nunca una segunda fila en `ordenes_servicio`/`actas_inmutables`/`movimientos_inventario`.
2. Dos equipos distintos sincronizando casi al mismo tiempo → el encadenado de hash de cada equipo es independiente; el `previous_hash` de uno nunca debe venir del acta de otro equipo.
3. Sincronizar consumiendo un repuesto sin stock central suficiente en ese momento (aunque el stock móvil local decía que sí alcanzaba) → la transacción entera se revierte, la orden queda visible como `error` en el Outbox, nunca se pierde ni se aplica a medias.
4. GPS denegado, no soportado, o que expira por timeout → el formulario bloquea el cierre con un mensaje claro, nunca envía `gps_latitud`/`gps_longitud` nulos o inventados.
5. Login con `duracion="turno"` y credenciales incorrectas → mismo 401 sin enumerar que el login normal; nunca emite un token de 12h con credenciales inválidas.

## Estructura de archivos

```
backend/
  app/schemas/orden.py         LecturasAgua, OrdenSincronizarIn/Out, RepuestoConsumidoIn (nuevo)
  app/services/ordenes.py      payload_raw_canonico, sincronizar_orden, excepciones de dominio (nuevo)
  app/api/v1/liquidacion.py    + POST "" (se agrega al router "/ordenes" ya existente; el archivo
                                 se mantiene pequeño, no amerita split todavía — ruling explícito)
  app/schemas/auth.py          + LoginIn.duracion
  app/api/v1/auth.py           + expires_delta segun duracion
  tests/test_ordenes_service.py   tests del servicio (sin HTTP)
  tests/test_ordenes_sync.py      tests HTTP de POST /ordenes
  tests/test_auth.py           + casos de duracion="turno"
pwa/
  package.json  vite.config.ts (vite-plugin-pwa)  tsconfig.json  index.html
  src/
    main.tsx  App.tsx
    api/client.ts               duplicado y adaptado de frontend/src/api/client.ts
    auth/session.ts              sesión de turno en IndexedDB (no sessionStorage)
    auth/LoginTurno.tsx
    db/dexie.ts                  esquema Dexie (catalogoLocal, ordenesLocal, stockMovilLocal)
    db/catalogo.ts               refresco de catalogoLocal cuando hay red
    db/stock.ts                  stock móvil local (carga y descuento)
    db/outbox.ts                 procesador de sincronización
    lib/validators.ts            duplicado + validadores de las 8 lecturas de agua
    features/orden/OrdenForm.tsx
    features/orden/Firma.tsx
    features/orden/useGps.ts
    features/stock/StockMovil.tsx
    test/setup.ts                 fake-indexeddb + testing-library
    test/utils.tsx
```

---

## Tarea 0: Scaffolding de `pwa/` y esquema Dexie

**Files:**
- Create: `pwa/package.json`, `pwa/vite.config.ts`, `pwa/tsconfig.json`, `pwa/index.html`, `pwa/src/main.tsx`, `pwa/src/App.tsx`
- Create: `pwa/src/test/setup.ts`, `pwa/src/test/utils.tsx`
- Create: `pwa/src/db/dexie.ts`
- Test: `pwa/src/db/dexie.test.ts`

**Interfaces:**
- Produces: `db: FildlabDB` (instancia Dexie) con tablas `catalogoLocal`, `ordenesLocal`, `stockMovilLocal`; tipos `CatalogoItem`, `OrdenLocal`, `EstadoSync`, `StockMovilItem`.

- [ ] **Paso 1: Escribir el test que falla**

```typescript
// pwa/src/db/dexie.test.ts
import { describe, expect, it, beforeEach } from "vitest";
import { db } from "./dexie";

describe("esquema Dexie", () => {
  beforeEach(async () => {
    await db.ordenesLocal.clear();
  });

  it("guarda y recupera una orden local con estado_sync por defecto", async () => {
    await db.ordenesLocal.add({
      id: "11111111-1111-1111-1111-111111111111",
      contrato_id: 1,
      equipo_serie: "RO-1",
      tecnico_id: 2,
      tipo_intervencion: "PREVENTIVO",
      fecha_creacion_cliente: "2026-03-01T10:00:00Z",
      lecturas_agua: {
        tds_entrada_ppm: 350, tds_post_membrana_ppm: 8, tds_producto_final_ppm: 5,
        ph: 7, conductividad_us_cm: 15, resistividad_mohm_cm: 1.2,
        litros_consumidos_red: 500, litros_agua_pura: 420,
      },
      firma_base64: "AAAA",
      gps_latitud: -8.1116,
      gps_longitud: -79.0288,
      repuestos_consumidos: [],
      estado_sync: "pendiente",
      creado_en_local: "2026-03-01T10:00:00Z",
      intentos_sync: 0,
    });
    const guardada = await db.ordenesLocal.get("11111111-1111-1111-1111-111111111111");
    expect(guardada?.estado_sync).toBe("pendiente");
  });

  it("permite consultar ordenesLocal por estado_sync (el Outbox)", async () => {
    const pendientes = await db.ordenesLocal.where("estado_sync").equals("pendiente").toArray();
    expect(Array.isArray(pendientes)).toBe(true);
  });
});
```

- [ ] **Paso 2: Correr y verificar que falla**

Run: `cd pwa && npx vitest run src/db/dexie.test.ts`
Expected: FAIL — `Cannot find module './dexie'`

- [ ] **Paso 3: Scaffolding + implementación mínima**

Crear `package.json`/`vite.config.ts`/`tsconfig.json`/`index.html` siguiendo el mismo patrón que `frontend/` (Tarea 8 del plan de 3.1), agregando `dexie`, `vite-plugin-pwa`, `fake-indexeddb` a las dependencias, y `import "fake-indexeddb/auto";` en `pwa/src/test/setup.ts` antes de cualquier otro import.

```typescript
// pwa/src/db/dexie.ts
import Dexie, { type Table } from "dexie";

export type EstadoSync = "borrador" | "pendiente" | "sincronizando" | "sincronizada" | "error";

export interface LecturasAgua {
  tds_entrada_ppm: number; tds_post_membrana_ppm: number; tds_producto_final_ppm: number;
  ph: number; conductividad_us_cm: number; resistividad_mohm_cm: number;
  litros_consumidos_red: number; litros_agua_pura: number;
}

export interface CatalogoItem {
  id: string;
  tipo: "cliente" | "equipo" | "contrato";
  datos: unknown;
  actualizado_en: string;
}

export interface RepuestoConsumido { repuesto_codigo: string; cantidad: number }

export interface OrdenLocal {
  id: string;
  contrato_id: number;
  equipo_serie: string;
  tecnico_id: number;
  tipo_intervencion: string;
  fecha_creacion_cliente: string;
  lecturas_agua: LecturasAgua;
  firma_base64: string;
  gps_latitud: number;
  gps_longitud: number;
  repuestos_consumidos: RepuestoConsumido[];
  estado_sync: EstadoSync;
  error_detalle?: string;
  creado_en_local: string;
  intentos_sync: number;
}

export interface StockMovilItem {
  repuesto_codigo: string;
  cantidad_cargada: number;
  cantidad_consumida: number;
  turno_id: string;
}

class FildlabDB extends Dexie {
  catalogoLocal!: Table<CatalogoItem, string>;
  ordenesLocal!: Table<OrdenLocal, string>;
  stockMovilLocal!: Table<StockMovilItem, string>;

  constructor() {
    super("fildlab-pwa");
    this.version(1).stores({
      catalogoLocal: "id, tipo",
      ordenesLocal: "id, estado_sync, creado_en_local",
      stockMovilLocal: "repuesto_codigo, turno_id",
    });
  }
}

export const db = new FildlabDB();
```

- [ ] **Paso 4: Correr y verificar que pasa**

Run: `cd pwa && npx vitest run src/db/dexie.test.ts`
Expected: PASS 2/2

- [ ] **Paso 5: `tsc --noEmit` limpio y commit**

```bash
cd pwa && npx tsc --noEmit
git add pwa docs/superpowers/plans/2026-09-21-fase-3-2-pwa-campo.md
git commit -m "feat(pwa): scaffolding Vite y esquema Dexie (tarea 0)"
```

## Tarea 1: Backend — `services/ordenes.py` (hash encadenado, idempotencia)

**Files:**
- Create: `backend/app/schemas/orden.py`
- Create: `backend/app/services/ordenes.py`
- Test: `backend/tests/test_ordenes_service.py`

**Interfaces:**
- Consumes: `registrar_movimiento(session, codigo, tipo, cantidad, usuario_id, orden_id=None, venta_id=None)` de `app/services/inventario.py`; modelos `OrdenServicio`, `ActaInmutable`, `Contrato`, `Equipo`, `Usuario`.
- Produces: `payload_raw_canonico(datos: OrdenSincronizarIn) -> str`; `async def sincronizar_orden(session: AsyncSession, datos: OrdenSincronizarIn, usuario: Usuario) -> OrdenServicio`; excepciones `EquipoNoEncontrado`, `ContratoNoEncontrado`, `TecnicoNoAutorizado` (heredan de una base `OrdenSyncError`).

- [ ] **Paso 1: Escribir los tests que fallan**

```python
# backend/tests/test_ordenes_service.py
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.orden import ActaInmutable, OrdenServicio
from app.models.repuesto import MovimientoInventario
from app.schemas.orden import OrdenSincronizarIn
from app.services.ordenes import (
    ContratoNoEncontrado, EquipoNoEncontrado, TecnicoNoAutorizado,
    payload_raw_canonico, sincronizar_orden,
)

LECTURAS = dict(tds_entrada_ppm=350, tds_post_membrana_ppm=8, tds_producto_final_ppm=5,
                ph=7.0, conductividad_us_cm=15, resistividad_mohm_cm=1.2,
                litros_consumidos_red=500, litros_agua_pura=420)


@pytest.fixture
async def escenario(crear_cliente, db):
    from datetime import date
    from app.models.contrato import Contrato
    from app.models.equipo import Equipo
    await crear_cliente("20612493821")
    c = Contrato(cliente_ruc="20612493821", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31), monto_mensual_soles=100)
    db.add(c)
    await db.flush()
    db.add(Equipo(serie="RO-1", cliente_ruc="20612493821", contrato_id=c.id, tipo_sistema="OSMOSIS_INVERSA",
                  fecha_instalacion=date(2026, 1, 2), parametros_nominales={"x": 1}))
    await db.flush()
    return c


def _datos(tecnico_id, **over):
    base = dict(id=uuid.uuid4(), contrato_id=1, equipo_serie="RO-1", tecnico_id=tecnico_id,
                tipo_intervencion="PREVENTIVO", fecha_creacion_cliente=datetime.now(timezone.utc),
                lecturas_agua=LECTURAS, firma_base64="AAAA", gps_latitud="-8.1116000",
                gps_longitud="-79.0288000", repuestos_consumidos=[])
    base.update(over)
    return OrdenSincronizarIn(**base)


def test_payload_canonico_es_deterministico_sin_importar_orden_de_claves():
    a = payload_raw_canonico(_datos(1))
    b = payload_raw_canonico(_datos(1))
    assert a == b


async def test_sincronizar_orden_nueva_crea_orden_y_acta(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    orden = await sincronizar_orden(db, _datos(tec.id), tec)
    assert orden.estado == "SINCRONIZADA"
    acta = (await db.execute(select(ActaInmutable).where(ActaInmutable.orden_id == orden.id))).scalar_one()
    assert acta.previous_hash is None


async def test_sincronizar_dos_veces_mismo_id_es_idempotente(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    datos = _datos(tec.id)
    o1 = await sincronizar_orden(db, datos, tec)
    o2 = await sincronizar_orden(db, datos, tec)
    assert o1.id == o2.id
    total = (await db.execute(select(func.count()).select_from(OrdenServicio))).scalar()
    assert total == 1


async def test_segunda_orden_del_mismo_equipo_encadena_hash(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    o1 = await sincronizar_orden(db, _datos(tec.id), tec)
    o2 = await sincronizar_orden(db, _datos(tec.id), tec)
    a1 = (await db.execute(select(ActaInmutable).where(ActaInmutable.orden_id == o1.id))).scalar_one()
    a2 = (await db.execute(select(ActaInmutable).where(ActaInmutable.orden_id == o2.id))).scalar_one()
    assert a2.previous_hash == a1.hash_sha256


async def test_orden_de_otro_equipo_no_hereda_previous_hash(db, escenario, crear_usuario, crear_cliente):
    from datetime import date
    from app.models.equipo import Equipo
    tec = await crear_usuario("TECNICO")
    await sincronizar_orden(db, _datos(tec.id), tec)  # acta en RO-1
    db.add(Equipo(serie="RO-2", cliente_ruc="20612493821", contrato_id=1, tipo_sistema="OSMOSIS_INVERSA",
                  fecha_instalacion=date(2026, 1, 2), parametros_nominales={"x": 1}))
    await db.flush()
    o2 = await sincronizar_orden(db, _datos(tec.id, equipo_serie="RO-2"), tec)
    a2 = (await db.execute(select(ActaInmutable).where(ActaInmutable.orden_id == o2.id))).scalar_one()
    assert a2.previous_hash is None


async def test_stock_insuficiente_revierte_orden_acta_y_movimientos(db, escenario, crear_usuario):
    from app.models.repuesto import Repuesto
    tec = await crear_usuario("TECNICO")
    db.add(Repuesto(codigo="FILT-05", descripcion="x", costo_unitario_soles=1, stock_almacen_central=0))
    await db.flush()
    with pytest.raises(Exception):
        await sincronizar_orden(db, _datos(tec.id, repuestos_consumidos=[{"repuesto_codigo": "FILT-05", "cantidad": 1}]), tec)
    assert (await db.execute(select(func.count()).select_from(OrdenServicio))).scalar() == 0
    assert (await db.execute(select(func.count()).select_from(MovimientoInventario))).scalar() == 0


async def test_equipo_inexistente_lanza_EquipoNoEncontrado(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    with pytest.raises(EquipoNoEncontrado):
        await sincronizar_orden(db, _datos(tec.id, equipo_serie="NOPE"), tec)


async def test_contrato_inexistente_lanza_ContratoNoEncontrado(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    with pytest.raises(ContratoNoEncontrado):
        await sincronizar_orden(db, _datos(tec.id, contrato_id=999999), tec)


async def test_tecnico_no_puede_sincronizar_a_nombre_de_otro(db, escenario, crear_usuario):
    tec1 = await crear_usuario("TECNICO")
    tec2 = await crear_usuario("TECNICO")
    with pytest.raises(TecnicoNoAutorizado):
        await sincronizar_orden(db, _datos(tec2.id), tec1)


async def test_gerencia_puede_sincronizar_a_nombre_de_cualquier_tecnico(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    ger = await crear_usuario("GERENCIA")
    orden = await sincronizar_orden(db, _datos(tec.id), ger)
    assert orden.tecnico_id == tec.id
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd backend && .venv\Scripts\python -m pytest -q tests/test_ordenes_service.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.ordenes'`

- [ ] **Paso 3: Implementación**

`app/schemas/orden.py`: `LecturasAgua` (8 campos, mismos tipos/límites que `ParametrosNominales` de `app/schemas/equipo.py` — se duplica el par `NoNegativo`/`Ph` en vez de importarlos de `equipo.py`, para no acoplar el dominio de "lectura de una orden" al de "ficha técnica del equipo"), `RepuestoConsumidoIn(repuesto_codigo: Codigo, cantidad: int > 0)`, `OrdenSincronizarIn(id: UUID, contrato_id: int, equipo_serie: str, tecnico_id: int, tipo_intervencion: NonBlank, fecha_creacion_cliente: datetime, lecturas_agua: LecturasAgua, firma_base64: NonBlank, gps_latitud: Decimal, gps_longitud: Decimal, repuestos_consumidos: list[RepuestoConsumidoIn])`.

`app/services/ordenes.py`: `payload_raw_canonico` serializa `lecturas_agua` con `json.dumps(..., sort_keys=True)`; `sincronizar_orden`:
1. Si `usuario.rol != "GERENCIA"` y `datos.tecnico_id != usuario.id` → `TecnicoNoAutorizado`.
2. `existente = await session.get(OrdenServicio, datos.id)`; si existe, devolverlo tal cual (idempotencia, sin re-procesar nada).
3. Validar contrato/equipo existen (404 lógico vía excepciones).
4. `async with session.begin_nested():` insertar `OrdenServicio(estado="SINCRONIZADA", ...)`, calcular hash, buscar `previous_hash` con `select(ActaInmutable.hash_sha256).join(OrdenServicio).where(OrdenServicio.equipo_serie == datos.equipo_serie).order_by(ActaInmutable.creado_en.desc()).limit(1)`, insertar `ActaInmutable`, y por cada repuesto `await registrar_movimiento(session, ..., tipo="SALIDA_ORDEN", orden_id=datos.id)`.
5. `await session.refresh(orden)`; devolver.

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd backend && .venv\Scripts\python -m pytest -q tests/test_ordenes_service.py`
Expected: PASS 11/11

- [ ] **Paso 5: Commit**

```bash
git add backend/app/schemas/orden.py backend/app/services/ordenes.py backend/tests/test_ordenes_service.py
git commit -m "feat(backend): servicio de sincronizacion de ordenes con hash encadenado e idempotencia"
```

## Tarea 2: Backend — `POST /api/v1/ordenes`

**Files:**
- Modify: `backend/app/api/v1/liquidacion.py`
- Test: `backend/tests/test_ordenes_sync.py`

**Interfaces:**
- Consumes: `sincronizar_orden` de la Tarea 1.
- Produces: `POST /api/v1/ordenes` → 201 (nueva) / 200 (ya existía) con `OrdenOut` (schema ya existente en `app/schemas/liquidacion.py`).

- [ ] **Paso 1: Escribir los tests que fallan**

```python
# backend/tests/test_ordenes_sync.py
import uuid
from datetime import datetime, timezone

LECTURAS = dict(tds_entrada_ppm=350, tds_post_membrana_ppm=8, tds_producto_final_ppm=5,
                ph=7.0, conductividad_us_cm=15, resistividad_mohm_cm=1.2,
                litros_consumidos_red=500, litros_agua_pura=420)


async def _preparar(crear_cliente, db, tecnico_id):
    from datetime import date
    from app.models.contrato import Contrato
    from app.models.equipo import Equipo
    await crear_cliente("20612493821")
    c = Contrato(cliente_ruc="20612493821", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31), monto_mensual_soles=100)
    db.add(c)
    await db.flush()
    db.add(Equipo(serie="RO-1", cliente_ruc="20612493821", contrato_id=c.id, tipo_sistema="OSMOSIS_INVERSA",
                  fecha_instalacion=date(2026, 1, 2), parametros_nominales={"x": 1}))
    await db.flush()
    return c.id


def _body(tecnico_id, contrato_id, **over):
    base = {"id": str(uuid.uuid4()), "contrato_id": contrato_id, "equipo_serie": "RO-1", "tecnico_id": tecnico_id,
            "tipo_intervencion": "PREVENTIVO", "fecha_creacion_cliente": datetime.now(timezone.utc).isoformat(),
            "lecturas_agua": LECTURAS, "firma_base64": "AAAA", "gps_latitud": "-8.1116000",
            "gps_longitud": "-79.0288000", "repuestos_consumidos": []}
    base.update(over)
    return base


async def test_post_ordenes_crea_y_devuelve_201(client, crear_usuario, auth_headers, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db, tec.id)
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid), headers=auth_headers(tec))
    assert r.status_code == 201 and r.json()["estado"] == "SINCRONIZADA"


async def test_post_ordenes_mismo_id_dos_veces_200_sin_duplicar(client, crear_usuario, auth_headers, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db, tec.id)
    body = _body(tec.id, cid)
    r1 = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    r2 = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    assert r1.status_code == 201 and r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


import pytest


@pytest.mark.parametrize("campo", list(LECTURAS.keys()))
async def test_post_ordenes_lectura_faltante_422(client, crear_usuario, auth_headers, crear_cliente, db, campo):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db, tec.id)
    lecturas = {k: v for k, v in LECTURAS.items() if k != campo}
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid, lecturas_agua=lecturas), headers=auth_headers(tec))
    assert r.status_code == 422


async def test_post_ordenes_firma_vacia_422(client, crear_usuario, auth_headers, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db, tec.id)
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid, firma_base64=""), headers=auth_headers(tec))
    assert r.status_code == 422


async def test_post_ordenes_gps_invalido_422(client, crear_usuario, auth_headers, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db, tec.id)
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid, gps_latitud="no-es-numero"), headers=auth_headers(tec))
    assert r.status_code == 422


async def test_post_ordenes_stock_insuficiente_409(client, crear_usuario, auth_headers, crear_cliente, db):
    from app.models.repuesto import Repuesto
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db, tec.id)
    db.add(Repuesto(codigo="FILT-05", descripcion="x", costo_unitario_soles=1, stock_almacen_central=0))
    await db.flush()
    body = _body(tec.id, cid, repuestos_consumidos=[{"repuesto_codigo": "FILT-05", "cantidad": 1}])
    r = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    assert r.status_code == 409


async def test_post_ordenes_sin_token_401(client, crear_usuario, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db, tec.id)
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid))
    assert r.status_code == 401


async def test_post_ordenes_tecnico_de_otro_403(client, crear_usuario, auth_headers, crear_cliente, db):
    tec1 = await crear_usuario("TECNICO")
    tec2 = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db, tec1.id)
    r = await client.post("/api/v1/ordenes", json=_body(tec2.id, cid), headers=auth_headers(tec1))
    assert r.status_code == 403
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd backend && .venv\Scripts\python -m pytest -q tests/test_ordenes_sync.py`
Expected: FAIL — 405/404 (la ruta `POST /ordenes` no existe todavía)

- [ ] **Paso 3: Implementación**

En `liquidacion.py`, agregar:

```python
@router.post("", response_model=OrdenOut, status_code=status.HTTP_201_CREATED)
async def sincronizar(datos: OrdenSincronizarIn, session: AsyncSession = Depends(get_session),
                       usuario: Usuario = Depends(get_current_user), response: Response = None):
    try:
        existente = await session.get(OrdenServicio, datos.id)
        orden = await ordenes_svc.sincronizar_orden(session, datos, usuario)
        if existente is not None:
            response.status_code = status.HTTP_200_OK
        return orden
    except ordenes_svc.TecnicoNoAutorizado:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes sincronizar ordenes de otro tecnico") from None
    except ordenes_svc.EquipoNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado") from None
    except ordenes_svc.ContratoNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrato no encontrado") from None
    except inv.StockInsuficiente as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None
    except inv.RepuestoNoEncontrado as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Repuesto no encontrado: {e}") from None
```

(Nota: capturar `existente` antes de llamar al servicio, porque `sincronizar_orden` no distingue crear de reencontrar en su valor de retorno — la distinción 200 vs 201 vive en el router, no en el servicio.)

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd backend && .venv\Scripts\python -m pytest -q tests/test_ordenes_sync.py`
Expected: PASS 9/9 (incluye 8 parametrizados de `test_post_ordenes_lectura_faltante_422`)

- [ ] **Paso 5: Suite completa y commit**

```bash
cd backend && .venv\Scripts\python -m pytest -q
git add backend/app/api/v1/liquidacion.py backend/tests/test_ordenes_sync.py
git commit -m "feat(backend): POST /api/v1/ordenes idempotente con validacion RN-02"
```

## Tarea 3: Backend — sesión de turno (JWT de 12 horas)

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/v1/auth.py`
- Test: `backend/tests/test_auth.py` (agregar casos)

**Interfaces:**
- Produces: `LoginIn.duracion: Literal["normal", "turno"] = "normal"`; `POST /auth/login` con `duracion="turno"` → token con `exp` a 12h.

- [ ] **Paso 1: Escribir los tests que fallan**

```python
# agregar a backend/tests/test_auth.py
import jwt as pyjwt
from datetime import datetime, timezone

from app.core.config import get_settings


def _exp_horas(token: str) -> float:
    payload = pyjwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    return (datetime.fromtimestamp(payload["exp"], tz=timezone.utc) - datetime.now(timezone.utc)).total_seconds() / 3600


async def test_login_duracion_turno_emite_token_de_12_horas(client, crear_usuario):
    await crear_usuario("TECNICO", email="t@x.pe", password="pw-correcta")
    r = await client.post("/api/v1/auth/login", json={"email": "t@x.pe", "password": "pw-correcta", "duracion": "turno"})
    assert 11.9 < _exp_horas(r.json()["access_token"]) <= 12.0


async def test_login_sin_duracion_sigue_siendo_60_min(client, crear_usuario):
    await crear_usuario("TECNICO", email="t2@x.pe", password="pw-correcta")
    r = await client.post("/api/v1/auth/login", json={"email": "t2@x.pe", "password": "pw-correcta"})
    assert 0.9 < _exp_horas(r.json()["access_token"]) <= 1.0


async def test_login_duracion_turno_password_incorrecto_401_sin_emitir_token(client, crear_usuario):
    await crear_usuario("TECNICO", email="t3@x.pe", password="pw-correcta")
    r = await client.post("/api/v1/auth/login", json={"email": "t3@x.pe", "password": "mala", "duracion": "turno"})
    assert r.status_code == 401 and "access_token" not in r.json()
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd backend && .venv\Scripts\python -m pytest -q tests/test_auth.py -k duracion`
Expected: FAIL — `duracion` no es un campo aceptado, o el token sigue en 60 min

- [ ] **Paso 3: Implementación**

`schemas/auth.py`: `LoginIn.duracion: Literal["normal", "turno"] = "normal"`.
`api/v1/auth.py`: en `login()`, `expires = timedelta(hours=12) if datos.duracion == "turno" else None`; pasar `expires_delta=expires` a `create_access_token` (ya acepta ese parámetro desde 3.1).

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd backend && .venv\Scripts\python -m pytest -q`
Expected: PASS (suite completa, sin regresiones)

- [ ] **Paso 5: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/v1/auth.py backend/tests/test_auth.py
git commit -m "feat(backend): login con duracion=turno emite JWT de 12 horas"
```

## Tarea 4: PWA — catálogo local (clientes/equipos/contratos offline)

**Files:**
- Create: `pwa/src/api/client.ts` (duplicado y adaptado de `frontend/src/api/client.ts`)
- Create: `pwa/src/db/catalogo.ts`
- Test: `pwa/src/db/catalogo.test.ts`

**Interfaces:**
- Consumes: `db` (Tarea 0), `apiFetch` (nuevo, mismo contrato que en `frontend/`).
- Produces: `async function refrescarCatalogo(): Promise<void>`; `async function buscarEquipos(query: string): Promise<CatalogoItem[]>`.

- [ ] **Paso 1: Escribir los tests que fallan**

```typescript
// pwa/src/db/catalogo.test.ts
import { describe, expect, it, vi, beforeEach } from "vitest";
import { db } from "./dexie";
import { refrescarCatalogo, buscarEquipos } from "./catalogo";

function mockApi(clientes: unknown[], equipos: unknown[], contratos: unknown[]) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    const body = url.includes("/clientes") ? clientes : url.includes("/equipos") ? equipos : contratos;
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
}

describe("catalogo local", () => {
  beforeEach(async () => { await db.catalogoLocal.clear(); });

  it("refrescar puebla clientes, equipos y contratos", async () => {
    mockApi([{ ruc: "20612493821" }], [{ serie: "RO-1" }], [{ id: 1 }]);
    await refrescarCatalogo();
    expect((await db.catalogoLocal.where("tipo").equals("equipo").toArray())[0].datos).toEqual({ serie: "RO-1" });
  });

  it("buscarEquipos funciona sin red, leyendo de Dexie", async () => {
    await db.catalogoLocal.add({ id: "RO-1", tipo: "equipo", datos: { serie: "RO-1" }, actualizado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("sin red"));
    const r = await buscarEquipos("RO");
    expect(r).toHaveLength(1);
  });

  it("si falla la red, refrescarCatalogo no borra lo que ya habia", async () => {
    await db.catalogoLocal.add({ id: "RO-1", tipo: "equipo", datos: { serie: "RO-1" }, actualizado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("sin red"));
    await refrescarCatalogo();
    expect(await db.catalogoLocal.get("RO-1")).toBeDefined();
  });
});
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd pwa && npx vitest run src/db/catalogo.test.ts`
Expected: FAIL — módulos no existen

- [ ] **Paso 3: Implementación**

`api/client.ts`: copia de `frontend/src/api/client.ts` con el mismo contrato (`ApiError`, `apiFetch`), leyendo el token desde `auth/session.ts` de la PWA (Tarea 5) en vez de `sessionStorage` directamente.

`db/catalogo.ts`: `refrescarCatalogo` hace `Promise.allSettled([apiFetch("/clientes"), apiFetch("/equipos"), apiFetch("/contratos")])`, escribe cada resultado exitoso en `catalogoLocal` vía `bulkPut`; los que fallan (sin red) se ignoran silenciosamente y dejan el catálogo previo intacto. `buscarEquipos` lee `db.catalogoLocal.where("tipo").equals("equipo")` y filtra en memoria por `query`.

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd pwa && npx vitest run src/db/catalogo.test.ts`
Expected: PASS 3/3

- [ ] **Paso 5: Commit**

```bash
git add pwa/src/api/client.ts pwa/src/db/catalogo.ts pwa/src/db/catalogo.test.ts
git commit -m "feat(pwa): catalogo local offline (clientes/equipos/contratos)"
```

## Tarea 5: PWA — sesión de turno (12h en IndexedDB)

**Files:**
- Create: `pwa/src/auth/session.ts`
- Create: `pwa/src/auth/LoginTurno.tsx`
- Test: `pwa/src/auth/session.test.ts`, `pwa/src/auth/LoginTurno.test.tsx`

**Interfaces:**
- Produces: `async function guardarSesionTurno(token: string): Promise<void>`; `async function obtenerToken(): Promise<string | null>`; `async function cerrarSesion(): Promise<void>`; componente `<LoginTurno />`.

- [ ] **Paso 1: Escribir los tests que fallan**

```typescript
// pwa/src/auth/session.test.ts
import { describe, expect, it, beforeEach } from "vitest";
import { db } from "../db/dexie";
import { guardarSesionTurno, obtenerToken, cerrarSesion } from "./session";

describe("sesion de turno", () => {
  it("guarda el token en IndexedDB, no en sessionStorage", async () => {
    await guardarSesionTurno("tok-123");
    expect(sessionStorage.getItem("fildlab.token")).toBeNull();
    expect(await obtenerToken()).toBe("tok-123");
  });

  it("cerrarSesion borra el token guardado", async () => {
    await guardarSesionTurno("tok-456");
    await cerrarSesion();
    expect(await obtenerToken()).toBeNull();
  });
});
```

```typescript
// pwa/src/auth/LoginTurno.test.tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginTurno } from "./LoginTurno";
import { obtenerToken } from "./session";

describe("LoginTurno", () => {
  it("envia duracion=turno y guarda el token recibido", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ access_token: "tok-789", token_type: "bearer" }), { status: 200 }),
    );
    render(<LoginTurno />);
    await userEvent.type(screen.getByLabelText(/correo/i), "t@x.pe");
    await userEvent.type(screen.getByLabelText(/contraseña/i), "clave");
    await userEvent.click(screen.getByRole("button", { name: /ingresar/i }));
    expect(await obtenerToken()).toBe("tok-789");
  });

  it("credenciales invalidas muestran error y no guardan token", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Credenciales inválidas" }), { status: 401 }),
    );
    render(<LoginTurno />);
    await userEvent.type(screen.getByLabelText(/correo/i), "t@x.pe");
    await userEvent.type(screen.getByLabelText(/contraseña/i), "mala");
    await userEvent.click(screen.getByRole("button", { name: /ingresar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Credenciales inválidas");
    expect(await obtenerToken()).toBeNull();
  });
});
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd pwa && npx vitest run src/auth`
Expected: FAIL — módulos no existen

- [ ] **Paso 3: Implementación**

`auth/session.ts`: tabla nueva `sesion` en `db/dexie.ts` (`{ id: 'actual', token: string, guardado_en: string }`, versión 2 del esquema Dexie) o, más simple, una fila fija en `stockMovilLocal`... **no** — crear tabla dedicada `sesion` es más claro. Actualizar `dexie.ts` (`this.version(1).stores({..., sesion: "id"})`, con `sesion` en el mismo `version(1)` ya que todavía no se ha publicado ninguna versión anterior).

`auth/LoginTurno.tsx`: formulario igual al `LoginPage` de `frontend/`, pero llama `apiFetch("/auth/login", {method:"POST", body:{email,password,duracion:"turno"}})` y `guardarSesionTurno(access_token)`.

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd pwa && npx vitest run src/auth`
Expected: PASS

- [ ] **Paso 5: Commit**

```bash
git add pwa/src/auth pwa/src/db/dexie.ts
git commit -m "feat(pwa): sesion de turno de 12h persistida en IndexedDB"
```

## Tarea 6: PWA — stock móvil local

**Files:**
- Create: `pwa/src/db/stock.ts`
- Create: `pwa/src/features/stock/StockMovil.tsx`
- Test: `pwa/src/db/stock.test.ts`, `pwa/src/features/stock/StockMovil.test.tsx`

**Interfaces:**
- Produces: `async function cargarStockTurno(items: {repuesto_codigo: string; cantidad: number}[], turnoId: string): Promise<void>`; `async function consumir(codigo: string, cantidad: number): Promise<{ok: true} | {ok: false; motivo: string}>`.

- [ ] **Paso 1: Escribir los tests que fallan**

```typescript
// pwa/src/db/stock.test.ts
import { describe, expect, it, beforeEach } from "vitest";
import { db } from "./dexie";
import { cargarStockTurno, consumir } from "./stock";

describe("stock movil local", () => {
  beforeEach(async () => { await db.stockMovilLocal.clear(); });

  it("carga el stock de turno", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno-1");
    const item = await db.stockMovilLocal.get("FILT-05");
    expect(item?.cantidad_cargada).toBe(10);
  });

  it("consumir dentro del limite incrementa cantidad_consumida", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno-1");
    const r = await consumir("FILT-05", 3);
    expect(r.ok).toBe(true);
    expect((await db.stockMovilLocal.get("FILT-05"))?.cantidad_consumida).toBe(3);
  });

  it("consumir mas de lo cargado se bloquea y no cambia el registro", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 2 }], "turno-1");
    const r = await consumir("FILT-05", 5);
    expect(r.ok).toBe(false);
    expect((await db.stockMovilLocal.get("FILT-05"))?.cantidad_consumida).toBe(0);
  });
});
```

```typescript
// pwa/src/features/stock/StockMovil.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StockMovil } from "./StockMovil";
import { db } from "../../db/dexie";

describe("StockMovil", () => {
  it("registra la carga de turno y la refleja en Dexie", async () => {
    render(<StockMovil />);
    await userEvent.type(screen.getByLabelText(/código de repuesto/i), "FILT-05");
    await userEvent.type(screen.getByLabelText(/cantidad cargada/i), "10");
    await userEvent.click(screen.getByRole("button", { name: /cargar/i }));
    expect((await db.stockMovilLocal.get("FILT-05"))?.cantidad_cargada).toBe(10);
  });
});
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd pwa && npx vitest run src/db/stock.test.ts`
Expected: FAIL — módulo no existe

- [ ] **Paso 3: Implementación**

`db/stock.ts`: operaciones directas sobre `db.stockMovilLocal`; `consumir` lee el registro, calcula `cantidad_consumida + cantidad > cantidad_cargada` → `{ok:false, motivo:"Stock móvil insuficiente"}` sin escribir; si alcanza, `put` con el nuevo total.

`features/stock/StockMovil.tsx`: formulario con dos campos (`FormField` "Código de repuesto", "Cantidad cargada") y un botón "Cargar" que llama `cargarStockTurno([{repuesto_codigo, cantidad}], turnoId)` con un `turnoId` generado una vez por sesión (p. ej. `crypto.randomUUID()` guardado en la tabla `sesion` de la Tarea 5).

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd pwa && npx vitest run src/db/stock.test.ts`
Expected: PASS 3/3

- [ ] **Paso 5: Commit**

```bash
git add pwa/src/db/stock.ts pwa/src/db/stock.test.ts pwa/src/features/stock
git commit -m "feat(pwa): stock movil local con bloqueo por exceso de consumo"
```

## Tarea 7: PWA — formulario de orden (lecturas de agua)

**Files:**
- Create: `pwa/src/lib/validators.ts` (duplicado de `frontend/src/lib/validators.ts` + validadores de `LecturasAgua`)
- Create: `pwa/src/features/orden/OrdenForm.tsx`
- Test: `pwa/src/features/orden/OrdenForm.test.tsx`

**Interfaces:**
- Consumes: `buscarEquipos` (Tarea 4), `consumir` (Tarea 6).
- Produces: `<OrdenForm />`, validadores `errorLectura(campo, valor): string | null` para los 8 campos (no-negativo salvo `ph` en 0-14).

- [ ] **Paso 1: Escribir los tests que fallan**

```typescript
// pwa/src/features/orden/OrdenForm.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrdenForm } from "./OrdenForm";

describe("OrdenForm — lecturas de agua", () => {
  it("rechaza ph fuera de 0-14", async () => {
    render(<OrdenForm />);
    const ph = screen.getByLabelText(/ph/i);
    await userEvent.type(ph, "15");
    await userEvent.tab();
    expect(await screen.findByText(/entre 0 y 14/i)).toBeInTheDocument();
  });

  it("rechaza un valor negativo en TDS entrada", async () => {
    render(<OrdenForm />);
    const campo = screen.getByLabelText(/tds.*entrada/i);
    await userEvent.type(campo, "-1");
    await userEvent.tab();
    expect(await screen.findByText(/no puede ser negativo/i)).toBeInTheDocument();
  });

  it("el boton de siguiente/guardar sigue deshabilitado con lecturas incompletas", async () => {
    render(<OrdenForm />);
    expect(screen.getByRole("button", { name: /continuar/i })).toBeDisabled();
  });
});
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd pwa && npx vitest run src/features/orden/OrdenForm.test.tsx`
Expected: FAIL — módulo no existe

- [ ] **Paso 3: Implementación**

Formulario con los 8 campos + selector de equipo (`buscarEquipos`) + selector de repuestos consumidos contra `consumir()` del stock móvil. Estado local de lecturas + validación por campo con `errorLectura`. El botón "Continuar" (hacia firma/GPS, Tarea 8) queda deshabilitado hasta que las 8 lecturas sean válidas.

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd pwa && npx vitest run src/features/orden/OrdenForm.test.tsx`
Expected: PASS 3/3

- [ ] **Paso 5: Commit**

```bash
git add pwa/src/lib/validators.ts pwa/src/features/orden/OrdenForm.tsx pwa/src/features/orden/OrdenForm.test.tsx
git commit -m "feat(pwa): formulario de lecturas de agua con validacion RN-02"
```

## Tarea 8: PWA — firma (DPR=2), GPS y bloqueo de cierre

**Files:**
- Create: `pwa/src/features/orden/Firma.tsx`
- Create: `pwa/src/features/orden/useGps.ts`
- Modify: `pwa/src/features/orden/OrdenForm.tsx` (integra firma + GPS + botón "Cerrar orden")
- Test: `pwa/src/features/orden/Firma.test.tsx`, `pwa/src/features/orden/useGps.test.ts`, actualizar `OrdenForm.test.tsx`

**Interfaces:**
- Produces: `<Firma onCambio={(base64: string | null) => void} />` (usa `react-signature-canvas` con `minWidth`/`maxWidth` fijos para DPR=2); `useGps(): {lat: number|null; lng: number|null; error: string|null; solicitar: () => void}`.

- [ ] **Paso 1: Escribir los tests que fallan**

```typescript
// pwa/src/features/orden/useGps.test.ts
import { describe, expect, it, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useGps } from "./useGps";

describe("useGps", () => {
  it("permiso denegado deja un mensaje claro, no crashea", async () => {
    const getCurrentPosition = vi.fn((_ok, err) => err({ code: 1, message: "denegado" }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    const { result } = renderHook(() => useGps());
    act(() => result.current.solicitar());
    await waitFor(() => expect(result.current.error).toMatch(/permiso/i));
    expect(result.current.lat).toBeNull();
  });

  it("exito guarda lat/lng", async () => {
    const getCurrentPosition = vi.fn((ok) => ok({ coords: { latitude: -8.11, longitude: -79.02 } }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    const { result } = renderHook(() => useGps());
    act(() => result.current.solicitar());
    await waitFor(() => expect(result.current.lat).toBe(-8.11));
  });

  it("sin soporte de geolocalizacion en el navegador, error claro", async () => {
    vi.stubGlobal("navigator", {});
    const { result } = renderHook(() => useGps());
    act(() => result.current.solicitar());
    await waitFor(() => expect(result.current.error).toMatch(/no disponible/i));
  });
});
```

```typescript
// agregar a OrdenForm.test.tsx
it("cerrar orden sigue deshabilitado sin firma ni GPS aun con lecturas completas", async () => {
  render(<OrdenForm />);
  await completarLecturasValidas();  // helper que llena los 8 campos con valores validos
  expect(screen.getByRole("button", { name: /cerrar orden/i })).toBeDisabled();
});

it("se habilita solo cuando lecturas + firma + gps estan completos", async () => {
  render(<OrdenForm />);
  await completarLecturasValidas();
  await firmarEnCanvas();
  await concederGpsMock();
  expect(screen.getByRole("button", { name: /cerrar orden/i })).toBeEnabled();
});
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd pwa && npx vitest run src/features/orden`
Expected: FAIL — `useGps`/`Firma` no existen

- [ ] **Paso 3: Implementación**

`useGps`: envuelve `navigator.geolocation.getCurrentPosition`, mapea `code===1` (denegado) a un mensaje "Se necesita permiso de ubicación para cerrar la orden", cualquier otro código a un mensaje genérico, y la ausencia de `navigator.geolocation` a "Geolocalización no disponible en este dispositivo".

`Firma`: wrapper de `react-signature-canvas` con `penColor="black"` y trazo fijo (no depende de `window.devicePixelRatio` del dispositivo, para que el payload de firma pese igual en cualquier Galaxy A14); `onEnd` llama `onCambio(ref.current.toDataURL())`, `onCambio(null)` si se limpia.

`OrdenForm`: agrega los tres bloques; "Cerrar orden" solo se habilita con lecturas válidas + firma no nula + GPS presente; al hacer clic escribe en `ordenesLocal` con `estado_sync: "pendiente"`.

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd pwa && npx vitest run src/features/orden`
Expected: PASS

- [ ] **Paso 5: Commit**

```bash
git add pwa/src/features/orden
git commit -m "feat(pwa): firma DPR=2, GPS y bloqueo de cierre (RN-02)"
```

## Tarea 9: PWA — Outbox de sincronización

**Files:**
- Create: `pwa/src/db/outbox.ts`
- Test: `pwa/src/db/outbox.test.ts`

**Interfaces:**
- Consumes: `apiFetch` (Tarea 4), `db.ordenesLocal`.
- Produces: `async function procesarOutbox(): Promise<void>`; se invoca desde un listener `window.addEventListener("online", procesarOutbox)` registrado en `main.tsx`.

- [ ] **Paso 1: Escribir los tests que fallan**

```typescript
// pwa/src/db/outbox.test.ts
import { describe, expect, it, vi, beforeEach } from "vitest";
import { db } from "./dexie";
import { procesarOutbox } from "./outbox";

const ORDEN_BASE = {
  contrato_id: 1, equipo_serie: "RO-1", tecnico_id: 1, tipo_intervencion: "PREVENTIVO",
  fecha_creacion_cliente: "2026-03-01T10:00:00Z",
  lecturas_agua: { tds_entrada_ppm: 1, tds_post_membrana_ppm: 1, tds_producto_final_ppm: 1, ph: 7,
                   conductividad_us_cm: 1, resistividad_mohm_cm: 1, litros_consumidos_red: 1, litros_agua_pura: 1 },
  firma_base64: "AAAA", gps_latitud: -8, gps_longitud: -79, repuestos_consumidos: [],
  creado_en_local: "2026-03-01T10:00:00Z", intentos_sync: 0,
};

async function agregarPendiente(id: string) {
  await db.ordenesLocal.add({ ...ORDEN_BASE, id, estado_sync: "pendiente" });
}

describe("procesarOutbox", () => {
  beforeEach(async () => { await db.ordenesLocal.clear(); });

  it("marca sincronizada en exito", async () => {
    await agregarPendiente("11111111-1111-1111-1111-111111111111");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "1" }), { status: 201 }));
    await procesarOutbox();
    expect((await db.ordenesLocal.get("11111111-1111-1111-1111-111111111111"))?.estado_sync).toBe("sincronizada");
  });

  it("marca error en fallo de negocio (409) y no reintenta sola", async () => {
    await agregarPendiente("22222222-2222-2222-2222-222222222222");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "stock insuficiente" }), { status: 409 }),
    );
    await procesarOutbox();
    const o = await db.ordenesLocal.get("22222222-2222-2222-2222-222222222222");
    expect(o?.estado_sync).toBe("error");
    expect(o?.error_detalle).toContain("stock insuficiente");
  });

  it("deja pendiente en fallo de red (se reintenta despues)", async () => {
    await agregarPendiente("33333333-3333-3333-3333-333333333333");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("sin red"));
    await procesarOutbox();
    expect((await db.ordenesLocal.get("33333333-3333-3333-3333-333333333333"))?.estado_sync).toBe("pendiente");
  });

  it("procesa en orden por creado_en_local, no en paralelo", async () => {
    await db.ordenesLocal.bulkAdd([
      { ...ORDEN_BASE, id: "a", creado_en_local: "2026-03-01T10:02:00Z", estado_sync: "pendiente" },
      { ...ORDEN_BASE, id: "b", creado_en_local: "2026-03-01T10:01:00Z", estado_sync: "pendiente" },
    ]);
    const orden: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_url, init) => {
      orden.push(JSON.parse((init as RequestInit).body as string).id);
      return new Response(JSON.stringify({ id: "x" }), { status: 201 });
    });
    await procesarOutbox();
    expect(orden).toEqual(["b", "a"]);  // b es mas antigua, va primero
  });
});
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd pwa && npx vitest run src/db/outbox.test.ts`
Expected: FAIL — módulo no existe

- [ ] **Paso 3: Implementación**

```typescript
// pwa/src/db/outbox.ts
import { ApiError, apiFetch } from "../api/client";
import { db, type OrdenLocal } from "./dexie";

export async function procesarOutbox(): Promise<void> {
  const pendientes = await db.ordenesLocal.where("estado_sync").equals("pendiente").sortBy("creado_en_local");
  for (const orden of pendientes) {
    await sincronizarUna(orden);  // secuencial: nunca Promise.all
  }
}

function aPayloadDeSincronizacion(orden: OrdenLocal) {
  // Solo los campos que OrdenSincronizarIn espera en el backend — nunca los campos
  // de bookkeeping local (estado_sync, error_detalle, creado_en_local, intentos_sync).
  const { estado_sync: _es, error_detalle: _ed, creado_en_local: _cl, intentos_sync: _is, ...payload } = orden;
  return payload;
}

async function sincronizarUna(orden: OrdenLocal): Promise<void> {
  await db.ordenesLocal.update(orden.id, { estado_sync: "sincronizando" });
  try {
    await apiFetch("/ordenes", { method: "POST", body: aPayloadDeSincronizacion(orden) });
    await db.ordenesLocal.update(orden.id, { estado_sync: "sincronizada" });
  } catch (e) {
    if (e instanceof ApiError && e.status !== 0) {
      // Error de negocio (4xx del backend): no se pierde, pero tampoco se reintenta sola.
      await db.ordenesLocal.update(orden.id, { estado_sync: "error", error_detalle: e.message });
    } else {
      // Error de red (status 0): vuelve a pendiente para el proximo ciclo.
      await db.ordenesLocal.update(orden.id, { estado_sync: "pendiente", intentos_sync: orden.intentos_sync + 1 });
    }
  }
}
```

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd pwa && npx vitest run src/db/outbox.test.ts`
Expected: PASS 4/4

- [ ] **Paso 5: Commit**

```bash
git add pwa/src/db/outbox.ts pwa/src/db/outbox.test.ts
git commit -m "feat(pwa): outbox de sincronizacion secuencial con manejo de error de red vs negocio"
```

## Tarea 10: Integración — `main.tsx`, manifest, build real

**Files:**
- Modify: `pwa/src/main.tsx` (registra el listener `online`, monta `<App />` con las rutas: login de turno, formulario de orden, stock)
- Modify: `pwa/vite.config.ts` (confirma la config de `vite-plugin-pwa`: `registerType: "autoUpdate"`, `manifest` con nombre/iconos/colores)
- Create: `pwa/src/App.tsx` (rutas reales, reemplaza el placeholder de la Tarea 0)
- Test: `pwa/src/App.test.tsx` (smoke: login → formulario)

- [ ] **Paso 1: Escribir el test que falla**

```typescript
// pwa/src/App.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App (PWA)", () => {
  it("sin sesion muestra el login de turno", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /ingreso/i })).toBeInTheDocument();
  });
});
```

- [ ] **Paso 2: Correr y verificar que falla**

Run: `cd pwa && npx vitest run src/App.test.tsx`
Expected: FAIL (o pasa trivialmente si el placeholder ya tenía ese texto — en ese caso, este paso confirma que el placeholder se reemplaza y el test se re-verifica contra la app real)

- [ ] **Paso 3: Implementación**

Cablear `App.tsx` con las pantallas ya construidas (Tareas 5-9) y `main.tsx` con `window.addEventListener("online", procesarOutbox)` más un intervalo de respaldo cada 30s (Android no siempre dispara `online` de forma confiable).

- [ ] **Paso 4: Correr y verificar que pasa**

Run: `cd pwa && npx vitest run`
Expected: PASS (suite completa de `pwa/`)

- [ ] **Paso 5: Build real y commit**

```bash
cd pwa && npx tsc --noEmit && npx vite build
git add pwa
git commit -m "feat(pwa): integracion final, listener de sincronizacion y build de produccion"
```

## Tarea 11: Cierre de fase

- [ ] `pytest` (backend) y `vitest run` (pwa y frontend) completos en verde, sin warnings.
- [ ] `tsc --noEmit` y `vite build` limpios en `pwa/` y `frontend/`.
- [ ] Marcar 3.2.1–3.2.5 y 3.2 en la sección 7 de `CLAUDE.md`.
- [ ] Revisión final de toda la rama con `requesting-code-review` (modelo más capaz), Review Focus de este plan incluido explícitamente.
- [ ] Pase de arreglos sobre Critical/Important, con TDD, igual que el cierre de la Fase 3.1.

## Nota de alcance del plan

Igual que en el plan de 3.1: el código de cada test se termina de precisar en el paso RED de su tarea; lo escrito arriba ya es código real y ejecutable, no pseudocódigo, salvo los tests de UI marcados con helpers (`completarLecturasValidas`, `firmarEnCanvas`, `concederGpsMock`) cuyo cuerpo exacto se escribe junto con el test en la Tarea 8, una vez que `OrdenForm` tiene sus `label`s definitivos.

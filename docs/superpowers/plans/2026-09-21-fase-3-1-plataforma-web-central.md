# Fase 3.1 – Plataforma Web Central: Plan de Implementación

> **Para agentes:** SUB-SKILL REQUERIDA: usar superpowers:executing-plans (nativo) o superpowers:subagent-driven-development para ejecutar tarea por tarea. Los pasos usan checkboxes (`- [ ]`).

**Goal:** Entregar el backend FastAPI + Neon y el frontend administrativo React para clientes, contratos/SLA, inventario, ventas, equipos, liquidación/adendas y RBAC (Argon2 + JWT), todo con TDD.

**Architecture:** Monolito asíncrono FastAPI (SQLAlchemy 2.0 async + asyncpg) con un router por módulo y capa `services` con la lógica. Frontend SPA React 18 + Vite + TS + Tailwind, con `RequireRole` sobre las rutas y un cliente HTTP único que inyecta el JWT.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg, Alembic, argon2-cffi, PyJWT, pytest + pytest-asyncio + httpx · React 18, Vite, TypeScript, Tailwind, React Router, TanStack Query, vitest + Testing Library + MSW.

**Spec:** `CLAUDE.md` (secciones 3, 4, 5, 6 y 7).

## Global Constraints

- Presupuesto de licencias S/. 0.00: solo open source / free tier.
- Backend: FastAPI asíncrono, Pydantic v2, contenedor objetivo Koyeb 512 MB RAM / 0.1 vCPU → pool conservador (`pool_size=2`, `max_overflow=1`, `pool_pre_ping=True`, `pool_recycle=300`).
- `GET /api/v1/healthz` liviano: sin autenticación y sin consulta a BD.
- Contraseñas con Argon2 (parámetros OWASP: `time_cost=2`, `memory_cost=19456` KiB, `parallelism=1`); roles solo `GERENCIA` y `TECNICO`.
- RUC: exactamente 11 dígitos numéricos.
- **RN-01:** crear/actualizar/anular clientes, contratos y SLA solo `GERENCIA`; `TECNICO` solo lectura.
- **RN-03:** fase 1 = `COMPROMETIDA`; fase 2 = `LIQUIDADA` (baja contable definitiva, solo Gerencia).
- **RN-04:** un acta firmada nunca se edita; las correcciones son `adendas_correccion` vinculadas a la orden.
- Esquema de datos: el de la sección 6 de `CLAUDE.md` (más las tablas nuevas marcadas abajo).
- Cada tarea se marca en la sección 7 de `CLAUDE.md` solo tras `pytest` / `vitest` en verde (suite completa, no solo el archivo).

## Review Focus

Entradas que el spec insinúa y ninguna tarea prueba de forma natural:

1. RUC con espacios, letras o 10/12 dígitos → 422, nunca 500; RUC duplicado → 409.
2. `fecha_fin < fecha_inicio`, monto ≤ 0 o `sla_horas_max_respuesta` ≤ 0 → 422.
3. Salida de stock mayor al disponible → 409 y el stock **no** cambia (transacción atómica); dos salidas concurrentes no dejan stock negativo.
4. JWT expirado, manipulado o de un usuario ya inexistente → 401; `TECNICO` en ruta de Gerencia → 403 (no 401).
5. Liquidar dos veces la misma orden, o liquidar una orden inexistente / ya `LIQUIDADA` → 409/404; adenda sobre orden no liquidable-editable nunca modifica `actas_inmutables`.

---

## Decisiones abiertas (necesito tu confirmación antes de arrancar)

| # | Tema | Recomendación |
|---|------|---------------|
| D1 | **BD de pruebas.** El equipo no tiene Docker ni Postgres local. | Rama de Neon dedicada a tests (`DATABASE_URL_TEST`); aisla cada test con transacción + rollback. Alternativa: `pgserver` (Postgres embebido vía pip). |
| D2 | **Python 3.14 instalado vs 3.12 exigido** por el stack. | Crear venv con 3.12 si está disponible (`py -3.12`); si no, instalar 3.12 antes de seguir. |
| D3 | **Git no está instalado** y el directorio no es repositorio; el plan asume commits frecuentes. | Instalar Git e `git init` (o ejecutar sin commits). |
| D4 | **3.1.3 «Ventas» no existe en el esquema.** | Modelarlo como `ventas` + `ventas_items`: venta de repuestos a un cliente (por RUC) que genera movimientos `SALIDA_VENTA`. Sin facturación electrónica (fuera de alcance). |
| D5 | **`ordenes_servicio` las crea la PWA (Fase 3.2)**, pero la liquidación las necesita. | En 3.1 solo se **leen y liquidan**; los tests las insertan por fixture. Sin endpoint de creación. |
| D6 | **Movimientos de inventario:** REQ-05 los exige ligados a una orden, pero las entradas (compras) no tienen orden. | `orden_id` obligatorio solo para `SALIDA_ORDEN`; opcional para `ENTRADA` y `SALIDA_VENTA`. |

## Tablas nuevas (además de la sección 6)

```sql
CREATE TABLE movimientos_inventario (
    id SERIAL PRIMARY KEY,
    repuesto_codigo VARCHAR(30) NOT NULL REFERENCES repuestos(codigo),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('ENTRADA','SALIDA_ORDEN','SALIDA_VENTA','AJUSTE')),
    cantidad INT NOT NULL CHECK (cantidad > 0),
    orden_id UUID REFERENCES ordenes_servicio(id),
    venta_id INT REFERENCES ventas(id),
    usuario_id INT NOT NULL REFERENCES usuarios(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE ventas (
    id SERIAL PRIMARY KEY,
    cliente_ruc VARCHAR(11) NOT NULL REFERENCES clientes(ruc),
    usuario_id INT NOT NULL REFERENCES usuarios(id),
    total_soles NUMERIC(12,2) NOT NULL,
    fecha TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE ventas_items (
    id SERIAL PRIMARY KEY,
    venta_id INT NOT NULL REFERENCES ventas(id),
    repuesto_codigo VARCHAR(30) NOT NULL REFERENCES repuestos(codigo),
    cantidad INT NOT NULL CHECK (cantidad > 0),
    precio_unitario_soles NUMERIC(10,2) NOT NULL
);
```

## Estructura de archivos

```
backend/
  pyproject.toml            requirements.txt        alembic.ini
  alembic/versions/         migraciones (0001 esquema base, 0002 inventario/ventas)
  app/
    main.py                 crea la app, registra routers
    core/config.py          Settings (pydantic-settings): DATABASE_URL, JWT_SECRET, JWT_EXPIRE_MIN
    core/db.py              engine async + pool conservador, get_session
    core/security.py        hash_password, verify_password, create_access_token, decode_access_token
    core/deps.py            get_current_user, require_role(*roles)
    models/                 un archivo por entidad (usuario, cliente, contrato, equipo, repuesto, movimiento, venta, orden, acta, adenda)
    schemas/                Pydantic v2 por módulo
    services/               lógica por módulo (sin FastAPI)
    api/v1/                 health.py auth.py clientes.py contratos.py inventario.py ventas.py equipos.py liquidacion.py
  tests/                    conftest.py + un test_*.py por módulo
frontend/
  package.json  vite.config.ts  tailwind.config.ts
  src/
    api/client.ts           fetch con JWT + manejo 401/403
    auth/AuthContext.tsx    RequireRole.tsx    LoginPage.tsx
    components/DataTable.tsx  FormField.tsx  Layout.tsx
    features/{clientes,contratos,equipos,inventario,ventas,liquidacion}/  Page + hooks + tests
    App.tsx  main.tsx  test/setup.ts  test/msw.ts
```

---

## Tarea 0: Scaffolding y entorno de pruebas

**Files:** Create `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/core/{config,db}.py`, `backend/tests/conftest.py`, `frontend/*` (Vite + Tailwind + vitest).
**Interfaces:** Produces `get_session() -> AsyncIterator[AsyncSession]`, fixture `client: AsyncClient`, fixture `db: AsyncSession` (rollback por test), `renderWithProviders(ui, {role})` en el frontend.

- [ ] Resolver D1–D3 (venv 3.12, BD de test, git).
- [ ] RED: `tests/test_health.py::test_healthz_devuelve_ok` (`GET /api/v1/healthz` → 200 `{"status":"ok"}`) y `test_healthz_no_requiere_bd`.
- [ ] Verificar fallo → implementar app mínima + healthz → verificar verde.
- [ ] RED/GREEN: `tests/test_db.py::test_pool_conservador` (engine con `pool_size=2`, `max_overflow=1`, `pool_pre_ping=True`) y `test_conexion_neon_responde` (`SELECT 1`).
- [ ] Frontend: `App.test.tsx::renderiza_login` en rojo → verde.
- [ ] Alembic: migración 0001 con el esquema de la sección 6; test que verifica `ruc` con `CHECK (LENGTH=11)` rechaza 10 dígitos.

## Tarea 1 (3.1.7): RBAC – Argon2 + JWT

**Files:** `core/security.py`, `core/deps.py`, `models/usuario.py`, `schemas/auth.py`, `api/v1/auth.py`, `tests/test_security.py`, `tests/test_auth.py`.
**Interfaces:** Produces `hash_password(plain) -> str`, `verify_password(plain, hashed) -> bool`, `create_access_token(sub: int, rol: str) -> str`, `decode_access_token(token) -> TokenPayload`, dependencia `require_role(*roles) -> Callable[..., Usuario]`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`.

Tests (cada uno RED → verificar fallo → GREEN):
- [ ] `test_hash_es_argon2_y_no_reversible`; `test_verify_rechaza_password_incorrecto`.
- [ ] `test_token_contiene_sub_y_rol`; `test_token_expirado_lanza_error`; `test_token_manipulado_lanza_error`.
- [ ] `test_login_ok_devuelve_token`; `test_login_password_incorrecto_401`; `test_login_email_inexistente_401` (mismo mensaje que el anterior, sin enumerar usuarios).
- [ ] `test_me_sin_token_401`; `test_me_con_usuario_borrado_401`.
- [ ] `test_require_role_tecnico_en_ruta_gerencia_403`; `test_rol_invalido_no_se_puede_crear` (CHECK).
- [ ] Semilla: script `python -m app.scripts.crear_gerente` (usa variables de entorno, sin credenciales en el repo).
- [ ] Marcar 3.1.7 en `CLAUDE.md` tras `pytest` completo en verde.

## Tarea 2 (3.1.1): Clientes

**Files:** `models/cliente.py`, `schemas/cliente.py`, `services/clientes.py`, `api/v1/clientes.py`, `tests/test_clientes.py`.
**Interfaces:** Consumes `require_role`. Produces `GET/POST /api/v1/clientes`, `GET/PUT/DELETE /api/v1/clientes/{ruc}` (DELETE = baja lógica `activo=false`; se añade la columna `activo BOOLEAN DEFAULT TRUE` en migración 0002).

- [ ] `test_crear_cliente_gerencia_201`; `test_crear_cliente_tecnico_403` (RN-01).
- [ ] `test_ruc_10_digitos_422`, `test_ruc_12_digitos_422`, `test_ruc_con_letras_422`, `test_ruc_con_espacios_422`.
- [ ] `test_ruc_duplicado_409`; `test_razon_social_y_direccion_obligatorias_422`.
- [ ] `test_tecnico_puede_listar_y_leer_200`; `test_actualizar_solo_gerencia`; `test_anular_cliente_con_contrato_activo_409`.
- [ ] `test_cliente_inexistente_404`.

## Tarea 3 (3.1.2): Contratos y SLA

**Files:** `models/contrato.py`, `schemas/contrato.py`, `services/contratos.py`, `api/v1/contratos.py`, `tests/test_contratos.py`.
**Interfaces:** Produces `POST/GET /api/v1/contratos`, `GET/PUT /api/v1/contratos/{id}`, `POST /api/v1/contratos/{id}/anular`; estados `ACTIVO|VENCIDO|ANULADO`.

- [ ] `test_crear_contrato_gerencia_201`; `test_crear_contrato_tecnico_403` (RN-01).
- [ ] `test_fecha_fin_anterior_a_inicio_422`; `test_monto_cero_o_negativo_422`; `test_sla_horas_cero_o_negativo_422`; `test_sla_por_defecto_4`.
- [ ] `test_cliente_inexistente_404`; `test_contrato_incompleto_bloqueado` (REQ-04, sin dejar fila parcial).
- [ ] `test_solapamiento_de_vigencia_mismo_cliente_409` **[a confirmar en D-extra: ¿permitir contratos solapados por cliente?]**.
- [ ] `test_anular_contrato_cambia_estado_y_es_solo_gerencia`.

## Tarea 4 (3.1.4): Inventario (stock central y movimientos)

**Files:** `models/{repuesto,movimiento}.py`, `schemas/inventario.py`, `services/inventario.py`, `api/v1/inventario.py`, `tests/test_inventario.py`.
**Interfaces:** Produces `registrar_movimiento(session, codigo, tipo, cantidad, usuario_id, orden_id=None, venta_id=None) -> Movimiento` (bloquea la fila con `SELECT … FOR UPDATE`), `POST/GET /api/v1/repuestos`, `POST /api/v1/inventario/movimientos`, `GET /api/v1/inventario/movimientos?repuesto=`.

- [ ] `test_crear_repuesto_y_stock_inicial_0`; `test_costo_negativo_422`; `test_codigo_duplicado_409`.
- [ ] `test_entrada_incrementa_stock`; `test_salida_decrementa_stock`.
- [ ] `test_salida_mayor_al_stock_409_y_stock_intacto`.
- [ ] `test_salida_orden_sin_orden_id_422` (D6); `test_cantidad_cero_422`.
- [ ] `test_movimiento_deja_registro_con_usuario_y_fecha`.
- [ ] `test_dos_salidas_concurrentes_no_dejan_stock_negativo` (`asyncio.gather` sobre sesiones distintas).
- [ ] Permisos: `GERENCIA` escribe; `TECNICO` solo lectura del stock central.

## Tarea 5 (3.1.3): Ventas

**Files:** `models/venta.py`, `schemas/venta.py`, `services/ventas.py`, `api/v1/ventas.py`, `tests/test_ventas.py`.
**Interfaces:** Consumes `registrar_movimiento`. Produces `POST /api/v1/ventas` (transacción única: venta + items + movimientos `SALIDA_VENTA`), `GET /api/v1/ventas`, `GET /api/v1/ventas/{id}`.

- [ ] `test_venta_descuenta_stock_y_calcula_total`; `test_venta_sin_items_422`; `test_venta_con_stock_insuficiente_409_y_no_crea_venta` (rollback completo).
- [ ] `test_venta_cliente_inexistente_404`; `test_venta_solo_gerencia_escribe`.
- [ ] `test_venta_repuesto_duplicado_en_items_se_acumula` (mismo código dos veces no evade la validación de stock).

## Tarea 6 (3.1.5): Equipos

**Files:** `models/equipo.py`, `schemas/equipo.py`, `services/equipos.py`, `api/v1/equipos.py`, `tests/test_equipos.py`.
**Interfaces:** Produces `POST/GET /api/v1/equipos`, `GET/PUT /api/v1/equipos/{serie}`; `tipo_sistema ∈ {OSMOSIS_INVERSA, ABLANDADOR, FILTRO}`.

- [ ] `test_crear_equipo_osmosis_con_parametros_nominales_201`; `test_tipo_sistema_invalido_422`.
- [ ] `test_serie_duplicada_409`; `test_serie_vacia_422`; `test_parametros_nominales_obligatorios_422`.
- [ ] `test_cliente_o_contrato_inexistente_404`; `test_contrato_de_otro_cliente_422`.
- [ ] `test_fecha_instalacion_futura_422`; `test_tecnico_lee_pero_no_escribe`.

## Tarea 7 (3.1.6): Liquidación y adendas

**Files:** `models/{orden,acta,adenda}.py`, `schemas/liquidacion.py`, `services/liquidacion.py`, `api/v1/liquidacion.py`, `tests/test_liquidacion.py`.
**Interfaces:** Consumes `registrar_movimiento`. Produces `GET /api/v1/ordenes?estado=`, `GET /api/v1/ordenes/{id}`, `POST /api/v1/ordenes/{id}/liquidar`, `POST /api/v1/ordenes/{id}/adendas`, `GET /api/v1/ordenes/{id}/adendas`.

- [ ] `test_liquidar_orden_comprometida_pasa_a_liquidada` (RN-03 fase 2).
- [ ] `test_liquidar_dos_veces_409`; `test_liquidar_orden_inexistente_404`; `test_liquidar_solo_gerencia_403_tecnico`.
- [ ] `test_liquidar_no_modifica_acta_inmutable` (hash y payload idénticos antes/después).
- [ ] `test_crear_adenda_vincula_orden_y_gerente`; `test_adenda_no_edita_acta` (RN-04); `test_adenda_sin_observacion_422`.
- [ ] `test_adenda_con_ajuste_repuestos_genera_movimiento_ajuste`; `test_adenda_ajuste_excede_stock_409`.
- [ ] `test_no_existe_endpoint_put_delete_sobre_acta` (405/404).

## Tarea 8: Frontend – base, auth y rutas protegidas

**Files:** `src/api/client.ts`, `src/auth/{AuthContext,RequireRole,LoginPage}.tsx`, `src/components/{Layout,DataTable,FormField}.tsx`, tests junto a cada archivo.
**Interfaces:** Produces `useAuth(): {user, login, logout}`, `<RequireRole roles={['GERENCIA']}>`, `<DataTable columns rows onEdit? />`, `apiFetch<T>(path, init)`.

- [ ] `LoginPage`: éxito guarda sesión y redirige; credenciales malas muestran error.
- [ ] `RequireRole`: sin sesión → `/login`; `TECNICO` en ruta de Gerencia → pantalla «Acceso denegado».
- [ ] `apiFetch`: adjunta `Authorization`; ante 401 limpia sesión y redirige.
- [ ] `DataTable`: estado vacío «Sin datos disponibles»; oculta acciones de edición si no se pasa `onEdit`.
- [ ] Token en `sessionStorage` (no `localStorage`); decisión anotada en el código.

## Tarea 9: Frontend – Clientes y Contratos

- [ ] `ClientesPage`: lista, formulario con validación de RUC (11 dígitos) **antes** de enviar; botones crear/editar solo con rol `GERENCIA`; muestra el 409 del backend.
- [ ] `ContratosPage`: lista, formulario con fechas/monto/SLA y validaciones equivalentes al backend; `TECNICO` ve solo lectura.

## Tarea 10: Frontend – Equipos, Inventario, Ventas y Liquidación

- [ ] `EquiposPage`: tabla + ficha técnica (tipo, serie, fecha, parámetros).
- [ ] `InventarioPage`: stock central, alta de repuesto, registro de movimientos, error legible ante stock insuficiente.
- [ ] `VentasPage`: alta con ítems, total calculado.
- [ ] `LiquidacionPage` (solo Gerencia): órdenes `COMPROMETIDA`, acción «Liquidar», formulario de adenda; el acta se muestra en solo lectura.

## Tarea 11: Cierre de fase

- [ ] `pytest` y `vitest run` completos en verde, salida sin warnings.
- [ ] `tsc --noEmit` y build de Vite sin errores.
- [ ] Marcar 3.1.1–3.1.7 y 3.1 en la sección 7 de `CLAUDE.md`.
- [ ] Revisión final con `requesting-code-review` y `verification-before-completion`.

## Nota de alcance del plan

Este documento fija arquitectura, interfaces y los tests (con nombre y comportamiento) de cada tarea. El **código de cada test se escribe en el paso RED de cada tarea**, no aquí; si prefieres el código completo de cada test en el documento antes de arrancar, lo expando.

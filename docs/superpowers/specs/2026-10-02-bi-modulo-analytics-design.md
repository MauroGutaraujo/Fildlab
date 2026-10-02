# Módulo 4.1 — Business Intelligence (Apache ECharts): Diseño

**Estado:** Aprobado por el usuario en brainstorming (2026-10-02). Listo para `writing-plans`.

## 1. Propósito y alcance

Dar a Gerencia dos tableros analíticos en la Plataforma Web Central, bajo presupuesto S/. 0.00: rentabilidad real por contrato y cumplimiento de SLA, renderizados con Apache ECharts del lado del cliente (CSR), sin que el backend transaccional cargue agregaciones pesadas en memoria (Render free tier: 512 MB RAM / 0.1 vCPU).

**Cubre del EDT:**
- 4.1.1 Tablero de rentabilidad financiera por contrato
- 4.1.2 Tablero de seguimiento y alertas de SLA (< 2%)

**No cubre:**
- 4.2 (RUL/supervivencia) ni 4.3 (pruebas generales de calidad ISO/IEC 25010) — fases separadas.
- Ingresos de `ventas` (punto de venta) — decisión explícita, ver sección 2.
- Cualquier campo nuevo de "horas de mano de obra" en el esquema — decisión explícita, ver sección 2.
- Prorrateo de ingreso contractual por días — se usa mes calendario completo.

## 2. Decisiones de diseño confirmadas con el usuario

1. **Horas de servicio:** no existe ningún campo de horas trabajadas en el esquema (`tiempo_respuesta_horas` es tiempo de respuesta del SLA, no mano de obra). El margen se calcula solo como `ingreso contractual − costo de repuestos`, sin componente de horas. Agregar ese campo queda fuera de alcance (tocaría la PWA offline-first ya cerrada en 3.2 y no hay datos históricos).
2. **Estados de orden para costo de repuestos:** solo `LIQUIDADA` (RN-03 Fase 2 — es cuando Gerencia consolida la baja contable definitiva).
3. **Definición de cumplimiento SLA:** por orden, `tiempo_respuesta_horas <= contrato.sla_horas_max_respuesta`. El universo de órdenes para el tablero de SLA **no se filtra por estado** — es una métrica operativa de puntualidad, no depende de que la liquidación contable haya concluido.
4. **Selector de periodo:** mes calendario (`YYYY-MM`), no rango libre.
5. **Ventas (punto de venta):** quedan fuera del cálculo de rentabilidad por contrato — no están vinculadas de forma consistente a contratos en el esquema actual.
6. **Atribución temporal del costo:** por **mes de servicio** (`ordenes_servicio.fecha_creacion_cliente`), no por mes de liquidación — principio de devengo. Una orden de marzo liquidada en abril sigue contando como costo de marzo.

## 3. Arquitectura — Backend

### 3.1 Router nuevo: `backend/app/api/v1/analytics.py`

```python
router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_role("GERENCIA"))])
```

Mismo patrón que `ventas.py`/`liquidacion.py`: todo el router exige rol GERENCIA (RN-01), nunca expuesto a TECNICO. Registrado en `app/main.py` junto a los demás routers, prefijo final `/api/v1/analytics`.

Agregación **en SQL** (SQLAlchemy `func.sum`/`group_by`), nunca trayendo filas crudas a Python — ver sección 1 del pasado turno de diseño para el razonamiento de por qué (RAM/CPU del free tier de Render).

### 3.2 `GET /api/v1/analytics/rentabilidad?periodo=YYYY-MM`

Valida `periodo` con un patrón `YYYY-MM` (Pydantic/regex) → 422 si no matchea o el mes es inválido.

Por cada contrato cuyo rango (`fecha_inicio`..`fecha_fin`) se solapa con el mes pedido:
- `ingreso_soles` = `monto_mensual_soles` (mes completo, sin prorrateo).
- `costo_repuestos_soles` = `SUM(movimientos_inventario.cantidad * repuestos.costo_unitario_soles)` para movimientos `tipo='SALIDA_ORDEN'`, unidos a `ordenes_servicio` donde `estado='LIQUIDADA'` y `fecha_creacion_cliente` cae en el mes pedido, y la orden pertenece a ese contrato. `0` si no hay movimientos.
- `margen_soles` = ingreso − costo.
- `margen_pct` = `margen_soles / ingreso_soles * 100` si `ingreso_soles > 0`, si no `null`.

Respuesta (200 siempre, nunca 404 por "sin datos" — ver sección 5):
```json
{
  "periodo": "2026-09",
  "contratos": [
    {
      "contrato_id": 12,
      "cliente_ruc": "20612493821",
      "razon_social": "Clínica Ejemplo S.A.C.",
      "ingreso_soles": 2500.00,
      "costo_repuestos_soles": 340.50,
      "margen_soles": 2159.50,
      "margen_pct": 86.38
    }
  ]
}
```
Sin contratos activos en el mes → `"contratos": []`.

### 3.3 `GET /api/v1/analytics/sla?periodo=YYYY-MM`

Sobre todas las órdenes con `fecha_creacion_cliente` en el mes pedido (sin filtrar por `estado`):
- `total_ordenes`: conteo.
- `ordenes_fuera_sla`: lista de las que exceden `contrato.sla_horas_max_respuesta`, con `orden_id`, `equipo_serie`, `cliente_ruc`/`razon_social`, `tiempo_respuesta_horas`, `sla_horas_max_respuesta`.
- `pct_cumplimiento`: `(total_ordenes - len(ordenes_fuera_sla)) / total_ordenes * 100` si `total_ordenes > 0`, si no `null`.

```json
{
  "periodo": "2026-09",
  "total_ordenes": 48,
  "ordenes_fuera_sla": [
    { "orden_id": "...", "equipo_serie": "RO-2026-0001", "razon_social": "Clínica X", "tiempo_respuesta_horas": 9.5, "sla_horas_max_respuesta": 4 }
  ],
  "pct_cumplimiento": 97.92
}
```
Sin órdenes en el mes → `"total_ordenes": 0, "ordenes_fuera_sla": [], "pct_cumplimiento": null`.

## 4. Arquitectura — Frontend

### 4.1 Dependencia nueva

`echarts` + `echarts-for-react`, con imports modulares (`echarts/core` + `BarChart`/`LineChart`/`GaugeChart`/`GridComponent`/`TooltipComponent`/`LegendComponent`, `CanvasRenderer`) para mantener el bundle liviano — ninguna de las dos es una "librería pesada" en el sentido de frameworks/UI kits; es la librería de gráficos que `CLAUDE.md` ya exige, con su wrapper oficial de React.

### 4.2 `frontend/src/features/bi/`

- `BiPage.tsx` — página única (sigue el patrón flat de `ventas/`, `liquidacion/`). Estado local `periodo: string` (default: mes actual, `YYYY-MM`), con un selector de mes/año. Dos `useQuery` de TanStack Query independientes por periodo:
  ```ts
  useQuery({ queryKey: ["analytics", "rentabilidad", periodo], queryFn: () => apiFetch(`/analytics/rentabilidad?periodo=${periodo}`) })
  useQuery({ queryKey: ["analytics", "sla", periodo], queryFn: () => apiFetch(`/analytics/sla?periodo=${periodo}`) })
  ```
- `TableroRentabilidad.tsx` — recibe los datos de rentabilidad; barras agrupadas (ingreso vs costo) por contrato + línea de `margen_pct` en eje secundario.
- `TableroSla.tsx` — gauge/dona con `pct_cumplimiento` (verde si ≥98%, rojo si menor, coherente con la meta REQ-15 de <2% fuera de SLA) + tabla de `ordenes_fuera_sla` reutilizando `DataTable.tsx`.
- Cada tablero maneja su propio loading/error/vacío — si SLA falla, rentabilidad igual se renderiza (y viceversa).

### 4.3 Ruta y navegación

- `App.tsx`: `<Route path="bi" element={<RequireRole roles={["GERENCIA"]}><BiPage /></RequireRole>} />` dentro del árbol de `Layout`.
- `Layout.tsx`: nueva entrada en `ENLACES` ("BI", ícono SVG nuevo siguiendo el patrón ya existente), visible solo si `user.rol === "GERENCIA"` (el array ya filtra por `roles` en el `.filter()` existente).

## 5. Manejo de errores y estado vacío (REQ-16)

- **Loading:** spinner igual al patrón de `DataTable` (borde animado), independiente por tablero.
- **Error:** mismo bloque rojo de alerta que `DataTable`/`FormPanel`, con el mensaje de `ApiError` (incluye un eventual 403 si TECNICO llegara a golpear el endpoint directo, aunque la ruta ya está protegida por `RequireRole` en el cliente y `require_role` en el servidor).
- **Vacío — texto exacto:** `"Sin datos disponibles para el periodo"`. El backend **nunca** devuelve 404 por ausencia de datos — siempre 200 con listas vacías / `null` en los porcentajes (evita división entre cero). El frontend decide mostrar el estado vacío por `contratos.length === 0` o `total_ordenes === 0`, nunca intenta renderizar un gráfico con datos en cero reales.
- **Validación de `periodo`:** formato inválido → 422 de FastAPI/Pydantic, mostrado como el bloque de error ya descrito.

## 6. Pruebas

### 6.1 Backend — `backend/tests/test_analytics.py`

- RBAC: TECNICO → 403 en ambos endpoints (`tecnico_h`); GERENCIA → 200 (`gerente_h`).
- Rentabilidad: contrato + orden `LIQUIDADA` con movimientos `SALIDA_ORDEN` en el mes → `ingreso`/`costo`/`margen` correctos; orden `COMPROMETIDA` (no liquidada) → no suma costo pero el contrato sigue listado con `costo_repuestos_soles: 0`; orden de otro mes → excluida del costo; sin contratos activos en el mes → `"contratos": []`, 200.
- SLA: orden que excede `sla_horas_max_respuesta` → aparece en `ordenes_fuera_sla`; orden que cumple → no aparece; orden `SINCRONIZADA` (no liquidada) → sí cuenta para SLA (a diferencia de rentabilidad); sin órdenes en el mes → `total_ordenes: 0`, `pct_cumplimiento: null`, `ordenes_fuera_sla: []`.
- `periodo` con formato inválido (`"2026-13"`, `"abc"`, vacío) → 422.

### 6.2 Frontend — `frontend/src/features/bi/BiPage.test.tsx`

- Selector de periodo por defecto al mes actual; cambiarlo dispara nuevas queries con el `periodo` correcto en la URL.
- `TableroRentabilidad`/`TableroSla` reciben los datos correctos: se mockea el wrapper `echarts-for-react` en los tests (capturando el prop `option` recibido) en vez de inspeccionar un `<canvas>` — patrón estándar para testear componentes ECharts con Testing Library.
- Loading, error y vacío (`"Sin datos disponibles para el periodo"`) para cada tablero, de forma independiente entre sí.
- TECNICO no ve el enlace "BI" en el navbar ni puede acceder a `/bi` (reutiliza el patrón ya probado de `RequireRole`).
- `npm run build` compila limpio con la dependencia nueva de `echarts`/`echarts-for-react`.

## 7. Puntos que este spec resuelve explícitamente

- Sin campo nuevo de horas de mano de obra: el margen es solo ingreso contractual vs costo de repuestos, declarado como limitación de alcance, no escondido.
- Costo de repuestos atribuido por mes de **servicio** (devengo), no por mes de **liquidación** — una orden liquidada tarde sigue corrigiendo el margen del mes en que se prestó el servicio.
- SLA es una métrica operativa independiente del estado contable de la orden; rentabilidad sí exige `LIQUIDADA`.
- Toda agregación ocurre en SQL (Neon/Postgres), nunca cargando filas crudas a memoria del proceso FastAPI (respeta el límite de 512 MB/0.1 vCPU de Render).
- El backend nunca responde 404 por ausencia de datos — siempre 200 con estructuras vacías/`null`, y el frontend decide el estado vacío (REQ-16) a partir de eso.
- Dos endpoints independientes (no uno combinado) para que un fallo en SLA no tumbe el tablero de rentabilidad ni viceversa.

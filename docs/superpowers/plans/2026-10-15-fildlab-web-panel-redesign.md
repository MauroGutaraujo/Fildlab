# Fildlab Web Panel Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the Fildlab administrative web UI for contract auditing, SLA monitoring, synchronized order settlement, inventory, and equipment RUL while preserving current behavior and data.

**Architecture:** Refine the existing Tailwind shell and shared form/table primitives, then apply their visual language to existing business pages and BI dashboards. Keep React Router, role guards, TanStack Query, API contracts, mutations, and ECharts setup unchanged; derive all visible values from current query data.

**Tech Stack:** React 18, TypeScript, Tailwind CSS 4, React Router, TanStack Query, Apache ECharts.

**Spec:** `docs/superpowers/specs/2026-10-15-ux-redesign-panel-pwa-design.md`

## Global Constraints

- Implement styles with Tailwind CSS already installed. Do not add shadcn/ui or visual dependencies.
- Use clean/deep blues, slate/zinc surfaces, and emerald, amber, and crimson semantic states.
- Keep existing routes, queries, mutations, API payloads, permissions, and business rules unchanged.
- Never invent static operational metrics; show only values backed by existing API responses.
- Keep BI charts client-rendered with `echarts-for-react/lib/core` and reactive TanStack Query data.

## Review Focus

- A user without GERENCIA role must not gain write actions due to redesigned page headers; retain `puedeEscribir` conditions and existing role tests.
- Empty, loading, and failed queries must remain distinguishable; keep the `DataTable` state tests and add assertions only if its state markup changes.
- RUL values absent from prediction data must still render as “Sin evaluar”; preserve/add a focused EquiposPage assertion.
- SLA below 98%, at exactly 98%, and above 98% must preserve the source data and semantic color threshold; pin the gauge threshold in TableroSla tests.
- Long client names and narrow screens must not make tables unusable; verify responsive overflow and readable labels in `DataTable.test.tsx`.

---

### Task 1: Shared visual primitives and desktop shell

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/components/DataTable.tsx`
- Modify: `frontend/src/components/FormField.tsx`
- Modify: `frontend/src/components/FormPanel.tsx`
- Test: `frontend/src/components/Layout.test.tsx`
- Test: `frontend/src/components/DataTable.test.tsx`

**Interfaces:**
- Consumes: existing `Layout` auth/router behavior and `DataTable`/form component props.
- Produces: same component exports and props; polished responsive primitives for all pages.

- [ ] **Step 1: Pin shell and table behaviors before styling**

Add assertions to existing tests for the selected active route, role-filtered navigation, empty/loading/error table states, and an action column remaining optional. Do not rewrite behavior tests.

- [ ] **Step 2: Run the focused baseline tests**

Run from `frontend`: `npm test -- --run src/components/Layout.test.tsx src/components/DataTable.test.tsx`.
Expected: current tests pass; any new assertion must first fail only when its target behavior is absent.

- [ ] **Step 3: Apply the shared visual system**

Keep Tailwind import and font stack in `index.css`; set neutral page background, consistent text rendering, focus-visible outlines, and scrollbar. Convert `Layout` to a navy sidebar/header + light work surface with responsive navigation while retaining the same `NavLink`s, `ENLACES` role filter, breadcrumb, logout handler, and `Outlet`. Give `DataTable` a white bordered surface, muted header row, compact separators, horizontal overflow wrapper, and explicit accessible loading/empty/error states. Give form fields and panels consistent slate borders, blue focus rings, rounded corners, spacing, and disabled styles. Use utility patterns such as `rounded-xl border border-slate-200 bg-white shadow-sm` and `focus-visible:outline-2 focus-visible:outline-blue-600`; do not create new dependencies.

- [ ] **Step 4: Run shared component tests**

Run: `npm test -- --run src/components/Layout.test.tsx src/components/DataTable.test.tsx`.
Expected: PASS with navigation, permissions, and table state behavior unchanged.

- [ ] **Step 5: Commit the shared shell**

Run: `git add frontend/src/index.css frontend/src/components frontend/src/components/Layout.test.tsx frontend/src/components/DataTable.test.tsx; git commit -m "style(frontend): refresh admin shell and shared controls"`.

### Task 2: Contract, equipment, inventory, and settlement screens

**Files:**
- Modify: `frontend/src/features/contratos/ContratosPage.tsx`
- Modify: `frontend/src/features/equipos/EquiposPage.tsx`
- Modify: `frontend/src/features/inventario/InventarioPage.tsx`
- Modify: `frontend/src/features/liquidacion/LiquidacionPage.tsx`
- Test: corresponding `*.test.tsx` files for the four features

**Interfaces:**
- Consumes: the shared primitives from Task 1 and existing query/mutation data.
- Produces: visually aligned contract audit, RUL, inventory, and settlement pages with current public behavior.

- [ ] **Step 1: Strengthen representative behavior assertions**

Ensure page tests cover role-based create/edit controls, a query result row, and the RUL “Sin evaluar” or amber/red alert rendering. Add a settlement test that confirms “Liquidar” remains gated by the current status and only invokes the current mutation when valid.

- [ ] **Step 2: Run these feature tests before styling**

Run: `npm test -- --run src/features/contratos/ContratosPage.test.tsx src/features/equipos/EquiposPage.test.tsx src/features/inventario/InventarioPage.test.tsx src/features/liquidacion/LiquidacionPage.test.tsx`.
Expected: PASS against current business behavior.

- [ ] **Step 3: Restyle the four feature pages**

Give each page a consistent title/action row and use cards for contextual summaries only where a count/value is already available from that page's response. In contracts, emphasize vigencia, SLA hours, and active/anulado state. In equipment, retain prediction data and existing `BadgeAlerta` thresholds while making RUL and preventive maintenance action scannable. In inventory, separate stock list from recent movements. In settlement, make sync/commit/liquidated states, audit acta, adenda, and order actions legible. Preserve every handler, permission check, query key, mutation, confirmation, form field, and label meaning; never add fake dashboard totals.

- [ ] **Step 4: Run feature tests**

Run the Task 2 test command.
Expected: PASS; role visibility, mutations, filters, RUL levels, and settlement flow retain current results.

- [ ] **Step 5: Commit business page styling**

Run: `git add frontend/src/features/contratos frontend/src/features/equipos frontend/src/features/inventario frontend/src/features/liquidacion; git commit -m "style(frontend): clarify contracts equipment and settlement"`.

### Task 3: BI views and remaining web pages

**Files:**
- Modify: `frontend/src/features/bi/BiPage.tsx`
- Modify: `frontend/src/features/bi/TableroSla.tsx`
- Modify: `frontend/src/features/bi/TableroRentabilidad.tsx`
- Modify: `frontend/src/features/clientes/ClientesPage.tsx`
- Modify: `frontend/src/features/ventas/VentasPage.tsx`
- Test: corresponding `*.test.tsx` files and `frontend/src/features/bi/echartsSetup.ts` (read-only verification)

**Interfaces:**
- Consumes: shared primitives and existing reactive BI/customer/sales queries.
- Produces: coherent styling across all web routes; identical chart and data contracts.

- [ ] **Step 1: Pin reactive chart and business states**

In existing BI tests assert the period control updates the dashboard query inputs, loading/error/empty states are retained, and SLA alert rows still display. Add a test at 97.99% and 98% only if current behavior defines the boundary; otherwise preserve the existing 0.98 threshold exactly and test that line in source.

- [ ] **Step 2: Run BI, customer, and sales tests**

Run: `npm test -- --run src/features/bi src/features/clientes/ClientesPage.test.tsx src/features/ventas/VentasPage.test.tsx`.
Expected: PASS before visual changes.

- [ ] **Step 3: Apply visual hierarchy without changing chart setup**

Use the shared surfaces for chart panels, period control, customer table/forms, and sales total/forms. Keep `periodoActual`, query keys/functions, ECharts option data mappings, `echartsSetup`, and `ReactEChartsCore` rendering unchanged except color tokens required by the approved palette. Keep chart options data-driven and errors/empty states explicit.

- [ ] **Step 4: Run BI and remaining page tests**

Run the Task 3 test command.
Expected: PASS; charts remain reactive and pages keep current server-derived values.

- [ ] **Step 5: Commit BI and remaining pages**

Run: `git add frontend/src/features/bi frontend/src/features/clientes frontend/src/features/ventas; git commit -m "style(frontend): align BI and service pages"`.

### Task 4: Web build and final regression review

**Files:**
- Verify: all modified `frontend/src/**` files and the web spec.

- [ ] **Step 1: Run the production build**

Run from `frontend`: `npm run build`.
Expected: TypeScript and Vite build succeed.

- [ ] **Step 2: Run the full frontend test suite**

Run from `frontend`: `npm test`.
Expected: all existing and added frontend tests pass.

- [ ] **Step 3: Inspect behavior-sensitive diff**

Run `git diff -- frontend/src`; verify no changes to API URLs, query keys, mutation payloads, role guards, route paths, or `echartsSetup.ts` registration. Confirm all new metrics are rendered only from response data.

- [ ] **Step 4: Commit final fixes if required**

If build/test review requires a correction, stage only the exact affected paths, for example `git add frontend/src/components/DataTable.tsx frontend/src/components/DataTable.test.tsx`, then run `git commit -m "fix(frontend): preserve behavior in visual refresh"`.

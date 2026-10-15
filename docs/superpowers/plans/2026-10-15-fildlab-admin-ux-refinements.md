# Fildlab Admin UX Refinements Implementation Plan

> **For agentic workers:** Implement inline with `superpowers:executing-plans`. Each task ends with its focused tests and a commit.

**Goal:** Make client identity, equipment health, inventory, audit, and SLA information easier to scan in the existing admin panel.

**Architecture:** Add a shared client lookup/view that consumes the existing `/clientes` response. Refine feature-level React views using existing React Query data, Tailwind CSS, and ECharts. Use only current backend endpoints and payloads; keep business mutations, role gates, and routes unchanged.

**Tech Stack:** React 18, TypeScript, Tailwind CSS 4, TanStack Query, Apache ECharts, Vitest.

**Spec:** User request in this thread; existing base design: `docs/superpowers/specs/2026-10-15-ux-redesign-panel-pwa-design.md`.

## Global Constraints

- Do not change backend code, request bodies, response contracts, routes, role rules, or mutation behavior.
- Use the existing `GET /clientes`, `GET /ordenes`, `GET /contratos`, and `GET /analytics/sla` responses only.
- Do not fabricate identity, response-time averages, counts, or stock values when source data is missing.
- Keep charts client-rendered with `echarts-for-react/lib/core` and reactive query data.
- Preserve loading, empty, and error states and keep the selected thresholds: SLA 98%; RUL >60 / 15–60 / <15 days; stock >10 / 1–5 / 0 units.

## Review Focus

- Client lookup may fail or may have no exact company-name match; retain the source RUC/name and never substitute another client.
- SLA metrics may have zero measurements, missing order/contract query data, or exactly 98% compliance; use truthful fallbacks and the explicit success boundary.
- RUL values at exactly 15 and 60 days, negative values, and absent predictions must have deterministic semantic states.
- Stock levels 0, 1, 5, 6, 10, and 11 must avoid implying the wrong threshold state.
- Acta signature data has no signer name/type; display the stored image without claiming an identity the response does not provide. Keep hashes collapsed by default.

---

### Task 1: Client identity in contracts, sales, and SLA

**Files:** Create `frontend/src/components/ClienteIdentidad.tsx`; create `frontend/src/features/clientes/useClientesLookup.ts`; modify Contracts, Sales, and SLA views/tests.

**Steps:**

1. Add tests proving contracts and sales render the client reason plus `RUC: ...`, and SLA resolves a RUC from a unique normalized reason match.
2. Run the three focused page test files and confirm the new assertions fail for missing reason/RUC display.
3. Add one shared TanStack Query lookup under `['clientes']`, indexed by exact RUC and unique accent/case-insensitive reason; ambiguous names do not map to an arbitrary RUC.
4. Add a stacked, bold-name/secondary-RUC presentation component and wire it into the three table columns. Preserve source values as fallbacks if lookup is unavailable.
5. Re-run the three focused test files; verify mutation payload tests remain unchanged. Commit the task.

### Task 2: Equipment system, RUL, and nominal parameter badges

**Files:** Modify `frontend/src/features/equipos/EquiposPage.tsx` and its tests.

**Steps:**

1. Add coverage for system chips, formatted TDS/pH badges, absent predictions, and RUL boundaries at 15/60 days.
2. Run the focused equipment tests and confirm the new visual assertions fail.
3. Render system types as colored icon chips; calculate display status from days remaining (`>60` optimal, `15–60` maintenance soon, `<15` urgent); keep `Sin evaluar` when absent.
4. Show TDS entrance, post-membrane, and pH as compact formatted badges in the table and render all nominal parameters as unit-aware badges in the detail dialog.
5. Re-run equipment tests and confirm create payload and role guards remain unchanged. Commit the task.

### Task 3: Inventory stock indicators, currency, and sections

**Files:** Modify `frontend/src/features/inventario/InventarioPage.tsx` and its tests.

**Steps:**

1. Add tests for stock levels 0, 1, 5, 6, 10, and 11, Peruvian currency with two decimals, and distinct catalog/movement headings.
2. Run focused inventory tests and confirm the new assertions fail.
3. Add red zero-stock, amber 1–5, emerald >10, and neutral 6–10 badges. Format displayed prices as `S/. 120.00` without changing stored or submitted values.
4. Keep both tables visible and separate them into clear catalog and movement sections; preserve all existing controls and mutation inputs.
5. Re-run inventory tests and verify existing create/movement payload assertions. Commit the task.

### Task 4: Liquidation audit details and correction copy

**Files:** Modify `frontend/src/features/liquidacion/LiquidacionPage.tsx` and its tests.

**Steps:**

1. Add assertions that the raw hash is absent while the audit disclosure is closed, appears when opened, and the signature image/GPS are presented readably.
2. Add an assertion for the administrative correction explanation and preserve the existing adenda request-body tests.
3. Run focused liquidation tests and confirm the new audit assertions fail.
4. Add a green integrity badge; move SHA-256 and prior hash into a collapsed technical disclosure; show the acta signature image with an explicit note that signer identity is not included; format GPS coordinates to five decimals.
5. Update the adenda title and explanatory copy without changing the POST payload or immutable acta behavior.
6. Re-run the full liquidation test file and commit the task.

### Task 5: SLA dashboard with truthful summary cards

**Files:** Modify `frontend/src/features/bi/TableroSla.tsx` and `TableroSla.test.tsx`.

**Steps:**

1. Add tests for the 98% success boundary and secondary cards with source data, no measurements, and failed supporting queries.
2. Run focused SLA tests and confirm the new assertions fail.
3. Restyle the primary card and client-side gauge. At `>=98` show emerald `SLA en Norma (Meta > 98%)`; below it show an amber/red `Riesgo de Penalización Contractual` state.
4. Derive orders in-period, on-time, and late counts from the SLA response fields. Derive average measured response and matching average contract limit from current `/ordenes` and `/contratos` endpoints, filtered to the selected Lima calendar month. If supporting data or measurements are unavailable, show an explicit no-data state rather than a fabricated example.
5. Keep the existing outside-SLA table and its customer identity lookup. Re-run focused BI tests and commit.

### Task 6: Verification and sensitive-diff review

1. Run `npm test` and `npm run build` from `frontend`.
2. Inspect the complete frontend diff and confirm no backend changes, API payload changes, route changes, permission changes, or ECharts client-rendering changes.
3. Record commands/results and any deferred review notes in the local execution ledger.


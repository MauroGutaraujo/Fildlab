# Fildlab Field PWA Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the technician's offline field workflow clearer and easier to use on mobile while preserving every existing order validation, local save, signature, stock, GPS, and sync behavior.

**Architecture:** Keep `App` as the navigation and offline-sync owner. Extract presentational order sections with explicit props so `OrdenForm` remains the sole owner of field state, validation, stock consumption, GPS, signature validity, and IndexedDB write logic. Apply responsive Tailwind styling to the equipment picker, order, signature, stock, and local-order views.

**Tech Stack:** React 18, TypeScript, Tailwind CSS 4, Dexie, TanStack Query, react-signature-canvas, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-15-ux-redesign-panel-pwa-design.md`

## Global Constraints

- Implement styles with Tailwind CSS already installed. Do not add shadcn/ui or visual dependencies.
- Use clean/deep blues, slate/zinc surfaces, and emerald, amber, and crimson semantic states.
- Do not change Dexie schemas, local order payload, Outbox/sync behavior, or API contracts.
- Keep the eight existing readings, their validations, required GPS, non-empty signature, and order-completion gate.
- Keep spare parts in the existing selection and immediate local stock-discount flow; do not add a checklist or change stock semantics.
- Keep `react-signature-canvas`, explicit width 600/height 200, stroke settings, and signature save validation unchanged.

## Review Focus

- Invalid/negative/non-numeric readings and pH outside 0–14 must continue to block completion; existing validators and order tests must prove this.
- A stock shortage or invalid part quantity must show the current error and must not append a consumed part; preserve the `consumir` path and its existing coverage.
- Clearing an existing signature must set the signature state back to null and keep the close action disabled; preserve `Firma.test.tsx` and close-gate assertions.
- GPS denial/unavailable coordinates and IndexedDB write failure must remain visible and prevent navigation as before; preserve `useGps` and error-save tests.
- Offline/pending/sync error labels and manual sync must remain readable in a narrow viewport without hiding failed orders; pin existing `MisOrdenes` and `App` tests.

---

### Task 1: PWA shell, status, and navigation surfaces

**Files:**
- Modify: `pwa/src/index.css`
- Modify: `pwa/src/App.tsx`
- Test: `pwa/src/App.test.tsx`

**Interfaces:**
- Consumes: existing screen stack, auth token, online status, manual Outbox sync, and navigation callbacks.
- Produces: same `App` behavior and screens with a calmer clinical palette, clear connectivity/sync state, and comfortable mobile navigation.

- [ ] **Step 1: Pin navigation and sync-visible states**

In existing App tests ensure equipo, order, stock, and local-orders navigation remain reachable; the sync button still invokes the current sync callback; online/offline status text remains present.

- [ ] **Step 2: Run focused baseline tests**

Run from `pwa`: `npm test -- --run src/App.test.tsx`.
Expected: current behavior passes before styling.

- [ ] **Step 3: Apply the field shell styling**

Set the app background and base type in `index.css`. Restyle the existing top bar with navy/blue brand context, status badges with semantic colors, content spacing and bottom navigation with safe tap sizes and active state. Keep all event handlers, screen state, `BotonSincronizar`, `BadgeConectividad`, history behavior, and routes exactly as implemented. Maintain enough bottom padding that the fixed navigation cannot cover page actions.

- [ ] **Step 4: Run App tests**

Run: `npm test -- --run src/App.test.tsx`.
Expected: PASS with status and navigation interactions unchanged.

- [ ] **Step 5: Commit the PWA shell**

Run: `git add pwa/src/index.css pwa/src/App.tsx pwa/src/App.test.tsx; git commit -m "style(pwa): refresh field navigation and status shell"`.

### Task 2: Extract and style water readings and existing parts entry

**Files:**
- Create: `pwa/src/features/orden/LecturasAguaFields.tsx`
- Create: `pwa/src/features/orden/RepuestosSection.tsx`
- Modify: `pwa/src/features/orden/OrdenForm.tsx`
- Test: `pwa/src/features/orden/OrdenForm.test.tsx`

**Interfaces:**
- Consumes: `OrdenForm` field/error/touched state and current repuesto code/count handlers.
- Produces: presentational `LecturasAguaFields` and `RepuestosSection`; no state, storage, or business logic moves out of `OrdenForm`.

- [ ] **Step 1: Pin required-reading and current-stock behavior**

Ensure the order test asserts all eight current parameter labels and error behavior; invalid reading blocks later sections/save. Assert successful repuesto consumption appears in the order list and insufficient stock shows its returned error without adding a line.

- [ ] **Step 2: Run the order test baseline**

Run: `npm test -- --run src/features/orden/OrdenForm.test.tsx`.
Expected: PASS before extraction.

- [ ] **Step 3: Extract pure reading fields**

Create `LecturasAguaFields` with props `lecturas: Record<CampoLectura,string>`, `tocado: Partial<Record<CampoLectura,boolean>>`, `errores: Record<CampoLectura,string|null>`, and `onValor(campo: CampoLectura, valor: string)` / `onTocado(campo: CampoLectura)`. Render the same eight labels and ids in two groups: quality (three TDS measures, pH, conductivity, resistivity) and production/consumption (network liters and pure-water liters). Keep each input `inputMode="decimal"`; keep helper/error copy tied to existing validation results. Style labels and inputs with large mobile targets, unit cues, clear focus, and visible error text.

- [ ] **Step 4: Extract only the repuesto presentation**

Create `RepuestosSection` with props for `codigo`, `cantidad`, `repuestos`, `error`, `onCodigoChange`, `onCantidadChange`, and `onAgregar`. Render code/count fields, an add button, current error, and the consumed list. Keep async validation, call to `consumir`, stock rejection, and state updates in `OrdenForm`; do not add checkbox state, checklist data, DB writes, or alternate flow.

- [ ] **Step 5: Wire the extracted sections to existing state**

Replace only the corresponding inline JSX in `OrdenForm` with these components. Retain `errores`, `lecturasCompletas`, `puedeCerrar`, `agregarRepuesto`, and order creation code. Style intervention choice, GPS, error save notice, signature heading, and close/cancel actions as grouped surfaces with readable semantic states.

- [ ] **Step 6: Run order tests**

Run: `npm test -- --run src/features/orden/OrdenForm.test.tsx`.
Expected: PASS for readings, stock discount, GPS/signature close gate, and failed local save.

- [ ] **Step 7: Commit order form presentation**

Run: `git add pwa/src/features/orden/LecturasAguaFields.tsx pwa/src/features/orden/RepuestosSection.tsx pwa/src/features/orden/OrdenForm.tsx pwa/src/features/orden/OrdenForm.test.tsx; git commit -m "style(pwa): group water readings and part entry"`.

### Task 3: Equipment selection, signature, stock, and local orders

**Files:**
- Modify: `pwa/src/App.tsx` (existing `EquipoPicker`)
- Modify: `pwa/src/features/orden/Firma.tsx`
- Modify: `pwa/src/features/orden/MisOrdenes.tsx`
- Modify: `pwa/src/features/stock/StockMovil.tsx`
- Test: `pwa/src/App.test.tsx`, `pwa/src/features/orden/Firma.test.tsx`, `pwa/src/features/orden/MisOrdenes.test.tsx`, `pwa/src/features/stock/StockMovil.test.tsx`

**Interfaces:**
- Consumes: existing catalog query, local orders query, stock load form, and signature callback.
- Produces: consistent visual treatment and unchanged behaviors/status representation.

- [ ] **Step 1: Pin selection, signing, and offline list states**

Ensure tests cover equipment choice callback, signature clear callback and canvas geometry/settings, pending and error local order visibility, and stock loading form submission.

- [ ] **Step 2: Run focused tests before styling**

Run: `npm test -- --run src/App.test.tsx src/features/orden/Firma.test.tsx src/features/orden/MisOrdenes.test.tsx src/features/stock/StockMovil.test.tsx`.
Expected: PASS.

- [ ] **Step 3: Restyle equipment picker without changing selection logic**

In `EquipoPicker`, retain its query, loading/error/empty conditions, and `onElegido` callback. Render equipment/contract context in touch-friendly cards with a visible series, clinic, and system-type hierarchy using only fields already present in the catalog item.

- [ ] **Step 4: Restyle signature and stock views**

In `Firma.tsx`, change only presentation classes and surrounding hint/clear button styles. Preserve `canvasProps` width 600, height 200, `data-testid`, pen color, min/max width, dot size, velocity filter, DPR comment/behavior, `onEnd` non-empty check, and clear callback. In `StockMovil.tsx`, use a grouped card, full-width inputs, clear quantity affordance and a prominent load action while preserving its exact submit validation and `cargarStockTurno` call.

- [ ] **Step 5: Restyle the local-order status list**

In `MisOrdenes.tsx`, keep the same Dexie `toArray` query and sorting. Present each order as a readable card with the existing status label; use crimson for errors and neutral/blue/emerald tones for other states. Keep `error_detalle` visible and retain the empty state.

- [ ] **Step 6: Run the focused tests**

Run the Task 3 test command.
Expected: PASS; signature settings/callbacks, stock writes, order status and equipment navigation remain unchanged.

- [ ] **Step 7: Commit supporting mobile screens**

Run: `git add pwa/src/App.tsx pwa/src/features/orden/Firma.tsx pwa/src/features/orden/MisOrdenes.tsx pwa/src/features/stock/StockMovil.tsx pwa/src/App.test.tsx pwa/src/features/orden/Firma.test.tsx pwa/src/features/orden/MisOrdenes.test.tsx pwa/src/features/stock/StockMovil.test.tsx; git commit -m "style(pwa): clarify equipment and offline order states"`.

### Task 4: PWA build and invariant review

**Files:**
- Verify: all modified `pwa/src/**` files, `pwa/src/db/dexie.ts`, `pwa/src/db/outbox.ts`, and `pwa/src/lib/validators.ts` (read-only).

- [ ] **Step 1: Run the production build**

Run from `pwa`: `npm run build`.
Expected: TypeScript and Vite build succeed.

- [ ] **Step 2: Run the PWA test suite**

Run from `pwa`: `npm test`.
Expected: all tests pass, including Dexie and Outbox tests.

- [ ] **Step 3: Review the sensitive diff**

Run `git diff -- pwa/src`; confirm the extracted components are presentation-only. Verify no changes to `dexie.ts`, `outbox.ts`, validators, order payload, `consumir`, signature canvas geometry/props, or close predicates.

- [ ] **Step 4: Commit any verified final correction**

If a build or test reveals a presentation regression, stage only the exact affected paths, for example `git add pwa/src/features/orden/OrdenForm.tsx pwa/src/features/orden/OrdenForm.test.tsx`, then run `git commit -m "fix(pwa): preserve field workflow in visual refresh"`.

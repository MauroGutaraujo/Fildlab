# Fase 3.2 — PWA de Campo (Offline-First): Diseño

**Estado:** Aprobado por el usuario en brainstorming (2026-09-21). Listo para `writing-plans`.

## 1. Propósito y alcance

Dar a los técnicos de campo una PWA que funcione 100% offline para registrar órdenes de servicio de equipos de tratamiento de agua (ósmosis inversa, ablandador, filtro), con cierre bloqueado si faltan datos obligatorios, y que sincronice de forma resiliente con la Plataforma Web Central (Fase 3.1) al recuperar conectividad.

**Cubre del EDT (`CLAUDE.md` sección 7):**
- 3.2.1 Formulario de órdenes de servicio y lectura de agua
- 3.2.2 Modo offline con IndexedDB (Dexie.js)
- 3.2.3 Servicio de sincronización Outbox con TanStack Query
- 3.2.4 Inventario móvil en dispositivo (descuento local inmediato)
- 3.2.5 Firma digital en canvas (DPR=2) y geolocalización

**No cubre (fuera de alcance de 3.2):**
- Asignación de órdenes a técnicos por Gerencia (no existe ese concepto en el esquema; el técnico crea la orden en campo).
- Asignación server-side de stock móvil por técnico (decisión: local-only en Dexie).
- Módulo BI, RUL, despliegue (Fases 4 y 3.3).

## 2. Reglas de negocio vinculantes

- **RN-02:** la PWA bloquea el cierre de cualquier orden si falta: (1) los 8 parámetros físico-químicos y volumétricos del agua, (2) firma digital manuscrita, (3) GPS + doble marca de tiempo (local y de servidor).
- **RN-03 fases 1 y 2:** al cerrar la orden (online u offline) se descuenta de inmediato el stock móvil local (Dexie). Al transmitirse a la nube, el repuesto pasa a `Comprometido` en el almacén central (ya modelado: `MovimientoInventario.tipo = 'SALIDA_ORDEN'`).
- **RN-04:** una orden sincronizada es inmutable. El backend calcula el hash SHA-256 sobre el payload crudo y lo encadena al hash de la última acta del mismo equipo.
- **REQ-06:** control y descuento del stock local del técnico en Dexie.js, con o sin conexión.
- **REQ-10/11:** registro 100% offline, sincronización bidireccional automática al detectar red, congelamiento inmutable del acta.
- **REQ-12/13:** firma con GPS y doble timestamp; bloqueo preventivo si falta algo.
- **RNF-02:** renderizado de pantallas PWA en <2s sobre Galaxy A14 (4 GB RAM).
- **RNF-04:** cero pérdida de órdenes en campo vía persistencia en cola Outbox.

## 3. Arquitectura

### 3.1 Backend — nuevo endpoint `POST /api/v1/ordenes`

Único endpoint nuevo de escritura para 3.2. Recibe la orden completa (datos de orden + acta cruda + consumo de repuestos) y la procesa en una transacción atómica, siguiendo el mismo patrón `begin_nested` que ya usan `services/ventas.py` y `services/liquidacion.py`:

1. **Validar completitud RN-02** con Pydantic: los 8 parámetros de agua, firma no vacía, GPS presente, `fecha_creacion_cliente` presente → 422 si falta cualquiera, sin persistir nada parcial.
2. **Idempotencia por UUID de cliente.** El `id` de la orden lo genera el dispositivo del técnico (no el servidor), para que el Outbox pueda reintentar sin duplicar. Si el `id` ya existe en `ordenes_servicio`, el endpoint devuelve **200 con la orden existente** (no 409, no re-procesa) — un reintento de red tras un éxito no visto por el cliente no debe fallar ni duplicar.
3. **Insertar `OrdenServicio`** en su estado por defecto, `SINCRONIZADA` (el propio esquema de la sección 6 de `CLAUDE.md` lo define como `DEFAULT 'SINCRONIZADA'`, y la Tarea 7 de 3.1 ya dejó `liquidar` aceptando `SINCRONIZADA` o `COMPROMETIDA` indistintamente). Lo que RN-03 fase 1 llama "pasan a Comprometido" describe el **repuesto**, no la orden: ese estado ya lo captura el movimiento `SALIDA_ORDEN` del paso 6, sin necesidad de tocar `ordenes_servicio.estado`.
4. **Calcular el hash encadenado:** SHA-256 sobre el `payload_raw` entrante; busca el `hash_sha256` de la acta más reciente del mismo `equipo_serie` (por `creado_en` descendente) como `previous_hash`; si no hay acta previa para ese equipo, `previous_hash = NULL`.
5. **Insertar `ActaInmutable`** con el payload, hash, previous_hash, firma, GPS.
6. **Por cada repuesto consumido**, `registrar_movimiento(session, codigo, "SALIDA_ORDEN", cantidad, tecnico_id, orden_id=...)` — función ya existente en `services/inventario.py`, sin cambios.
7. Si algún repuesto no existe o no hay stock suficiente, la transacción entera se revierte (ningún dato parcial) y el endpoint responde 404/409 — el técnico ve el error y decide (reintentar tras que Gerencia reponga stock, o Gerencia corrige después vía adenda).

**Esquema de entrada (`OrdenSincronizarIn`):**
```
id: UUID                          # generado en el dispositivo
contrato_id: int
equipo_serie: str
tecnico_id: int
tipo_intervencion: str
fecha_creacion_cliente: datetime  # timestamp local, al firmar
lecturas_agua: {
  tds_entrada_ppm, tds_post_membrana_ppm, tds_producto_final_ppm,
  ph, conductividad_us_cm, resistividad_mohm_cm,
  litros_consumidos_red, litros_agua_pura
}                                  # mismos 8 campos que ParametrosNominales de Equipos (3.1), reutilizado
firma_base64: str
gps_latitud: Decimal
gps_longitud: Decimal
repuestos_consumidos: [{repuesto_codigo, cantidad}]
```

El `payload_raw` que se hashea es el JSON serializado y determinístico (claves ordenadas) de `lecturas_agua` + metadatos de la orden — la función de serialización vive en `services/ordenes.py` y se prueba explícitamente (mismo input → mismo hash, sin importar el orden de las claves en el JSON de entrada).

### 3.2 Proyecto `pwa/`

Vite + React 18 + TypeScript + Tailwind CSS (sin shadcn/ui — prioridad al peso del bundle) + `vite-plugin-pwa` (Workbox) + Dexie.js + `@tanstack/react-query` + `react-signature-canvas`.

Estructura, en paralelo a `frontend/`:
```
pwa/
  vite.config.ts          vite-plugin-pwa: manifest, service worker, estrategia cache-first para el shell
  manifest.json
  src/
    api/client.ts         copia delgada y adaptada de frontend/src/api/client.ts (decisión A: duplicar, no compartir)
    auth/session.ts        idem — sesión de turno extendida (ver 3.5)
    db/dexie.ts            definición de la base Dexie y sus tablas
    db/catalogo.ts         refresco de catalogoLocal cuando hay red
    db/outbox.ts           lectura/escritura de ordenesLocal y el procesador de sincronización
    features/orden/        formulario de cierre de orden (parámetros, firma, GPS)
    features/stock/        pantalla de stock móvil (carga inicial de turno, descuento)
```

**Decisión (aprobada):** sin paquete compartido con `frontend/`. Solo dos apps; se reconsidera si aparece una tercera.

### 3.3 Esquema Dexie

```
catalogoLocal:      { tipo: 'cliente'|'equipo'|'contrato', id, datos, actualizado_en }
ordenesLocal:       { id (uuid local = id servidor), ...todos los campos de OrdenSincronizarIn,
                       estado_sync: 'borrador'|'pendiente'|'sincronizando'|'sincronizada'|'error',
                       error_detalle?, creado_en_local, intentos_sync }
stockMovilLocal:    { repuesto_codigo, cantidad_cargada, cantidad_consumida, turno_id }
```

`ordenesLocal` filtrada por `estado_sync='pendiente'` **es** el Outbox — no hay tabla de cola separada. Esto evita mantener dos fuentes de verdad sobre la misma orden.

**Stock móvil (decisión aprobada — local-only):** al iniciar turno, el técnico registra manualmente cuánto cargó de cada repuesto (`cantidad_cargada`). Cerrar una orden con consumo de repuestos incrementa `cantidad_consumida` de inmediato (RN-03 fase 1), bloqueando el cierre si `cantidad_consumida + solicitado > cantidad_cargada` para ese repuesto (evita que el técnico registre más de lo que físicamente tiene). Al sincronizar la orden, el consumo ya registrado en Dexie no cambia — solo dispara el `SALIDA_ORDEN` real contra el almacén central vía el paso 6 del endpoint.

### 3.4 Flujo de cierre de orden (3.2.1, 3.2.5)

1. Técnico busca cliente → equipo desde `catalogoLocal` (funciona offline: el catálogo se refresca cada vez que hay red, vía `refetchOnReconnect`).
2. Completa tipo de intervención + los 8 campos de `lecturas_agua` (mismos tipos/rangos que `ParametrosNominales` del backend: no-negativos, pH 0-14).
3. Selecciona repuestos consumidos contra `stockMovilLocal` (bloqueo si excede lo cargado).
4. Firma en canvas (`react-signature-canvas`, `dotSize` y `minWidth`/`maxWidth` fijados para una densidad de píxeles DPR=2 constante, sin escalar con el dispositivo — evita canvases de memoria variable en distintos teléfonos).
5. Captura GPS (`navigator.geolocation.getCurrentPosition`); si el permiso se niega, el botón de cierre queda bloqueado con el motivo visible.
6. Botón **Cerrar orden** solo se habilita cuando los tres bloques (lecturas, firma, GPS) están completos — validado en el cliente (mismas reglas que el backend, para feedback inmediato) y re-validado por el backend al sincronizar (fuente de verdad).
7. Al cerrar: se escribe en `ordenesLocal` con `estado_sync='pendiente'` y `fecha_creacion_cliente = now()`. La orden queda de solo lectura en la UI (coherente con RN-04: una vez firmada, no se edita ni siquiera localmente).

### 3.5 Sesión de turno extendida (offline)

El JWT normal expira en 60 min (config actual del backend, sin cambios). Para que un técnico sin señal complete un turno de 12 horas:
- Al hacer login **con conectividad**, la PWA solicita el token normal y lo guarda junto a un timestamp de "inicio de turno" en IndexedDB (no en `sessionStorage`, que no sobrevive service worker/reinicio de pestaña en un PWA instalada).
- La PWA seguirá usando ese JWT para las llamadas de sincronización; si el token expira (60 min) mientras hay señal, se refresca silenciosamente reautenticando con las credenciales cacheadas **solo si el usuario optó por "recordar sesión de turno"** — evita guardar la contraseña en claro: en su lugar, el login de turno emite un JWT de vida larga (`jwt_expire_min` configurable por endpoint, o un segundo tipo de token `turno`) válido 12 horas, distinto del JWT de 60 min que sigue usando el panel administrativo.
- **Diseño del backend:** `POST /api/v1/auth/login` acepta un parámetro opcional `duracion: "normal" | "turno"`; con `"turno"` emite un JWT de 12 horas. Sin conectividad, ese JWT ya cacheado sigue siendo válido para las llamadas de sincronización en cuanto vuelva la señal, sin pedir credenciales de nuevo.
- Este JWT de turno **no** amplía privilegios (sigue siendo `rol=TECNICO`, sigue pasando por `require_role`); solo cambia su tiempo de vida.

### 3.6 Sincronización — Outbox (3.2.3)

- Un listener de `window.addEventListener('online', ...)` y un intervalo corto de respaldo (por si el evento `online` no dispara, común en Android) llaman a `procesarOutbox()`.
- `procesarOutbox()` itera `ordenesLocal` con `estado_sync='pendiente'`, en orden de `creado_en_local`, y por cada una hace `POST /api/v1/ordenes` vía una `useMutation` de TanStack Query:
  - Éxito (200/201) → `estado_sync='sincronizada'`.
  - Error de validación (422/404/409 de negocio, p. ej. stock insuficiente) → `estado_sync='error'`, `error_detalle` guardado, visible para que el técnico o Gerencia decidan (no se reintenta solo, RNF-04: nunca se pierde, pero tampoco se reintenta a ciegas un error de negocio).
  - Error de red (sin respuesta) → permanece `pendiente`, se reintenta en el próximo ciclo.
- Procesamiento secuencial (no paralelo): evita que dos órdenes del mismo equipo lleguen fuera de orden y rompan el encadenado de hash (que depende del orden de llegada al backend).

## 4. Componentes y responsabilidades

| Componente | Responsabilidad | Depende de |
|---|---|---|
| `services/ordenes.py` (backend) | Validar, encadenar hash, insertar orden+acta+movimientos en una transacción; idempotencia por UUID | `services/inventario.registrar_movimiento` |
| `db/dexie.ts` | Definición de tablas y versión del esquema Dexie | — |
| `db/catalogo.ts` | Refrescar `catalogoLocal` cuando hay red | `api/client.ts` |
| `db/outbox.ts` | Leer/escribir `ordenesLocal`, procesar la cola de sincronización | `db/dexie.ts`, `api/client.ts` |
| `features/orden/OrdenForm` | Formulario de cierre, las 3 validaciones bloqueantes | `db/outbox.ts`, `features/stock` |
| `features/stock/StockMovil` | Carga de turno y descuento local | `db/dexie.ts` |
| `auth/session.ts` (pwa) | JWT de turno de 12h en IndexedDB | `api/client.ts` |

## 5. Manejo de errores

- **Backend:** cualquier fallo dentro de la transacción de `POST /ordenes` revierte todo (ya es el patrón establecido); el handler global de `IntegrityError` (agregado en la revisión final de 3.1) sigue cubriendo condiciones de carrera imprevistas.
- **PWA offline:** ningún error de red bloquea al técnico — la orden queda en Dexie con `estado_sync='pendiente'` y se reintenta sola. Un error de negocio (422/404/409) sí requiere decisión humana y se muestra explícitamente, nunca se descarta.
- **Firma/GPS ausentes:** bloqueo puramente de UI (botón deshabilitado + mensaje), reforzado por la validación del backend al sincronizar.

## 6. Pruebas

- **Backend (pytest):** hash determinístico y encadenado (mismo payload → mismo hash; segunda acta del mismo equipo encadena con la primera); RN-02 rechaza payload incompleto (422, por cada campo faltante); idempotencia (mismo UUID dos veces → 200 ambas veces, una sola fila en `ordenes_servicio`/`actas_inmutables`); stock insuficiente revierte toda la transacción (ninguna orden, acta ni movimiento parcial); login con `duracion="turno"` emite un JWT de 12h, sin `duracion` sigue siendo 60 min.
- **PWA (vitest + Testing Library + `fake-indexeddb`):** el botón de cierre permanece deshabilitado hasta completar los 3 bloques; el stock móvil local bloquea un consumo que excede lo cargado; `procesarOutbox` marca `sincronizada` en éxito, `error` en fallo de negocio, y deja `pendiente` en fallo de red; el catálogo local sirve búsquedas sin red.

## 7. Puntos abiertos que este spec resuelve explícitamente (para que el plan no improvise)

- Sin tabla de asignación técnico↔orden: el técnico crea la orden, no la recibe pre-asignada.
- Stock móvil 100% local (Dexie), sin contrapartida en el servidor hasta la sincronización.
- Sin shadcn/ui en la PWA.
- Sin paquete compartido `frontend/`↔`pwa/`: duplicación deliberada del código delgado de auth/api.
- Un solo endpoint nuevo de escritura: `POST /api/v1/ordenes`, idempotente por UUID de cliente.

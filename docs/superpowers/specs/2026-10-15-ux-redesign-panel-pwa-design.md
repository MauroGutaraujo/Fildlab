# Rediseño UI del panel web y la PWA de campo

Fecha: 2026-10-15

## Objetivo

Modernizar la experiencia visual del panel administrativo web y de la PWA móvil de Fildlab, tomando las capturas como referencias de jerarquía y distribución y adaptándolas al trabajo de tratamiento y purificación de agua en clínicas y laboratorios.

## Decisiones aprobadas

- Implementar estilos con Tailwind CSS ya instalado. No añadir shadcn/ui ni dependencias visuales.
- Usar azules limpios y profundos, fondos slate/zinc claros y estados esmeralda, ámbar y carmesí.
- Mantener los datos, rutas, operaciones y reglas funcionales existentes.
- En la PWA no cambiar esquema Dexie, Outbox ni payloads de sincronización. Mejorar la presentación de lecturas, intervención y selección/descuento de repuestos existentes; no agregar checklist persistido de filtros.
- Preservar firma existente, validación del cierre y sus dimensiones/configuración de canvas.
- Mantener ECharts reactivo en cliente y los datos servidos por TanStack Query.
- Trabajar en `feature/ux-redesign-panel-pwa` dentro de un worktree, dejando intacto el checkout `main` con sus cambios locales.

## Alcance de interfaz

### Panel web

Refinar el marco de navegación y el contenedor de contenido para establecer jerarquía y contexto de módulo. Alinear títulos, espaciado, superficies y estados de formularios y tablas a una estética clínica limpia. Dar prioridad a contratos y auditoría, SLA, liquidación de órdenes sincronizadas, e inventario/vida útil de equipos y mantenimiento preventivo. Reutilizar los componentes y consultas existentes; presentar vacíos, carga, error y éxito con los estados semánticos de la paleta.

### PWA de campo

Mantener navegación móvil persistente y optimizarla para uso táctil. Organizar la captura de los ocho parámetros existentes —TDS de entrada, post-membrana y producto final; pH; conductividad; resistividad; litros de red y litros de agua pura— en grupos legibles. Dar contexto al equipo e intervención. Hacer más clara la selección y el descuento actual de repuestos, así como la ubicación, firma y cierre. Los campos obligatorios y el bloqueo de orden incompleta continúan bajo las validaciones actuales.

## Arquitectura y límites técnicos

El rediseño se limitará a componentes React y clases Tailwind en las dos apps. No se instalarán paquetes ni se cambiarán backend, esquemas, rutas, llamadas API, estructuras de datos, permisos de acceso, lógica de negocio o estrategias de sincronización. Dexie y el Outbox seguirán siendo la fuente y el mecanismo locales actuales. La firma continuará usando `react-signature-canvas` con configuración DPR=2, ancho/alto actuales y validación de firma no vacía. Los gráficos BI conservarán el componente de ECharts para React con consultas reactivas.

## Validación prevista

Ejecutar `npm run build` en `frontend` y `pwa`, que incluye `tsc --noEmit` y el build de Vite. Ejecutar las pruebas existentes relevantes de componentes para comprobar interacciones, estados de formularios y preservación de flujos si el plan lo requiere. Revisar el diff para confirmar que no hay cambios en DB, sincronización, firma o contratos funcionales.

## Fuera de alcance

- Añadir shadcn/ui u otras dependencias.
- Agregar checklist persistido de filtros o alterar el modelo de orden.
- Cambiar integración offline, Outbox, firma, validación o datos reactivos de BI.
- Convertir datos operativos en métricas estáticas de demostración.

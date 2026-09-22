# CLAUDE.md - CONTEXTO MAESTRO DEL PROYECTO
## SISTEMA DE HABILIDADES (SUPERPOWERS SKILLS)
Tienes a tu disposición una biblioteca de habilidades operativas en el directorio `.agents/skills/`.
La habilidad maestra que orquesta este sistema está en `.agents/skills/using-superpowers/SKILL.md`.

Antes de realizar cualquiera de las siguientes actividades, DEBES leer el archivo `SKILL.md` respectivo y ejecutar rigurosamente sus directivas:

- **Planificación de tareas y arquitectura:** `.agents/skills/writing-plans/SKILL.md` y `.agents/skills/brainstorming/SKILL.md`
- **Desarrollo por sub-agentes o tareas paralelas:** `.agents/skills/subagent-driven-development/SKILL.md` y `.agents/skills/dispatching-parallel-agents/SKILL.md`
- **Ejecución de planes de código:** `.agents/skills/executing-plans/SKILL.md`
- **Desarrollo guiado por pruebas (TDD):** `.agents/skills/test-driven-development/SKILL.md`
- **Diagnóstico y solución de errores/bugs:** `.agents/skills/systematic-debugging/SKILL.md`
- **Revisión de código:** `.agents/skills/requesting-code-review/SKILL.md` y `.agents/skills/receiving-code-review/SKILL.md`
- **Verificación previa a finalizar tareas:** `.agents/skills/verification-before-completion/SKILL.md`
- **Gestión de ramas y ramas de trabajo en Git:** `.agents/skills/using-git-worktrees/SKILL.md` y `.agents/skills/finishing-a-development-branch/SKILL.md`

REGLA OBLIGATORIA: Si el usuario o el flujo de trabajo requiere una de estas metodologías, utiliza tu herramienta de lectura de archivos para cargar el `SKILL.md` correspondiente antes de escribir o modificar código.

## 1. IDENTIFICACIÓN Y GENERALIDADES DEL PROYECTO
- **Código del Proyecto:** SI_FILDLAB-2026[cite: 1, 2, 3].
- **Título Oficial:** Sistema de Información para la gestión integral de equipos de tratamiento de agua en la empresa Fildlab Perú S.A.C.[cite: 1, 2, 3].
- **Empresa Cliente:** Fildlab Perú S.A.C. (RUC: 20612493821), ubicada en Trujillo, Perú[cite: 2, 6, 7]. Rubro: Tratamiento y purificación de agua orientado al sector salud (clínicas y laboratorios)[cite: 2].
- **Patrocinador / Sponsor:** Elva Acevedo Vargas (Gerente General)[cite: 1, 2, 3].
- **Líder de Proyecto:** José Mauro Gutierrez Araujo[cite: 1, 2, 3].
- **Equipo de Ingeniería:** Jorge Stevie Espejo Mogollón (Fullstack Dev), Deyvid Xander Gamboa Alva (Data & QA)[cite: 1, 2].
- **Marco Institucional:** Proyecto de Capstone (16 semanas)[cite: 1, 2], Universidad Privada del Norte[cite: 2, 6].

---

## 2. PROBLEMA, OBJETIVOS Y METAS DE NEGOCIO
- **Situación Actual:** Gestión desarticulada y manual basada en hojas de cálculo (Excel) y actas físicas en papel[cite: 2]. Esto ocasiona multas por incumplimiento de Acuerdos de Nivel de Servicio (SLA)[cite: 1, 2], desfase de 24 a 48 horas en la actualización del inventario de consumibles[cite: 1, 2, 3], demoras de 3 a 5 días para auditar la rentabilidad de contratos[cite: 1, 2, 3] y un modelo operativo puramente reactivo ante averías de equipos de ósmosis y filtración[cite: 1, 2].
- **Objetivos y Metas (KPIs):**
  1. *Cumplimiento de SLA:* Reducir los mantenimientos fuera de tiempo de respuesta a menos del 2% (erradicación de penalizaciones comerciales)[cite: 1, 2, 3].
  2. *Auditoría de Rentabilidad:* Automatizar y obtener de forma inmediata el cálculo del margen de ganancia real cruzando ingresos contractuales vs. consumibles y horas en campo[cite: 1, 2, 3].
  3. *Trazabilidad de Inventario:* Descuento inmediato del stock móvil en campo y sincronización con el almacén central en < 5 minutos al recuperar conectividad.
  4. *Mantenimiento Predictivo:* Elevar las intervenciones preventivas planificadas al 90% utilizando un modelo predictivo de Vida Útil Remanente (RUL)[cite: 1, 2, 3].
  5. *Cierre en Campo:* 0% de reportes con datos incompletos o sin firma mediante validación forzosa en la PWA.

---

## 3. ARQUITECTURA TÉCNICA Y STACK OBLIGATORIO
La solución se estructura bajo una política de presupuesto de infraestructura y licencias de S/. 0.00 (Free Tier / Open Source)[cite: 1, 2, 3]:

- **Frontend (Web y PWA):**
  - Framework: React 18+ con TypeScript y Vite.
  - Modo Offline: Service Workers con `vite-plugin-pwa` (Workbox)[cite: 2, 3].
  - Persistencia Local: IndexedDB gestionado con `Dexie.js`[cite: 2, 3].
  - Sincronización Resiliente: Patrón Outbox orquestado con `@tanstack/react-query`[cite: 2, 3].
  - Firma Electrónica: `react-signature-canvas` fijado a una densidad de píxeles DPR = 2 para no saturar memoria ni generar payloads pesados.
  - Estilos y Componentes: Tailwind CSS con componentes shadcn/ui.
  - Alojamiento Web: Cloudflare Pages (distribución CDN global y HTTPS/TLS 1.3)[cite: 2, 3].

- **Backend (API REST):**
  - Entorno y Lenguaje: Python 3.12 con FastAPI (arquitectura monolítica asíncrona)[cite: 2, 3].
  - Validación de Esquemas: Pydantic v2.
  - Criptografía y Seguridad: Autenticación RBAC con JWT; derivación de contraseñas con Argon2 (parámetros OWASP); validación de integridad con SHA-256 para actas[cite: 2, 3].
  - Alojamiento API: Contenedor Docker en Render, free tier (Límites: 512 MB de RAM, 0.1 vCPU)[cite: 2, 3]. Requiere endpoint liviano `/api/v1/healthz` para mitigar el arranque en frío (cold start, agravado en el free tier de Render por el spin-down tras 15 min de inactividad) mediante healthchecks periódicos[cite: 2, 3].

- **Base de Datos Central:**
  - Motor: PostgreSQL serverless en Neon (conexión directa, connection pooling conservador)[cite: 2, 3].
  - Registro Inmutable: Almacenamiento de payloads de actas en formato de texto crudo (`TEXT`) con hashes encadenados para garantizar auditoría legal[cite: 2, 3].

- **Módulo de Inteligencia de Negocios (BI):**
  - Motor: Apache ECharts renderizado nativamente del lado del cliente (*Client-Side Rendering*) en el navegador para no consumir la memoria del contenedor backend[cite: 2, 3].

- **Módulo de Inteligencia Artificial (Mantenimiento Predictivo / RUL):**
  - Librerías: `scikit-learn` y `lifelines` (Análisis de Supervivencia: curvas Kaplan-Meier y modelos de Cox)[cite: 2, 3].
  - Ejecución: **Aislada totalmente de la API transaccional**[cite: 2, 3]. Corre como rutina batch programada (GitHub Actions / script independiente) que actualiza la tabla de predicciones en Neon para evitar sobrecarga de RAM[cite: 2, 3].

- **Hardware Corporativo Asignado:**
  - Terminal Administrativa: Laptop HP ProBook 450 G9 (Intel Core i5, 8 GB RAM, SSD 512 GB) encargada de compilar PDFs y renderizar analítica en el cliente[cite: 1, 2, 3].
  - Terminal de Campo: Smartphones Samsung Galaxy A14 (Android 12, 4 GB RAM, 64 GB almacenamiento, 4G, GPS) encargados del hashing SHA-256 local y la captura en canvas[cite: 1, 2, 3].
  - Contingencia Física: Impresora Epson EcoTank L3250 (solo para emisión en papel si una clínica lo exige de forma excepcional)[cite: 1, 2, 3].

---

## 4. REGLAS DE NEGOCIO CRÍTICAS (SRS)
- **RN-01 (Jerarquía de Aprobación):** Privilegio exclusivo de la Gerencia General para crear, actualizar o anular clientes, contratos y configuración de SLAs. Los operarios de campo tienen privilegios estrictos de solo lectura sobre estas entidades[cite: 3].
- **RN-02 (Cierre Obligatorio de Órdenes en Campo):** La PWA bloquea el cierre de cualquier orden técnica si no se cuenta con:
  1. Lectura obligatoria de parámetros físico-químicos y volumétricos del agua:
     - Sólidos disueltos del agua de entrada (TDS Entrada - ppm / mg/L)[cite: 3].
     - Sólidos disueltos post membrana (TDS Post-Membrana - ppm / mg/L)[cite: 3].
     - Sólidos disueltos de producto final (TDS Producto Final - ppm / mg/L)[cite: 3].
     - pH (acidez/alcalinidad)[cite: 3].
     - Conductividad eléctrica (μS/cm)[cite: 3].
     - Resistividad (MΩ·cm)[cite: 3].
     - Litros consumidos de la red (agua cruda de entrada)[cite: 3].
     - Litros totales de agua pura (agua permeada / tratada)[cite: 3].
  2. Firma digital manuscrita capturada en pantalla táctil[cite: 3].
  3. Metadatos de validación: coordenadas GPS (latitud/longitud) y doble marca de tiempo (estampado local y del servidor)[cite: 3].
- **RN-03 (Trazabilidad de Inventario en Dos Fases):**
  - *Fase 1 (En campo):* Al cerrar la orden en la PWA (online u offline), se rebaja inmediatamente el stock del almacén móvil local en `Dexie.js`[cite: 3]. Al transmitirse a la nube, los repuestos pasan a estado `Comprometido` en el almacén central[cite: 3].
  - *Fase 2 (Liquidación):* La Gerencia General audita la orden en la plataforma web y cambia su estado a `Liquidada`, consolidando la baja contable definitiva en Neon[cite: 3].
- **RN-04 (Inmutabilidad de Registros y Ley N° 27269):**
  - Una orden firmada y sincronizada se vuelve inmutable y de solo lectura para el técnico[cite: 3].
  - El backend recalcula el hash SHA-256 sobre el payload crudo entrante y lo enlaza al hash de la última acta del equipo (tamper-evident ledger)[cite: 2, 3].
  - Ante cualquier discrepancia en consumibles, la Gerencia no edita el acta firmada; emite una «Nota Administrativa de Corrección / Adenda» vinculada a la orden para salvaguardar el no repudio y la eficacia probatoria legal[cite: 3].

---

## 5. CATÁLOGO DE REQUERIMIENTOS DEL SISTEMA

### Requerimientos Funcionales (RF)
- **REQ-01:** Registro, actualización y consulta de clientes con validación estricta de RUC (11 dígitos)[cite: 3].
- **REQ-02:** Gestión de contratos de servicio asociando vigencias y tiempos de respuesta de SLA[cite: 3].
- **REQ-03:** Ficha técnica de equipos de tratamiento de agua (serie, tipo: ósmosis inversa, ablandador o filtro, fecha de instalación y parámetros nominales de referencia: TDS entrada, TDS post-membrana, TDS producto final, pH, conductividad, resistividad, litros consumidos y litros de agua pura)[cite: 3].
- **REQ-04:** Manejo de excepciones y bloqueo ante contratos o formularios incompletos[cite: 3].
- **REQ-05:** Registro de entradas y salidas de repuestos asociadas obligatoriamente a órdenes de trabajo[cite: 3].
- **REQ-06:** Control y descuento del stock local del técnico en Dexie.js con o sin conexión[cite: 3].
- **REQ-07:** Sincronización diferida pasando consumibles al estado `Comprometido / En Tránsito`[cite: 3].
- **REQ-08:** Interfaz web de liquidación administrativa gerencial para baja contable definitiva[cite: 3].
- **REQ-09:** Emisión de notas de corrección / adendas administrativas vinculadas al acta original[cite: 3].
- **REQ-10:** Registro operativo 100% offline de órdenes en la PWA (IndexedDB)[cite: 3].
- **REQ-11:** Sincronización bidireccional automática al detectar red y congelamiento inmutable del acta[cite: 3].
- **REQ-12:** Captura de firma manuscrita digital en canvas con GPS y marcas de tiempo (Ley N° 27269)[cite: 3].
- **REQ-13:** Bloqueo preventivo de guardado si faltan firma o parámetros técnicos obligatorios[cite: 3].
- **REQ-14:** Módulo BI para el cálculo automatizado del margen de ganancia real por contrato[cite: 3].
- **REQ-15:** Indicadores visuales y alertas automáticas cuando un servicio excede el tiempo de SLA[cite: 3].
- **REQ-16:** Mensaje explícito «Sin datos disponibles para el periodo» en gráficos BI vacíos[cite: 3].
- **REQ-17:** Inferencia de Vida Útil Remanente (RUL) mediante modelos de supervivencia con historial de mantenimiento[cite: 3].
- **REQ-18:** Notificación de alertas preventivas ante riesgo de falla crítica en equipos clínicos[cite: 3].
- **REQ-19:** Tolerancia a anomalías: omisión de inferencia y registro en log ante parámetros físicos imposibles[cite: 3].

### Requerimientos No Funcionales (RNF)
- **RNF-01 (Tiempos de Respuesta):** Renderizado < 3 s en web y BI en estado activo (*warm*); tolerancia a cold starts con indicador visual no bloqueante y ping preventivo[cite: 3].
- **RNF-02 (Rendimiento Móvil):** Renderizado de pantallas PWA en < 2 s sobre smartphones Samsung Galaxy A14[cite: 2, 3].
- **RNF-03 (Disponibilidad):** 95% - 98% en horario comercial; mitigación de caídas mediante autonomía total en IndexedDB[cite: 3].
- **RNF-04 (Confiabilidad):** Cero pérdida de órdenes técnicas en campo gracias a la persistencia en cola Outbox[cite: 3].
- **RNF-05 (Seguridad en Tránsito):** Cifrado estricto de extremo a extremo con HTTPS y TLS 1.3[cite: 3].
- **RNF-06 (Privacidad de Datos):** Apego estricto a la Ley N° 29733 (Protección de Datos Personales del Perú)[cite: 2, 3].
- **RNF-07 (Mantenibilidad y Licenciamiento):** S/. 0.00 en licencias privativas; 100% tecnologías de código abierto[cite: 1, 3].
- **RNF-08 (Portabilidad):** Interfaz responsiva validada para la laptop de gerencia y móviles de campo[cite: 3].

---

## 6. ESQUEMA DE DATOS Y PERSISTENCIA

### Neon PostgreSQL (Backend)
```sql
-- Principales tablas referenciales
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Argon2
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('GERENCIA', 'TECNICO'))
);

CREATE TABLE clientes (
    ruc VARCHAR(11) PRIMARY KEY CHECK (LENGTH(ruc) = 11),
    razon_social VARCHAR(150) NOT NULL,
    direccion TEXT NOT NULL
);

CREATE TABLE contratos (
    id SERIAL PRIMARY KEY,
    cliente_ruc VARCHAR(11) REFERENCES clientes(ruc),
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    monto_mensual_soles NUMERIC(10, 2) NOT NULL,
    sla_horas_max_respuesta INT NOT NULL DEFAULT 4,
    estado VARCHAR(20) DEFAULT 'ACTIVO'
);

CREATE TABLE equipos (
    serie VARCHAR(50) PRIMARY KEY,
    cliente_ruc VARCHAR(11) REFERENCES clientes(ruc),
    contrato_id INT REFERENCES contratos(id),
    tipo_sistema VARCHAR(50) NOT NULL,
    fecha_instalacion DATE NOT NULL,
    parametros_nominales JSONB NOT NULL
);

CREATE TABLE repuestos (
    codigo VARCHAR(30) PRIMARY KEY,
    descripcion VARCHAR(150) NOT NULL,
    stock_almacen_central INT NOT NULL DEFAULT 0,
    costo_unitario_soles NUMERIC(10, 2) NOT NULL
);

CREATE TABLE ordenes_servicio (
    id UUID PRIMARY KEY,
    contrato_id INT REFERENCES contratos(id),
    equipo_serie VARCHAR(50) REFERENCES equipos(serie),
    tecnico_id INT REFERENCES usuarios(id),
    tipo_intervencion VARCHAR(30) NOT NULL,
    estado VARCHAR(20) DEFAULT 'SINCRONIZADA' CHECK (estado IN ('SINCRONIZADA', 'COMPROMETIDA', 'LIQUIDADA')),
    fecha_creacion_cliente TIMESTAMPTZ NOT NULL,
    fecha_sincronizacion TIMESTAMPTZ DEFAULT NOW(),
    tiempo_respuesta_horas NUMERIC(5,2)
);

CREATE TABLE actas_inmutables (
    id SERIAL PRIMARY KEY,
    orden_id UUID UNIQUE REFERENCES ordenes_servicio(id),
    payload_raw TEXT NOT NULL,
    hash_sha256 VARCHAR(64) NOT NULL,
    previous_hash VARCHAR(64),
    firma_base64 TEXT NOT NULL,
    gps_latitud NUMERIC(10, 7) NOT NULL,
    gps_longitud NUMERIC(10, 7) NOT NULL,
    creado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE adendas_correccion (
    id SERIAL PRIMARY KEY,
    orden_id UUID REFERENCES ordenes_servicio(id),
    gerente_id INT REFERENCES usuarios(id),
    observacion TEXT NOT NULL,
    ajuste_repuestos JSONB,
    fecha_adenda TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE predicciones_rul (
    equipo_serie VARCHAR(50) PRIMARY KEY REFERENCES equipos(serie),
    dias_vida_util_remanente INT,
    nivel_alerta VARCHAR(20) CHECK (nivel_alerta IN ('VERDE', 'AMARILLO', 'ROJO')),
    actualizado_en TIMESTAMPTZ DEFAULT NOW()
);

## 7. CHECKLIST DE IMPLEMENTACIÓN BASADO EN LA EDT

- [ ] **Fase 3: Núcleo Transaccional**
  - [x] 3.1 Plataforma Web Central
    - [x] 3.1.1 Módulo de clientes (Validación RUC de 11 dígitos)
    - [x] 3.1.2 Módulo de contratos y configuración SLA
    - [x] 3.1.3 Módulo de ventas
    - [x] 3.1.4 Módulo de inventario (Stock central y movimientos)
    - [x] 3.1.5 Módulo de equipos (Ficha técnica y series)
    - [x] 3.1.6 Liquidación de órdenes y notas de corrección (Adendas)
    - [x] 3.1.7 Control de accesos RBAC (Argon2 + JWT)
  - [x] 3.2 PWA de Campo (Offline-First)
    - [x] 3.2.1 Formulario de órdenes de servicio y lectura de agua (TDS entrada/post-membrana/producto, pH, conductividad, resistividad, litros red y litros agua pura)
    - [x] 3.2.2 Implementar modo offline con IndexedDB (Dexie.js)
    - [x] 3.2.3 Servicio de sincronización Outbox con TanStack Query
    - [x] 3.2.4 Inventario móvil en dispositivo (Descuento local inmediato)
    - [x] 3.2.5 Módulo de firma digital en canvas (DPR=2) y geolocalización
  - [ ] 3.3 Despliegue del Sistema (Free Tier)
    - [ ] 3.3.1 Configuración de Neon PostgreSQL
    - [ ] 3.3.2 Publicar API en Render con Dockerfile optimizado
    - [ ] 3.3.3 Publicar PWA en Cloudflare Pages

- [ ] **Fase 4: Integración Analítica y Pruebas**
  - [ ] 4.1 Módulo de Business Intelligence (Apache ECharts)
    - [ ] 4.1.1 Tablero de rentabilidad financiera por contrato
    - [ ] 4.1.2 Tablero de seguimiento y alertas de SLA (< 2%)
  - [ ] 4.2 Módulo de Inteligencia Artificial (RUL y Supervivencia)
    - [ ] 4.2.1 Preparación y depuración de historiales técnicos
    - [ ] 4.2.2 Pipeline de supervivencia (lifelines / Cox PH)
    - [ ] 4.2.3 Aislamiento batch en GitHub Actions hacia tabla predicciones
    - [ ] 4.2.4 Visualización de alertas de falla crítica en web
  - [ ] 4.3 Verificación de Calidad
    - [ ] 4.3.1 Pruebas unitarias backend (pytest) y frontend (vitest)
    - [ ] 4.3.2 Evaluación de atributos de calidad ISO/IEC 25010



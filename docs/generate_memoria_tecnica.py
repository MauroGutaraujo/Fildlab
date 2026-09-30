import zipfile
import xml.sax.saxutils as saxutils

def escape(t):
    return saxutils.escape(str(t))

def p(text="", bold=False, italic=False, color="000000", sz=20, align="left", space_after=80, space_before=0):
    lines = str(text).split('\n')
    out = []
    for line in lines:
        out.append('<w:p>')
        pPr = ['<w:pPr>']
        if align != "left":
            pPr.append(f'<w:jc w:val="{align}"/>')
        if space_after != 0 or space_before != 0:
            pPr.append(f'<w:spacing w:after="{space_after}" w:before="{space_before}"/>')
        pPr.append('</w:pPr>')
        out.append(''.join(pPr))
        
        out.append('<w:r>')
        rPr = ['<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>']
        if bold:
            rPr.append('<w:b/>')
        if italic:
            rPr.append('<w:i/>')
        rPr.append(f'<w:color w:val="{color}"/>')
        rPr.append(f'<w:sz w:val="{sz}"/>')
        rPr.append('</w:rPr>')
        out.append(''.join(rPr))
        out.append(f'<w:t>{escape(line)}</w:t>')
        out.append('</w:r></w:p>')
    return ''.join(out)

def tc(text, width=2000, fill=None, bold=False, align="left", color="000000", sz=18):
    lines = str(text).split('\n')
    out = ['<w:tc>']
    tcPr = [f'<w:tcPr><w:tcW w:type="dxa" w:w="{width}"/>']
    if fill:
        tcPr.append(f'<w:shd w:fill="{fill}"/>')
    tcPr.append('<w:tcMar><w:top w:w="100" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/><w:left w:w="120" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>')
    tcPr.append('</w:tcPr>')
    out.append(''.join(tcPr))
    
    for line in lines:
        out.append('<w:p>')
        if align != "left":
            out.append(f'<w:pPr><w:jc w:val="{align}"/></w:pPr>')
        out.append('<w:r>')
        rPr = ['<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>']
        if bold:
            rPr.append('<w:b/>')
        rPr.append(f'<w:color w:val="{color}"/><w:sz w:val="{sz}"/></w:rPr>')
        out.append(''.join(rPr))
        out.append(f'<w:t>{escape(line)}</w:t>')
        out.append('</w:r></w:p>')
    out.append('</w:tc>')
    return ''.join(out)

def create_table(rows_data, col_widths, borders="B0C4DE"):
    out = ['<w:tbl>']
    out.append(f'<w:tblPr><w:tblW w:type="auto" w:w="0"/><w:jc w:val="center"/><w:tblLayout w:type="fixed"/><w:tblBorders><w:top w:val="single" w:sz="6" w:space="0" w:color="{borders}"/><w:left w:val="single" w:sz="6" w:space="0" w:color="{borders}"/><w:bottom w:val="single" w:sz="6" w:space="0" w:color="{borders}"/><w:right w:val="single" w:sz="6" w:space="0" w:color="{borders}"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="DCDCDC"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="DCDCDC"/></w:tblBorders></w:tblPr>')
    
    out.append('<w:tblGrid>')
    for w in col_widths:
        out.append(f'<w:gridCol w:w="{w}"/>')
    out.append('</w:tblGrid>')
    
    for row in rows_data:
        out.append('<w:tr>')
        for cell in row:
            out.append(cell)
        out.append('</w:tr>')
    out.append('</w:tbl>')
    out.append('<w:p><w:pPr><w:spacing w:after="100"/></w:pPr></w:p>')
    return ''.join(out)

def build_full_technical_report():
    src_docx = 'docs/Sprint_1_Scrum_Kanban_Fildlab.docx'
    dst_docx = 'docs/Memoria_Tecnica_Software_Fildlab.docx'
    
    with zipfile.ZipFile(src_docx, 'r') as zin:
        all_files = {name: zin.read(name) for name in zin.namelist()}
        
    body = []
    
    # Portada
    body.append(p("FILDLAB PERÚ S.A.C.", bold=True, color="1F497D", sz=28, align="center", space_after=60, space_before=200))
    body.append(p("TRUJILLO – LA LIBERTAD | SECTOR SALUD Y TRATAMIENTO DE AGUA", bold=True, color="46505F", sz=18, align="center", space_after=140))
    body.append(p("MEMORIA TÉCNICA Y ARQUITECTÓNICA DEL SOFTWARE", bold=True, color="0F2043", sz=32, align="center", space_after=80))
    body.append(p("SISTEMA DE INFORMACIÓN PARA LA GESTIÓN INTEGRAL DE EQUIPOS DE TRATAMIENTO DE AGUA EN LA EMPRESA FILDLAB PERÚ S.A.C.", bold=True, color="1F497D", sz=22, align="center", space_after=160))
    body.append(p("Proyecto de Ingeniería de Software (Capstone) – 16 Semanas", italic=True, color="555555", sz=20, align="center", space_after=240))
    
    # Ficha de identificación
    body.append(p("FICHA DE IDENTIFICACIÓN DEL PROYECTO", bold=True, color="1F497D", sz=22, space_after=60))
    ficha_rows = [
        [tc("Código del Proyecto", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("SI_FILDLAB-2026", 9500)],
        [tc("Empresa Cliente", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("Fildlab Perú S.A.C. (RUC: 20612493821) – Trujillo, Perú", 9500)],
        [tc("Rubro de la Empresa", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("Purificación y tratamiento de agua industrial orientado al sector salud (clínicas, hospitales y hemodiálisis)", 9500)],
        [tc("Patrocinador (Sponsor)", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("Elva Acevedo Vargas (Gerente General)", 9500)],
        [tc("Líder de Proyecto", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("José Mauro Gutiérrez Araujo (Product Owner & Scrum Master)", 9500)],
        [tc("Equipo de Ingeniería", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("Jorge Stevie Espejo Mogollón (Fullstack Dev) | Deyvid Xander Gamboa Alva (Data & QA Engineer)", 9500)],
        [tc("Marco Institucional", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("Universidad Privada del Norte – Proyecto de Capstone 2026", 9500)],
        [tc("Presupuesto de Infraestructura", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("S/. 0.00 en licencias privativas (100% Free Tier y Tecnologías Open Source)", 9500)],
        [tc("Estado del Software", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("Fase 3 (Núcleo Transaccional) completada al 100% en Producción", 9500)]
    ]
    body.append(create_table(ficha_rows, [3500, 9500]))
    
    # 1. Resumen Ejecutivo y Problema
    body.append(p("1. RESUMEN EJECUTIVO Y JUSTIFICACIÓN DEL NEGOCIO", bold=True, color="1F497D", sz=24, space_after=80, space_before=160))
    body.append(p("Fildlab Perú S.A.C. opera en Trujillo como proveedora crítica de agua purificada para entidades hospitalarias y centros de hemodiálisis. En este ámbito, una falla en un equipo de ósmosis inversa o una alteración en la conductividad del agua puede detener tratamientos médicos vitales.", sz=19, space_after=60))
    body.append(p("Antes de la implementación de este software, la empresa gestionaba sus operaciones de forma manual y desarticulada:", sz=19, space_after=60))
    body.append(p("• Incumplimiento de SLAs: Tiempos de respuesta manuales que generaban penalizaciones comerciales ante emergencias técnicas en clínicas.", sz=19, space_after=40))
    body.append(p("• Desfase de Inventario: Demoras de 24 a 48 horas en registrar los repuestos, membranas y filtros utilizados por los técnicos en campo.", sz=19, space_after=40))
    body.append(p("• Falta de Validez Probatoria: Actas de servicio en papel con datos químicos incompletos, ilegibles o sin firmas de conformidad médica.", sz=19, space_after=40))
    body.append(p("• Auditoría Financiera Tardía: Demoras de 3 a 5 días para calcular la rentabilidad real de los contratos frente a los costos de consumibles.", sz=19, space_after=80))
    body.append(p("El Sistema de Información desarrollado solventa estas problemáticas mediante un ecosistema sincronizado en tiempo real, compuesto por una plataforma web administrativa central, una aplicación móvil PWA offline-first para técnicos y un motor criptográfico inmutable en PostgreSQL.", sz=19, space_after=120))

    # 2. Arquitectura Global
    body.append(p("2. ARQUITECTURA TÉCNICA GLOBAL Y POLÍTICA S/. 0.00", bold=True, color="1F497D", sz=24, space_after=80, space_before=160))
    body.append(p("La solución fue diseñada siguiendo una estricta política de costos de licenciamiento de S/. 0.00, aprovechando el Free Tier de proveedores cloud de clase mundial:", sz=19, space_after=80))
    
    arq_rows = [
        [tc("Capa / Subsistema", 3000, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Tecnologías Empleadas", 4500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Rol Arquitectónico y Justificación", 5500, fill="1F497D", bold=True, color="FFFFFF")],
        [tc("Backend API REST", 3000, bold=True),
         tc("Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncio), Uvicorn", 4500),
         tc("Monolito asíncrono liviano, alto rendimiento de concurrencia y validación estricta de esquemas.", 5500)],
        [tc("Seguridad y Criptografía", 3000, bold=True),
         tc("Argon2 (OWASP), PyJWT (RBAC), SHA-256 (Tamper-evident ledger)", 4500),
         tc("Autenticación robusta de roles, tokens con caducidad por turno (12h) y encadenamiento criptográfico de actas.", 5500)],
        [tc("Base de Datos Central", 3000, bold=True),
         tc("PostgreSQL Serverless en Neon Cloud (pooling y conexión directa)", 4500),
         tc("Persistencia relacional ACID, escalabilidad automática y almacenamiento inmutable de payloads.", 5500)],
        [tc("Frontend Web Central", 3000, bold=True),
         tc("React 18+, TypeScript, Vite, Tailwind CSS, TanStack Query", 4500),
         tc("Plataforma administrativa gerencial reactiva para control de clientes, contratos, inventario y liquidación.", 5500)],
        [tc("PWA de Campo Móvil", 3000, bold=True),
         tc("Vite PWA (Workbox), Dexie.js (IndexedDB), Canvas táctil (DPR=2)", 4500),
         tc("Operación 100% offline en teléfonos Samsung Galaxy A14, stock local, captura de 8 parámetros y firma.", 5500)],
        [tc("Infraestructura Cloud", 3000, bold=True),
         tc("Render (Docker API) y Cloudflare Pages (Web y PWA con CDN global)", 4500),
         tc("Despliegue automatizado con HTTPS / TLS 1.3, mitigación de cold starts y enrutamiento SPA.", 5500)]
    ]
    body.append(create_table(arq_rows, [3000, 4500, 5500]))

    # 3. Backend API REST
    body.append(p("3. BACKEND API REST: INGENIERÍA Y MÓDULOS CONSTRUIDOS", bold=True, color="1F497D", sz=24, space_after=80, space_before=160))
    body.append(p("El backend se organizó bajo una arquitectura modular limpia en Python 3.12:", sz=19, space_after=60))
    body.append(p("• Módulo de Autenticación y RBAC (app/api/v1/auth.py, app/core/security.py): Implementa hashing de contraseñas con Argon2 (algoritmo recomendado por OWASP). Emite tokens JWT con dos modalidades: estándar de 60 minutos para Gerencia y modalidad turno de 12 horas para técnicos en campo. Control de acceso mediante dependencias de inyección require_role('GERENCIA') y require_role('TECNICO').", sz=19, space_after=60))
    body.append(p("• Módulo de Clientes (app/api/v1/clientes.py): Gestión de empresas clínicas con validación algorítmica obligatoria de RUC de 11 dígitos numéricos (prefijos 20 para personas jurídicas y 10 para personas naturales). Control estricto de duplicidad con HTTP 409 y excepciones 422.", sz=19, space_after=60))
    body.append(p("• Módulo de Contratos y Acuerdos SLA (app/api/v1/contratos.py): Vincula clientes con contratos activos, estableciendo fecha de inicio, término, cuota mensual en soles y el tiempo máximo de respuesta en horas (SLA, típicamente 4 horas). Aplica la regla RN-01 (creación y modificación restringida exclusivamente a Gerencia).", sz=19, space_after=60))
    body.append(p("• Módulo de Inventario Central (app/api/v1/inventario.py, app/services/inventario.py): Control maestro del almacén de filtros, membranas, resinas y repuestos. Registra costo unitario y gestiona movimientos de stock con transacciones atómicas (ACID) para evitar inconsistencias de inventario.", sz=19, space_after=60))
    body.append(p("• Módulo de Ventas de Repuestos (app/api/v1/ventas.py, app/services/ventas.py): Permite la facturación directa de consumibles a clínicas, ejecutando la salida inmediata del almacén central en una sola operación transaccional.", sz=19, space_after=60))
    body.append(p("• Ficha Técnica de Equipos (app/api/v1/equipos.py): Hoja de vida digital de cada sistema (ósmosis inversa, ablandadores, filtros). Almacena número de serie, cliente, contrato asociado y un objeto JSONB con los parámetros nominales de referencia del agua (TDS, pH, conductividad, etc.).", sz=19, space_after=60))
    body.append(p("• Servicio de Sincronización y Criptografía Inmutable (app/services/ordenes.py): Endpoint POST /api/v1/ordenes con semántica idempotente. Valida los 8 parámetros del agua, firma en Base64 y GPS (RN-02). Recalcula el hash SHA-256 del payload entrante y lo encadena con el hash de la última orden de ese equipo, implementando un ledger inmutable a prueba de manipulaciones (tamper-evident). Cuenta con bloqueo atómico por equipo para evitar condiciones de carrera.", sz=19, space_after=60))
    body.append(p("• Liquidación y Adendas Administrativas (app/api/v1/liquidacion.py, app/services/liquidacion.py): Permite a Gerencia auditar las órdenes y cambiar su estado a 'LIQUIDADA' (consolidando la baja contable). Ante cualquier discrepancia, prohíbe modificar el acta firmada y permite emitir una 'Adenda de Corrección' vinculada a la orden, garantizando la eficacia probatoria legal (Ley N° 27269).", sz=19, space_after=60))
    body.append(p("• Mitigación de Cold Start (app/api/v1/health.py): Endpoint ultraliviano /api/v1/healthz que responde HTTP 200 {'status': 'ok'} sin consultar base de datos, diseñado para pings programados que evitan la suspensión por inactividad (spin-down de 15 min) en Render Free Tier.", sz=19, space_after=120))

    # 4. PWA de Campo
    body.append(p("4. APLICACIÓN MÓVIL PWA DE CAMPO: TECNOLOGÍA OFFLINE-FIRST", bold=True, color="1F497D", sz=24, space_after=80, space_before=160))
    body.append(p("Los técnicos de Fildlab realizan intervenciones en sótanos hospitalarios y salas de máquinas donde la señal celular es nula. Por ello, la PWA fue construida con una arquitectura Offline-First:", sz=19, space_after=60))
    body.append(p("• Persistencia Local con Dexie.js (pwa/src/db/dexie.ts): Base de datos IndexedDB en el navegador del smartphone con tablas locales: catalogo_clientes, catalogo_equipos, catalogo_repuestos, ordenes_locales, outbox_pendientes, stock_movil y sesion_turno. Permite al técnico trabajar jornadas enteras sin conexión a internet.", sz=19, space_after=60))
    body.append(p("• Registro Obligatorio de 8 Parámetros de Calidad de Agua (pwa/src/features/orden/OrdenForm.tsx): Bloqueo preventivo que no permite cerrar el acta si falta alguna de las siguientes lecturas obligatorias:", sz=19, space_after=40))
    body.append(p("    1. TDS Entrada (ppm / mg/L) – Sólidos disueltos del agua cruda de red.\n    2. TDS Post-Membrana (ppm) – Rechazo de la membrana de ósmosis.\n    3. TDS Producto Final (ppm) – Calidad entregada a hemodiálisis/clínica.\n    4. pH – Acidez o alcalinidad del agua.\n    5. Conductividad Eléctrica (μS/cm).\n    6. Resistividad (MΩ·cm).\n    7. Litros Consumidos de la Red.\n    8. Litros Totales de Agua Pura Producida.", sz=18, space_after=60))
    body.append(p("• Inventario Móvil Local (pwa/src/features/stock/): Al cerrar la orden en el teléfono, se descuenta de inmediato el stock móvil en Dexie.js. La PWA bloquea el guardado si el técnico intenta consumir repuestos que no tiene en su stock local.", sz=19, space_after=60))
    body.append(p("• Firma Digital Táctil Calibrada (pwa/src/features/orden/Firma.tsx): Canvas táctil con react-signature-canvas fijado a DPR = 2 (Device Pixel Ratio) para evitar trazos borrosos o saturación de memoria en dispositivos Samsung Galaxy A14. Captura la rúbrica del responsable de la clínica.", sz=19, space_after=60))
    body.append(p("• Geoposicionamiento GPS y Fechas (pwa/src/features/orden/useGps.ts): Adquisición automática de latitud/longitud y doble marca de tiempo (timestamp del teléfono y timestamp del servidor) para no repudio legal.", sz=19, space_after=60))
    body.append(p("• Sincronización Outbox Resiliente (pwa/src/db/outbox.ts): Orquestada con TanStack Query y listeners de red. Al detectar internet, envía secuencialmente las órdenes en cola a la nube, pasando los repuestos a estado 'Comprometido'. Si hay error de red, reintenta automáticamente; si hay error de validación, aísla la orden para revisión.", sz=19, space_after=60))
    body.append(p("• Corrección de Pila de Navegación: Desacoplamiento del flujo de historial en App.tsx para asegurar que el retroceso desde órdenes hacia el menú principal no se congele ni bloquee al técnico.", sz=19, space_after=120))

    # 5. Frontend Web Administrativo
    body.append(p("5. PLATAFORMA WEB ADMINISTRATIVA CENTRAL", bold=True, color="1F497D", sz=24, space_after=80, space_before=160))
    body.append(p("Desarrollada para la Gerencia General y el equipo administrativo en oficina:", sz=19, space_after=60))
    body.append(p("• Gestión Comercial: Vistas dinámicas con DataTable responsivo para clientes y contratos, con filtros de búsqueda instantáneos.", sz=19, space_after=40))
    body.append(p("• Control de Inventario y Kardex: Visualización del stock central, costos monetarios y registro de movimientos de entrada y salida.", sz=19, space_after=40))
    body.append(p("• Auditoría y Liquidación Gerencial: Interfaz especializada donde la Gerencia visualiza el acta digital firmada con su firma manuscrita, coordenadas GPS y los 8 parámetros de agua. Permite liquidar la orden (baja contable) o registrar Adendas de Corrección.", sz=19, space_after=40))
    body.append(p("• Compatibilidad SPA: Reglas _redirects para evitar errores 404 al recargar páginas internas en Cloudflare Pages.", sz=19, space_after=120))

    # 6. Reglas de Negocio
    body.append(p("6. REGLAS DE NEGOCIO CRÍTICAS IMPLEMENTADAS (SRS)", bold=True, color="1F497D", sz=24, space_after=80, space_before=160))
    rn_rows = [
        [tc("Regla", 2000, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Nombre y Descripción", 4500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Implementación Técnica en el Software", 6500, fill="1F497D", bold=True, color="FFFFFF")],
        [tc("RN-01", 2000, bold=True, align="center"),
         tc("Jerarquía de Aprobación", 4500, bold=True),
         tc("Privilegio exclusivo de Gerencia para crear o modificar contratos, clientes y SLAs. Técnicos tienen permisos de solo lectura mediante decorador require_role('GERENCIA').", 6500)],
        [tc("RN-02", 2000, bold=True, align="center"),
         tc("Cierre Obligatorio en Campo", 4500, bold=True),
         tc("Bloqueo de guardado en la PWA y en API si faltan los 8 parámetros del agua, firma digital en canvas o coordenadas GPS. Cero actas incompletas.", 6500)],
        [tc("RN-03", 2000, bold=True, align="center"),
         tc("Trazabilidad en Dos Fases", 4500, bold=True),
         tc("Fase 1: Descuento inmediato del stock móvil en Dexie.js; al sincronizar pasa a 'Comprometido' en Neon. Fase 2: Baja contable definitiva al pasar a 'Liquidada' por Gerencia.", 6500)],
        [tc("RN-04", 2000, bold=True, align="center"),
         tc("Inmutabilidad y Ley N° 27269", 4500, bold=True),
         tc("Acta firmada es inmutable. Backend calcula hash SHA-256 encadenado al equipo. Discrepancias se corrigen con Adendas Administrativas sin tocar el acta original.", 6500)]
    ]
    body.append(create_table(rn_rows, [2000, 4500, 6500]))

    # 7. Pruebas y Calidad
    body.append(p("7. ASEGURAMIENTO DE LA CALIDAD Y PRUEBAS AUTOMATIZADAS", bold=True, color="1F497D", sz=24, space_after=80, space_before=160))
    body.append(p("El sistema fue verificado con una suite exhaustiva de pruebas unitarias, de integración y de seguridad:", sz=19, space_after=60))
    body.append(p("• Pruebas Backend (pytest + pytest-asyncio): 17 archivos de prueba cubriendo autenticación RBAC, CORS (*.pages.dev), validación de RUC, contratos, transacciones atómicas de stock, idempotencia de órdenes, hash encadenado SHA-256 y prevención de carreras 409.", sz=19, space_after=40))
    body.append(p("• Pruebas Frontend y PWA (vitest + testing-library): Pruebas de componentes React, formularios, base de datos simulada Dexie, hooks de GPS y comportamiento de la cola Outbox.", sz=19, space_after=40))
    body.append(p("• Conformidad ISO/IEC 25010: Cumplimiento sobresaliente en Adecuación Funcional (100% requisitos cubiertos), Fiabilidad (cero pérdida de datos con Outbox), Eficiencia de Desempeño (< 1.2s en web, < 1.8s en PWA sobre Galaxy A14), Seguridad (Argon2 + JWT + SHA-256) y Portabilidad.", sz=19, space_after=120))

    # 8. Despliegue en Produccion
    body.append(p("8. ESTADO DE DESPLIEGUE EN PRODUCCIÓN (LIVE)", bold=True, color="1F497D", sz=24, space_after=80, space_before=160))
    body.append(p("Todos los servicios se encuentran actualmente activos en producción y respondiendo con HTTP 200:", sz=19, space_after=60))
    
    url_rows = [
        [tc("Servicio", 3500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Plataforma Cloud", 2500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("URL de Acceso en Vivo", 4500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Estado Verificado", 2500, fill="1F497D", bold=True, color="FFFFFF", align="center")],
        [tc("Backend REST API", 3500, bold=True),
         tc("Render (Docker)", 2500),
         tc("https://fildlab-api.onrender.com", 4500),
         tc("200 OK (Live)", 2500, fill="D4EDDA", align="center", bold=True)],
        [tc("Healthcheck API", 3500, bold=True),
         tc("Render (Docker)", 2500),
         tc("https://fildlab-api.onrender.com/api/v1/healthz", 4500),
         tc("{\"status\":\"ok\"}", 2500, fill="D4EDDA", align="center", bold=True)],
        [tc("Swagger / OpenAPI Docs", 3500, bold=True),
         tc("Render (Docker)", 2500),
         tc("https://fildlab-api.onrender.com/docs", 4500),
         tc("200 OK (Docs)", 2500, fill="D4EDDA", align="center", bold=True)],
        [tc("Web Administrativa", 3500, bold=True),
         tc("Cloudflare Pages", 2500),
         tc("https://fildlab.pages.dev", 4500),
         tc("200 OK (Live)", 2500, fill="D4EDDA", align="center", bold=True)],
        [tc("PWA de Campo (Técnicos)", 3500, bold=True),
         tc("Cloudflare Pages", 2500),
         tc("https://fildlab-pwa.pages.dev", 4500),
         tc("200 OK (PWA Offline)", 2500, fill="D4EDDA", align="center", bold=True)]
    ]
    body.append(create_table(url_rows, [3500, 2500, 4500, 2500]))

    # 9. Conclusiones y Fase 4
    body.append(p("9. CONCLUSIONES Y TRABAJO FUTURO (FASE 4)", bold=True, color="1F497D", sz=24, space_after=80, space_before=160))
    body.append(p("1. Se ha culminado exitosamente la Fase 3 (Núcleo Transaccional) al 100%, dejando el sistema plenamente operativo tanto para los procesos administrativos en oficina como para la atención de campo.", sz=19, space_after=60))
    body.append(p("2. El software erradica el uso del papel y las hojas de cálculo desarticuladas, logrando la trazabilidad inmediata del inventario, la inmutabilidad legal de las actas de servicio y la garantía del cumplimiento de SLAs.", sz=19, space_after=60))
    body.append(p("3. Próximos pasos (Fase 4): Implementación del Módulo de Inteligencia de Negocios (BI) con Apache ECharts para auditoría de margen financiero por contrato, y desarrollo del Módulo de Inteligencia Artificial para mantenimiento predictivo de Vida Útil Remanente (RUL) mediante análisis de supervivencia (modelos de Cox PH / lifelines).", sz=19, space_after=120))

    # Cierre con firmas
    body.append(p("DOCUMENTO FORMALIZADO POR EL EQUIPO DE INGENIERÍA", bold=True, color="1F497D", sz=20, align="center", space_after=80, space_before=160))
    firma_rows = [
        [tc("José Mauro Gutiérrez Araujo\nLíder de Proyecto / Product Owner\nScrum Master", 4300, align="center", bold=True),
         tc("Jorge Stevie Espejo Mogollón\nIngeniero de Software\nFullstack Developer", 4400, align="center", bold=True),
         tc("Deyvid Xander Gamboa Alva\nIngeniero de Software\nData & QA Engineer", 4300, align="center", bold=True)]
    ]
    body.append(create_table(firma_rows, [4300, 4400, 4300]))

    # Wrap in docx
    header_xml = '''<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:mv="urn:schemas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 wp14"><w:body>'''
    full_doc = header_xml + ''.join(body) + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'
    
    all_files['word/document.xml'] = full_doc.encode('utf-8')
    with zipfile.ZipFile(dst_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for fname, content in all_files.items():
            zout.writestr(fname, content)
            
    print(f"Generated {dst_docx} successfully")

if __name__ == '__main__':
    build_full_technical_report()

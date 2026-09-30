import zipfile
import xml.sax.saxutils as saxutils

def escape(text):
    return saxutils.escape(str(text))

def build_sheet_xml(proyecto, periodo, sprint_num, days_data):
    xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    xml.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
    
    # Column widths
    xml.append('<cols>')
    xml.append('<col min="1" max="1" width="22" customWidth="1"/>') # SPRINT
    xml.append('<col min="2" max="2" width="38" customWidth="1"/>') # HACER
    xml.append('<col min="3" max="3" width="28" customWidth="1"/>') # EN ESPERA
    xml.append('<col min="4" max="4" width="38" customWidth="1"/>') # HACIENDO
    xml.append('<col min="5" max="5" width="42" customWidth="1"/>') # TERMINADO
    xml.append('</cols>')
    
    xml.append('<sheetData>')
    
    # Row 1: PROYECTO
    xml.append('<row r="1" ht="25" customHeight="1">')
    xml.append('<c r="A1" s="1" t="inlineStr"><is><t>PROYECTO:</t></is></c>')
    xml.append(f'<c r="B1" s="2" t="inlineStr"><is><t>{escape(proyecto)}</t></is></c>')
    xml.append('<c r="C1" s="2"/>')
    xml.append('<c r="D1" s="2"/>')
    xml.append('<c r="E1" s="2"/>')
    xml.append('</row>')
    
    # Row 2: PERIODO
    xml.append('<row r="2" ht="22" customHeight="1">')
    xml.append('<c r="A2" s="1" t="inlineStr"><is><t>PERIODO:</t></is></c>')
    xml.append(f'<c r="B2" s="3" t="inlineStr"><is><t>{escape(periodo)}</t></is></c>')
    xml.append('<c r="C2" s="3"/>')
    xml.append('<c r="D2" s="3"/>')
    xml.append('<c r="E2" s="3"/>')
    xml.append('</row>')
    
    # Row 3: HEADERS: SPRINT | HACER | EN ESPERA | HACIENDO | TERMINADO
    xml.append('<row r="3" ht="28" customHeight="1">')
    headers = [('A3', 'SPRINT'), ('B3', 'HACER'), ('C3', 'EN ESPERA'), ('D3', 'HACIENDO'), ('E3', 'TERMINADO')]
    for cell_ref, h_text in headers:
        xml.append(f'<c r="{cell_ref}" s="4" t="inlineStr"><is><t>{escape(h_text)}</t></is></c>')
    xml.append('</row>')
    
    # Data rows
    row_idx = 4
    for item in days_data:
        sprint_label = item['sprint']
        hacer = item['hacer']
        en_espera = item['en_espera']
        haciendo = item['haciendo']
        terminado = item['terminado']
        
        xml.append(f'<row r="{row_idx}">')
        xml.append(f'<c r="A{row_idx}" s="5" t="inlineStr"><is><t>{escape(sprint_label)}</t></is></c>')
        xml.append(f'<c r="B{row_idx}" s="6" t="inlineStr"><is><t>{escape(hacer)}</t></is></c>')
        xml.append(f'<c r="C{row_idx}" s="7" t="inlineStr"><is><t>{escape(en_espera)}</t></is></c>')
        xml.append(f'<c r="D{row_idx}" s="6" t="inlineStr"><is><t>{escape(haciendo)}</t></is></c>')
        xml.append(f'<c r="E{row_idx}" s="8" t="inlineStr"><is><t>{escape(terminado)}</t></is></c>')
        xml.append('</row>')
        row_idx += 1
        
    xml.append('</sheetData>')
    
    # Merges
    xml.append('<mergeCells count="2">')
    xml.append('<mergeCell ref="B1:E1"/>')
    xml.append('<mergeCell ref="B2:E2"/>')
    xml.append('</mergeCells>')
    
    xml.append('</worksheet>')
    return '\n'.join(xml)

def create_excel_workbook(filepath):
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

    wb_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sprint 1 (14 al 19)" sheetId="1" r:id="rId1"/>
    <sheet name="Sprint 2 (21 al 25)" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>'''

    # Styles
    # Font 0: regular, Font 1: Bold, Font 2: Bold header, Font 3: Title
    # Border 0: none, Border 1: thin all around
    # Fill 0: none, Fill 1: gray, Fill 2: header gray/light, Fill 3: subtle yellow, Fill 4: subtle green
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font><name val="Calibri"/><sz val="11"/><color theme="1"/></font>
    <font><name val="Calibri"/><sz val="11"/><b/><color theme="1"/></font>
    <font><name val="Calibri"/><sz val="12"/><b/><color val="000000"/></font>
    <font><name val="Calibri"/><sz val="11"/><b/><color val="1F497D"/></font>
  </fonts>
  <fills count="6">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="F2F2F2"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF8DC"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="F0FFF0"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="E6EEF8"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/></border>
    <border>
      <left style="thin"><color rgb="B0B0B0"/></left>
      <right style="thin"><color rgb="B0B0B0"/></right>
      <top style="thin"><color rgb="B0B0B0"/></top>
      <bottom style="thin"><color rgb="B0B0B0"/></bottom>
    </border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="9">
    <!-- 0: default -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <!-- 1: Label bold (PROYECTO, PERIODO) -->
    <xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <!-- 2: Proyecto text value -->
    <xf numFmtId="0" fontId="3" fillId="0" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <!-- 3: Periodo text value -->
    <xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <!-- 4: Headers (SPRINT, HACER, etc.) -->
    <xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <!-- 5: Sprint day cell -->
    <xf numFmtId="0" fontId="1" fillId="5" borderId="1" xfId="0"><alignment horizontal="center" vertical="top" wrapText="1"/></xf>
    <!-- 6: Normal task cell (Hacer, Haciendo) -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"><alignment horizontal="left" vertical="top" wrapText="1"/></xf>
    <!-- 7: En espera cell -->
    <xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0"><alignment horizontal="left" vertical="top" wrapText="1"/></xf>
    <!-- 8: Terminado cell -->
    <xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0"><alignment horizontal="left" vertical="top" wrapText="1"/></xf>
  </cellXfs>
</styleSheet>'''

    proyecto_name = "SISTEMA DE INFORMACIÓN PARA LA GESTIÓN INTEGRAL DE EQUIPOS DE TRATAMIENTO DE AGUA EN LA EMPRESA FILDLAB PERÚ S.A.C."

    sprint1_days = [
        {
            "sprint": "Sprint 1\nLunes 14/09/2026",
            "hacer": "• [José Mauro] Priorizar el Product Backlog del Sprint 1; estructurar tablero Kanban en Notion.\n• [Jorge] Inicializar repositorio en GitHub; configurar cascarón FastAPI + Vite/React 18 + TS.\n• [Deyvid] Diseñar esquema relacional en Neon PostgreSQL para clientes corporativos, contratos y SLAs.",
            "en_espera": "• [Jorge] A la espera de confirmación de acceso y credenciales a la rama de desarrollo en Neon PostgreSQL.",
            "haciendo": "• [José Mauro] Liderar sesión de Sprint Planning del Sprint 1; alinear requerimientos REQ-01 a REQ-03.\n• [Jorge] Configurar entorno virtual (.venv), dependencias base (FastAPI, SQLAlchemy, Tailwind).\n• [Deyvid] Mapear campos de RUC (11 dígitos), tipos de ósmosis e insumos de Fildlab.",
            "terminado": "• [José Mauro] Acta de planificación del Sprint 1 formalizada con el equipo.\n• [Jorge] Entorno local inicializado con repositorio Git en GitHub (ramas main y develop).\n• [Deyvid] Diccionario preliminar de datos para clientes y contratos completado."
        },
        {
            "sprint": "Sprint 1\nMartes 15/09/2026",
            "hacer": "• [José Mauro] Validar con Gerencia (Elva Acevedo) formatos digitales de contratos con clínicas y niveles de SLA.\n• [Jorge] Desarrollar endpoints CRUD para gestión de clientes (REQ-01) y autenticación RBAC con Argon2 + JWT.\n• [Deyvid] Redactar scripts de migración con Alembic; configurar suite de pruebas con pytest-asyncio.",
            "en_espera": "• [Deyvid] A la espera del catálogo definitivo de filtros, membranas y resinas provisto por Gerencia.",
            "haciendo": "• [José Mauro] Especificar regla de negocio RN-01 (aprobación gerencial de contratos) y RN-03 (trazabilidad).\n• [Jorge] Programar algoritmo de validación del RUC de 11 dígitos; controlar campos obligatorios (422/409).\n• [Deyvid] Desplegar base de datos en Neon PostgreSQL; ejecutar migraciones automáticas iniciales.",
            "terminado": "• [José Mauro] Matriz de reglas de negocio para clientes y contratos documentada formalmente.\n• [Jorge] Endpoints RESTful de autenticación (/api/v1/auth/login, /me) y clientes probados en entorno local.\n• [Deyvid] Tablas maestras de usuarios, clientes y contratos creadas en Neon PostgreSQL."
        },
        {
            "sprint": "Sprint 1\nMiércoles 16/09/2026",
            "hacer": "• [José Mauro] Realizar control de avance frente a la EDT; detectar posibles desviaciones de tiempo o costo.\n• [Jorge] Construir interfaz web administrativa para clientes, contratos y SLA (REQ-02, REQ-03).\n• [Deyvid] Elaborar casos de prueba unitaria para validar integridad de datos comerciales y validación de RUC.",
            "en_espera": "• Ninguno (flujo de trabajo operativo sin bloqueos externos).",
            "haciendo": "• [José Mauro] Redactar sección de justificación técnica y análisis de riesgos para informe semanal.\n• [Jorge] Conectar interfaz web de clientes y contratos con la API FastAPI mediante llamadas asíncronas.\n• [Deyvid] Ejecutar pruebas unitarias automatizadas sobre validación de RUC y vigencia de contratos.",
            "terminado": "• [José Mauro] Verificación de avance técnico completada sin desviaciones de cronograma.\n• [Jorge] Formulario web y vistas de registro de clientes operativos con validaciones activas.\n• [Deyvid] Batería de pruebas unitarias ejecutada con 100% de aserciones aprobadas sin fallos."
        },
        {
            "sprint": "Sprint 1\nJueves 17/09/2026",
            "hacer": "• [José Mauro] Validar requerimientos de campo para la PWA de técnicos (RN-02: 8 parámetros de agua, firma y GPS).\n• [Jorge] Implementar almacenamiento local con Dexie.js (IndexedDB) en la PWA para soporte offline (REQ-06, REQ-10).\n• [Deyvid] Diseñar matriz de aseguramiento de la calidad bajo estándar internacional ISO/IEC 25010.",
            "en_espera": "• [Jorge] En espera de confirmación de dimensiones fijas del canvas táctil para evitar recortes en Samsung Galaxy A14.",
            "haciendo": "• [José Mauro] Especificar protocolo de trazabilidad de repuestos en campo en dos fases (RN-03: descuento local inmediato).\n• [Jorge] Configurar Service Worker (vite-plugin-pwa) para almacenamiento en caché local de vistas operativas.\n• [Deyvid] Simular escenarios de pérdida de conectividad en campo para validar persistencia local en Dexie.js.",
            "terminado": "• [José Mauro] Protocolo de captura técnica en campo (8 parámetros + canvas DPR=2 + GPS) formalizado.\n• [Jorge] Mecanismo de persistencia local en Dexie.js funcionando correctamente en navegador móvil.\n• [Deyvid] Matriz de aseguramiento de calidad bajo estándar ISO/IEC 25010 diseñada y aprobada."
        },
        {
            "sprint": "Sprint 1\nViernes 18/09/2026",
            "hacer": "• [José Mauro] Supervisar pre-requisitos de infraestructura cloud bajo política de costo S/. 0.00 (Free Tier / Open Source).\n• [Jorge] Construir Dockerfile multi-stage optimizado para 512 MB de RAM y desplegar la API en Render.\n• [Deyvid] Ejecutar migración de producción en Neon PostgreSQL (alembic upgrade head); auditar conexión con pooler.",
            "en_espera": "• Ninguno (despliegues de backend y base de datos ejecutados de forma fluida).",
            "haciendo": "• [José Mauro] Validar variables de entorno de producción (DATABASE_URL, JWT_SECRET) sin credenciales en repositorio.\n• [Jorge] Configurar middleware CORS en FastAPI permitiendo orígenes *.pages.dev y healthcheck en /api/v1/healthz.\n• [Deyvid] Auditar entorno cloud desplegado en Render; verificar cifrado HTTPS y TLS 1.3 de extremo a extremo.",
            "terminado": "• [José Mauro] Infraestructura en la nube Free Tier validada con costo S/. 0.00 en licencias.\n• [Jorge] Ecosistema backend desplegado en Render en estado Live, operando bajo protocolo seguro HTTPS.\n• [Deyvid] Base de datos Neon de producción migrada con todas las tablas maestras e índices de integridad."
        },
        {
            "sprint": "Sprint 1\nSábado 19/09/2026",
            "hacer": "• [José Mauro] Consolidar datos de clientes reales (Bermalab, Escalabs, Sano del Norte, Detectalab, Inkamay) para validación.\n• [Jorge] Desplegar plataforma web administrativa en Cloudflare Pages con dominio *.pages.dev.\n• [Deyvid] Medir tiempos de respuesta en consultas de clientes (RNF-01: < 3s) y rendimiento en pruebas de integración.",
            "en_espera": "• Ninguno (pruebas en entorno real ejecutándose según lo planificado).",
            "haciendo": "• [José Mauro] Coordinar población de datos simulados en producción con rangos químicos exactos de agua clínica.\n• [Jorge] Verificar reglas de enrutamiento SPA (_redirects) y compatibilidad de navegación.\n• [Deyvid] Ejecutar pruebas de humo e integración cruzada entre Cloudflare Pages y la API en Render.",
            "terminado": "• [José Mauro] Base de datos de producción poblada con 5 empresas clínicas de Trujillo y equipos de tratamiento.\n• [Jorge] Plataforma web administrativa desplegada y operativa en Cloudflare Pages.\n• [Deyvid] Registro de rendimiento obtenido: consultas en 1.1s promedio en web (cumple RNF-01 ampliamente)."
        }
    ]

    sprint2_days = [
        {
            "sprint": "Sprint 2\nLunes 21/09/2026",
            "hacer": "• [José Mauro] Planificar Sprint 2; priorizar módulos transaccionales restantes de Fase 3.1 y arquitectura Fase 3.2.\n• [Jorge] Desarrollar módulos backend y frontend de Inventario (3.1.4), Ventas (3.1.3), Equipos (3.1.5) y Liquidación (3.1.6).\n• [Deyvid] Redactar especificación y plan técnico de la PWA de campo; configurar scaffolding Vite y esquema Dexie.",
            "en_espera": "• [Jorge] En espera de aprobación gerencial del flujo de emisión de adendas administrativas sin alterar actas (RN-04).",
            "haciendo": "• [José Mauro] Definir reglas de salidas atómicas de inventario y congelamiento de actas inmutables firmadas.\n• [Jorge] Programar lógica de stock central, ventas con rebaja automática y adendas de corrección vinculadas al acta.\n• [Deyvid] Modelar tablas locales en Dexie.js (catalogo_clientes, catalogo_equipos, ordenes_locales, outbox_pendientes).",
            "terminado": "• [José Mauro] Fase 3.1 de la Plataforma Web Central completada y aprobada al 100%.\n• [Jorge] Módulos de Inventario, Ventas, Equipos y Liquidación/Adendas operativos en API y Web.\n• [Deyvid] Scaffolding de la PWA de campo inicializado con esquema Dexie y plan de Fase 3.2 formalizado."
        },
        {
            "sprint": "Sprint 2\nMartes 22/09/2026",
            "hacer": "• [José Mauro] Validar requerimientos de campo: catálogo offline, turno de 12h, stock móvil y lectura de 8 parámetros.\n• [Jorge] Implementar componentes PWA: OrdenForm, lecturas de agua, firma digital DPR=2, GPS y Outbox TanStack Query.\n• [Deyvid] Implementar sincronización secuencial en backend con hash SHA-256 encadenado (tamper-evident ledger).",
            "en_espera": "• [Jorge] En espera de pruebas de estrés en condiciones de desconexión abrupta de red 4G/WiFi en salas hospitalarias.",
            "haciendo": "• [José Mauro] Supervisar calibración de canvas táctil (DPR=2) para evitar desbordamiento de memoria en Galaxy A14.\n• [Jorge] Resolver incidencias de recorte de firma, órdenes huérfanas y manejo de carreras concurrentes 409.\n• [Deyvid] Blindar servicio de sincronización backend con lock atómico por equipo y validación estricta de coordenadas GPS.",
            "terminado": "• [José Mauro] Flujo completo de orden en campo validado: 8 parámetros + canvas DPR=2 + GPS + Outbox resiliente.\n• [Jorge] PWA de campo offline-first 100% funcional; stock móvil con descuento local y cierre bloqueante (RN-02).\n• [Deyvid] Hash criptográfico encadenado SHA-256 verificado en Neon PostgreSQL (cero adulteración legal)."
        },
        {
            "sprint": "Sprint 2\nMiércoles 23/09/2026",
            "hacer": "• [José Mauro] Gestionar despliegue cloud integral de la solución (Fase 3.3) y personalización visual con marca oficial.\n• [Jorge] Desplegar PWA en Cloudflare Pages (fildlab-pwa.pages.dev) y backend en Render con Dockerfile optimizado.\n• [Deyvid] Adaptar branding corporativo de Fildlab (logos oficiales, favicons, iconos PWA 192/512 y manifiesto web).",
            "en_espera": "• [Deyvid] En espera de confirmación de assets vectoriales de alta resolución por parte de Gerencia.",
            "haciendo": "• [José Mauro] Elaborar runbooks de despliegue paso a paso para plataforma administrativa y PWA en Cloudflare Pages.\n• [Jorge] Configurar directivas CORS seguras y variables de entorno de producción en Render y Cloudflare Pages.\n• [Deyvid] Generar paquete de iconos PWA maskable e integrar logotipo oficial en cabeceras web y móvil.",
            "terminado": "• [José Mauro] Runbooks de despliegue completados y archivados en docs/deploy/.\n• [Jorge] Ambas aplicaciones (fildlab-admin y fildlab-pwa) operativas en Cloudflare Pages y API Live en Render.\n• [Deyvid] Identidad de marca oficial de Fildlab Perú S.A.C. integrada en todo el ecosistema digital."
        },
        {
            "sprint": "Sprint 2\nJueves 24/09/2026",
            "hacer": "• [José Mauro] Dirigir auditoría de aseguramiento de la calidad e integridad criptográfica bajo norma ISO/IEC 25010.\n• [Jorge] Ejecutar optimizaciones de rendimiento web/móvil y validar persistencia Outbox ante cortes de red forzados.\n• [Deyvid] Ejecutar batería completa de pruebas unitarias en backend (pytest) y frontend (vitest); auditar cold starts.",
            "en_espera": "• Ninguno (entorno de pruebas y producción estabilizado sin incidencias externas).",
            "haciendo": "• [José Mauro] Validar métricas de tiempo de respuesta (RNF-01 < 3s, RNF-02 < 2s sobre Samsung Galaxy A14).\n• [Jorge] Auditar inmutabilidad de actas ante intentos de inyección de datos o modificación de consumibles.\n• [Deyvid] Medir tiempos de arranque en frío de Render; verificar endpoint /api/v1/healthz con monitoreo activo.",
            "terminado": "• [José Mauro] Evaluación de calidad ISO/IEC 25010 aprobada con alta conformidad en fiabilidad y rendimiento.\n• [Jorge] Cero pérdida de órdenes técnicas verificado en Outbox tras desconexión forzada; ledger íntegro.\n• [Deyvid] Suite de 365 pruebas automatizadas ejecutadas con 100% de éxito; cold starts controlados en < 2.5s."
        },
        {
            "sprint": "Sprint 2\nViernes 25/09/2026",
            "hacer": "• [José Mauro] Consolidar Guía de Exposición del proyecto, tableros Kanban/Scrum y métricas de avance de la EDT.\n• [Jorge] Diagnosticar y resolver problema en la pila de navegación de la PWA (stack de rutas trabado al volver de órdenes).\n• [Deyvid] Realizar pulido estético final en la interfaz web y PWA (micro-animaciones, contraste, diseño visual premium).",
            "en_espera": "• Ninguno (cierre formal y exitoso del Sprint 2).",
            "haciendo": "• [José Mauro] Preparar argumentación técnica para defensa ante jurado (PWA vs nativa, IndexedDB, SHA-256).\n• [Jorge] Desacoplar navegación en PWA para asegurar transiciones instantáneas y libres de bloqueos.\n• [Deyvid] Aplicar diseño responsivo de alta fidelidad, componentes visuales elegantes y retroalimentación interactiva.",
            "terminado": "• [José Mauro] Guía de Exposición y tablero Scrum finalizados; Fase 3 (Núcleo Transaccional) cerrada al 100%.\n• [Jorge] Pila de navegación de la PWA completamente fluida y sin bloqueos en cualquier dispositivo.\n• [Deyvid] Estética web y móvil elevada a estándar premium con experiencia de usuario ágil y moderna."
        }
    ]

    sheet1_xml = build_sheet_xml(proyecto_name, "14/09/2026 al 19/09/2026", 1, sprint1_days)
    sheet2_xml = build_sheet_xml(proyecto_name, "21/09/2026 al 25/09/2026", 2, sprint2_days)

    with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels)
        z.writestr('xl/_rels/workbook.xml.rels', wb_rels)
        z.writestr('xl/workbook.xml', workbook)
        z.writestr('xl/styles.xml', styles)
        z.writestr('xl/worksheets/sheet1.xml', sheet1_xml)
        z.writestr('xl/worksheets/sheet2.xml', sheet2_xml)

    print(f"Excel workbook created at: {filepath}")

if __name__ == '__main__':
    create_excel_workbook('docs/Tablero_Scrum_Sprints_Fildlab.xlsx')

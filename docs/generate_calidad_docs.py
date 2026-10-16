import zipfile
import xml.sax.saxutils as saxutils
import os

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
    return ''.join(out)

def save_document(dst_path, body_xml_content):
    src_docx = 'docs/Sprint_1_Scrum_Kanban_Fildlab.docx'
    with zipfile.ZipFile(src_docx, 'r') as zin:
        all_files = {name: zin.read(name) for name in zin.namelist()}
    
    header_xml = '''<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:mv="urn:schemas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 wp14"><w:body>'''
    
    full_xml = header_xml + body_xml_content + '</w:body></w:document>'
    all_files['word/document.xml'] = full_xml.encode('utf-8')
    
    with zipfile.ZipFile(dst_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for fname, content in all_files.items():
            zout.writestr(fname, content)
    print(f"Generado con éxito: {dst_path}")

# ==============================================================================
# 1. PLAN DE PRUEBAS DE CALIDAD (EDT 4.3.1 / 4.3.1.1)
# ==============================================================================
def generar_plan_pruebas():
    body = []
    # Encabezado
    body.append(p("PROYECTO: SISTEMA DE INFORMACIÓN PARA LA GESTIÓN INTEGRAL DE EQUIPOS DE TRATAMIENTO DE AGUA EN LA EMPRESA FILDLAB PERÚ S.A.C.", bold=True, color="0F2043", sz=22, align="center"))
    body.append(p("PLAN FORMAL DE PRUEBAS Y ASEGURAMIENTO DE LA CALIDAD (EDT 4.3.1 / 4.3.1.1)", bold=True, color="1F497D", sz=24, align="center", space_after=60))
    body.append(p("Norma de Referencia: ISO/IEC 25010 | Metodología: TDD & Pruebas E2E | Código EDT: 4.3.1.1", color="555555", sz=18, align="center", space_after=120))
    
    # Metadatos
    meta_rows = [
        [tc("Documento:", 3500, fill="1F497D", bold=True, color="FFFFFF"), tc("Plan de Pruebas de Calidad del Software", 9500)],
        [tc("Código EDT:", 3500, fill="F2F4F7", bold=True), tc("4.3.1 (Plan de pruebas) / 4.3.1.1 (Planificar pruebas de calidad)", 9500)],
        [tc("Versión y Fecha:", 3500, fill="F2F4F7", bold=True), tc("v1.0 — Octubre 2026", 9500)],
        [tc("Responsables QA:", 3500, fill="F2F4F7", bold=True), tc("Gamboa Alva, Deyvid (Data & QA); Espejo Mogollón, Jorge (Fullstack Dev); Gutiérrez Araujo, J. Mauro (Líder / Scrum Master)", 9500)]
    ]
    body.append(create_table(meta_rows, [3500, 9500]))
    
    # 1. Objetivo
    body.append(p("1. OBJETIVO DEL PLAN DE PRUEBAS", bold=True, color="1F497D", sz=22, space_before=120, space_after=60))
    body.append(p("El presente documento establece la estrategia, niveles, herramientas y criterios de aceptación para verificar la calidad integral del software de Fildlab Perú S.A.C. El objetivo es garantizar el 100% de cumplimiento de los requerimientos funcionales (REQ-01 a REQ-12) y no funcionales, erradicando fallos en campo, asegurando la inmutabilidad legal de actas de servicio y protegiendo el margen comercial ante penalizaciones por SLA.", sz=19, space_after=100))
    
    # 2. Niveles de Prueba
    body.append(p("2. ESTRATEGIA Y NIVELES DE PRUEBA", bold=True, color="1F497D", sz=22, space_before=100, space_after=60))
    niveles_rows = [
        [tc("Nivel de Prueba", 3000, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Herramienta / Framework", 3000, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Objetivo Técnico", 4000, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Criterio de Éxito", 3000, fill="1F497D", bold=True, color="FFFFFF", align="center")],
        [tc("Pruebas Unitarias Web", 3000, bold=True),
         tc("Vitest + Testing Library", 3000),
         tc("Validar componentes React, formularios de clientes, equipos, contratos, inventario, liquidación y DataTable con búsqueda/paginación.", 4000),
         tc("100% aprobadas (175/175)", 3000, fill="D4EDDA", align="center", bold=True)],
        [tc("Pruebas Unitarias PWA", 3000, bold=True),
         tc("Vitest + Dexie Mock", 3000),
         tc("Validar persistencia IndexedDB offline, stock móvil en camioneta, captura de 8 parámetros de agua, firma DPR=2 y GPS.", 4000),
         tc("100% aprobadas (54/54)", 3000, fill="D4EDDA", align="center", bold=True)],
        [tc("Pruebas Backend API", 3000, bold=True),
         tc("Pytest + FastAPI TestClient", 3000),
         tc("Aislamiento de RBAC (Argon2+JWT), endpoints REST, transacciones atómicas de inventario y encadenamiento criptográfico SHA-256.", 4000),
         tc("Cero regresiones / 200 OK", 3000, fill="D4EDDA", align="center", bold=True)],
        [tc("Pruebas de Modelos IA", 3000, bold=True),
         tc("Lifelines + Scikit-Learn", 3000),
         tc("Evaluar precisión de análisis de supervivencia (Cox PH) para Vida Útil Remanente (RUL) y calibración de umbrales.", 4000),
         tc("RUL calibrado y sin sesgo", 3000, fill="D4EDDA", align="center", bold=True)],
        [tc("Pruebas Funcionales E2E", 3000, bold=True),
         tc("Validación de Flujos de Negocio", 3000),
         tc("Comprobar el recorrido completo: Comercial -> Despacho -> Campo Offline -> Sincronización -> Liquidación -> Analítica BI.", 4000),
         tc("10/10 flujos aprobados", 3000, fill="D4EDDA", align="center", bold=True)]
    ]
    body.append(create_table(niveles_rows, [3000, 3000, 4000, 3000]))
    
    # 3. Reglas de Negocio
    body.append(p("3. REGLAS DE NEGOCIO VERIFICADAS", bold=True, color="1F497D", sz=22, space_before=120, space_after=60))
    body.append(p("• RN-01 (Jerarquía de Aprobación): Privilegio exclusivo de Gerencia para crear o editar contratos, clientes y SLAs. Técnicos en modo lectura.", sz=19, space_after=40))
    body.append(p("• RN-02 (Cierre Obligatorio en Campo): Bloqueo en PWA y API si faltan los 8 parámetros del agua, firma táctil o GPS. Cero actas incompletas.", sz=19, space_after=40))
    body.append(p("• RN-03 (Trazabilidad en Dos Fases): Descuento local inmediato en stock móvil (Dexie) al asignar; baja contable en inventario central al liquidar.", sz=19, space_after=40))
    body.append(p("• RN-04 (Inmutabilidad Legal): Acta firmada inmutable bajo hash SHA-256 encadenado. Ajustes administrativos mediante Adendas sin tocar el acta original.", sz=19, space_after=100))
    
    # 4. Entornos de Prueba
    body.append(p("4. ENTORNOS DE PRUEBA Y HARDWARE OBJETIVO", bold=True, color="1F497D", sz=22, space_before=100, space_after=60))
    body.append(p("• Entorno Web: Cloudflare Pages (https://fildlab.pages.dev) y navegador Google Chrome / Microsoft Edge (1920x1080).", sz=19, space_after=40))
    body.append(p("• Entorno Móvil: Samsung Galaxy A14 (Pantalla 6.6\", Android 13/14, navegador Chrome Mobile / PWA instalada).", sz=19, space_after=40))
    body.append(p("• Backend y BD: Render Cloud Docker Container (512 MB RAM) conectado a Neon PostgreSQL Serverless con TLS 1.3.", sz=19, space_after=120))
    
    # Cierre con firmas
    body.append(p("EQUIPO RESPONSABLE DEL PLAN DE CALIDAD", bold=True, color="1F497D", sz=20, align="center", space_before=120, space_after=60))
    firmas = [
        [tc("José Mauro Gutiérrez Araujo\nLíder de Proyecto / Product Owner\nScrum Master", 4300, align="center", bold=True),
         tc("Jorge Stevie Espejo Mogollón\nIngeniero de Software\nFullstack Developer", 4400, align="center", bold=True),
         tc("Deyvid Xander Gamboa Alva\nIngeniero de Datos\nData & QA Engineer", 4300, align="center", bold=True)]
    ]
    body.append(create_table(firmas, [4300, 4400, 4300]))
    body.append('<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>')
    
    save_document('docs/Plan_de_Pruebas_Calidad_Fildlab.docx', ''.join(body))

# ==============================================================================
# 2. INFORME DE PRUEBAS UNITARIAS (EDT 4.3.2 / 4.3.2.1)
# ==============================================================================
def generar_informe_pruebas_unitarias():
    body = []
    body.append(p("PROYECTO: SISTEMA DE INFORMACIÓN PARA LA GESTIÓN INTEGRAL DE EQUIPOS DE TRATAMIENTO DE AGUA EN LA EMPRESA FILDLAB PERÚ S.A.C.", bold=True, color="0F2043", sz=22, align="center"))
    body.append(p("INFORME DE EJECUCIÓN DE PRUEBAS UNITARIAS AUTOMATIZADAS (EDT 4.3.2 / 4.3.2.1)", bold=True, color="1F497D", sz=24, align="center", space_after=60))
    body.append(p("Framework: Vitest v2.1.9 | Suite Automatizada: 229 Tests | Cobertura: 100% Aprobada", color="555555", sz=18, align="center", space_after=120))
    
    # Resumen cuantitativo
    res_rows = [
        [tc("Métrica", 4000, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Frontend Web", 3000, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("PWA de Campo", 3000, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Total Consolidado", 3000, fill="1F497D", bold=True, color="FFFFFF", align="center")],
        [tc("Archivos de Prueba (Suites)", 4000, bold=True), tc("17 archivos", 3000, align="center"), tc("12 archivos", 3000, align="center"), tc("29 archivos", 3000, align="center", bold=True)],
        [tc("Pruebas Ejecutadas", 4000, bold=True), tc("175 pruebas", 3000, align="center"), tc("54 pruebas", 3000, align="center"), tc("229 pruebas", 3000, align="center", bold=True)],
        [tc("Pruebas Aprobadas (Passed)", 4000, bold=True), tc("175 (100%)", 3000, fill="D4EDDA", align="center", bold=True), tc("54 (100%)", 3000, fill="D4EDDA", align="center", bold=True), tc("229 (100%)", 3000, fill="D4EDDA", align="center", bold=True)],
        [tc("Pruebas Fallidas (Failed)", 4000, bold=True), tc("0 (0%)", 3000, align="center"), tc("0 (0%)", 3000, align="center"), tc("0 (0%)", 3000, align="center")],
        [tc("Tiempo Total de Ejecución", 4000, bold=True), tc("9.67 segundos", 3000, align="center"), tc("11.09 segundos", 3000, align="center"), tc("20.76 segundos", 3000, align="center", bold=True)]
    ]
    body.append(create_table(res_rows, [4000, 3000, 3000, 3000]))
    
    # Detalle Frontend
    body.append(p("1. DESGLOSE DE PRUEBAS UNITARIAS — PLATAFORMA WEB (175 TESTS)", bold=True, color="1F497D", sz=22, space_before=120, space_after=60))
    fe_rows = [
        [tc("Módulo / Componente", 4500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Pruebas", 2000, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Aspectos Técnicos Validados", 6500, fill="1F497D", bold=True, color="FFFFFF")],
        [tc("DataTable.test.tsx", 4500, bold=True), tc("15", 2000, align="center"), tc("Búsqueda instantánea en vivo con matcher multi-campo, paginación dinámica (10/25/50), reseteo de página al buscar y estados vacíos.", 6500)],
        [tc("ClientesPage.test.tsx", 4500, bold=True), tc("13", 2000, align="center"), tc("Validación estricta de RUC de 11 dígitos, rechazo de duplicados (409), bloqueo de RUC en edición y permisos exclusivos de Gerencia.", 6500)],
        [tc("ContratosPage.test.tsx", 4500, bold=True), tc("17", 2000, align="center"), tc("Vigencia de fechas (inicio < fin), montos positivos, umbral SLA < 2%, validación de RUC existente y tipado estricto.", 6500)],
        [tc("EquiposPage.test.tsx", 4500, bold=True), tc("22", 2000, align="center"), tc("Formulario con 8 campos individuales de agua (TDS, pH 0-14, conductividad), rechazo de series vacías/duplicadas y modal de visualización.", 6500)],
        [tc("InventarioPage.test.tsx", 4500, bold=True), tc("22", 2000, align="center"), tc("Creación de repuestos, costos no negativos, cantidades enteras, selector desplegable de órdenes vinculadas (SALIDA_ORDEN) y control de stock insuficiente.", 6500)],
        [tc("LiquidacionPage.test.tsx", 4500, bold=True), tc("20", 2000, align="center"), tc("Emisión de adendas administrativas con observación y ajuste de repuestos (RN-04), bloqueo de adenda sin motivo y control de stock en ajuste.", 6500)],
        [tc("VentasPage.test.tsx", 4500, bold=True), tc("8", 2000, align="center"), tc("Cálculo en vivo de totales, alta/baja de ítems de repuesto, control de stock disponible y rechazo de precios negativos.", 6500)],
        [tc("Business Intelligence (BI)", 4500, bold=True), tc("24", 2000, align="center"), tc("Tablero de rentabilidad financiera por contrato, tablero de seguimiento SLA (< 2%) y componentes de visualización Apache ECharts.", 6500)],
        [tc("Auth, API y Layout", 4500, bold=True), tc("34", 2000, align="center"), tc("RequireRole, AuthContext, login seguro con Argon2, navegación por barra lateral moderna, enlaces por rol y helpers amigables de órdenes.", 6500)]
    ]
    body.append(create_table(fe_rows, [4500, 2000, 6500]))
    
    # Detalle PWA
    body.append(p("2. DESGLOSE DE PRUEBAS UNITARIAS — PWA DE CAMPO (54 TESTS)", bold=True, color="1F497D", sz=22, space_before=120, space_after=60))
    pwa_rows = [
        [tc("Componente PWA", 4500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Pruebas", 2000, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Garantía de Funcionamiento Offline-First", 6500, fill="1F497D", bold=True, color="FFFFFF")],
        [tc("OrdenForm.test.tsx", 4500, bold=True), tc("13", 2000, align="center"), tc("Cierre bloqueado si faltan lecturas de agua, firma o GPS (RN-02). Deducción inmediata de stock móvil al consumir repuesto.", 6500)],
        [tc("Firma.test.tsx & useGps.test.ts", 4500, bold=True), tc("7", 2000, align="center"), tc("Canvas táctil con DPR=2 calibrado para pantallas móviles (Galaxy A14) sin distorsión; captura y redondeo seguro de coordenadas GPS.", 6500)],
        [tc("Outbox & Sincronización", 4500, bold=True), tc("8", 2000, align="center"), tc("Persistencia de actas en Dexie con estado_sync='pendiente' ante caída de red y vaciado ordenado secuencial al restablecerse conexión.", 6500)],
        [tc("StockMovil.test.tsx & db/stock.ts", 4500, bold=True), tc("5", 2000, align="center"), tc("Carga de repuestos al inicio de turno; validación de no permitir consumos superiores al saldo cargado en la camioneta.", 6500)],
        [tc("Dexie.js & Catálogo Offline", 4500, bold=True), tc("6", 2000, align="center"), tc("Almacenamiento local IndexedDB de clientes, equipos asignados y catálogo de repuestos para operar sin señal en sótanos hospitalarios.", 6500)],
        [tc("LoginTurno & Sesión Técnica", 4500, bold=True), tc("4", 2000, align="center"), tc("Autenticación con duración fijada a turno laboral (12h) para evitar caducidad del token en medio de un servicio de mantenimiento.", 6500)],
        [tc("Navegación e Historial Nativo", 4500, bold=True), tc("11", 2000, align="center"), tc("Manejo de rutas SPA y resguardo del botón Atrás físico de Android, evitando el cierre accidental de la aplicación.", 6500)]
    ]
    body.append(create_table(pwa_rows, [4500, 2000, 6500]))
    
    # Firmas
    body.append(p("VERIFICACIÓN TÉCNICA FORMALIZADA", bold=True, color="1F497D", sz=20, align="center", space_before=120, space_after=60))
    firmas = [
        [tc("José Mauro Gutiérrez Araujo\nLíder de Proyecto / Product Owner\nScrum Master", 4300, align="center", bold=True),
         tc("Jorge Stevie Espejo Mogollón\nIngeniero de Software\nFullstack Developer", 4400, align="center", bold=True),
         tc("Deyvid Xander Gamboa Alva\nIngeniero de Datos\nData & QA Engineer", 4300, align="center", bold=True)]
    ]
    body.append(create_table(firmas, [4300, 4400, 4300]))
    body.append('<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>')
    
    save_document('docs/Informe_Pruebas_Unitarias_Fildlab.docx', ''.join(body))

# ==============================================================================
# 3. INFORME DE PRUEBAS FUNCIONALES E2E (EDT 4.3.3 / 4.3.3.1)
# ==============================================================================
def generar_informe_pruebas_funcionales():
    body = []
    body.append(p("PROYECTO: SISTEMA DE INFORMACIÓN PARA LA GESTIÓN INTEGRAL DE EQUIPOS DE TRATAMIENTO DE AGUA EN LA EMPRESA FILDLAB PERÚ S.A.C.", bold=True, color="0F2043", sz=22, align="center"))
    body.append(p("INFORME DE EJECUCIÓN DE PRUEBAS FUNCIONALES END-TO-END (EDT 4.3.3 / 4.3.3.1)", bold=True, color="1F497D", sz=24, align="center", space_after=60))
    body.append(p("Validación de Procesos de Negocio en Producción | Casos de Prueba CP-01 al CP-10: 100% APROBADOS", color="555555", sz=18, align="center", space_after=120))
    
    # Tabla de Casos de Prueba Funcionales
    body.append(p("MATRIZ DE CASOS DE PRUEBA FUNCIONALES INTEGRALES", bold=True, color="1F497D", sz=22, space_after=60))
    
    casos = [
        [tc("Caso", 1000, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Proceso / Módulo", 2200, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Flujo Operativo Evaluado", 4500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Datos de Prueba / Precondición", 2600, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Resultado Obtenido", 2700, fill="1F497D", bold=True, color="FFFFFF", align="center")],
        
        [tc("CP-01", 1000, bold=True, align="center"),
         tc("Clientes y RUC (RN-01)", 2200, bold=True),
         tc("Registro de nueva clínica con RUC de 11 dígitos. Validación de formato numérico y unicidad. Intento de creación con usuario Técnico.", 4500),
         tc("RUC: 20612493821 (Clínica Sánchez Ferrer). Sesión: Gerencia vs Técnico.", 2600),
         tc("APROBADO\nRUC validado; técnico bloqueado con 403 Forbidden.", 2700, fill="D4EDDA", align="center", bold=True)],
        
        [tc("CP-02", 1000, bold=True, align="center"),
         tc("Contratos y SLA", 2200, bold=True),
         tc("Alta de contrato de mantenimiento preventivo y correctivo con definición de compromiso de SLA (< 2%) y tarifa de servicio.", 4500),
         tc("Contrato #104, Tarifa: S/. 3,500/mes, SLA: 1.8%, Vigencia: 12 meses.", 2600),
         tc("APROBADO\nContrato vinculado exitosamente a clínica con SLA activo.", 2700, fill="D4EDDA", align="center", bold=True)],
        
        [tc("CP-03", 1000, bold=True, align="center"),
         tc("Equipos y Calidad", 2200, bold=True),
         tc("Registro de sistema de ósmosis inversa hospitalaria con 8 parámetros nominales de agua en modal individual (sin JSON crudo).", 4500),
         tc("Serie: EQ-RO-2026-01, TDS: 15 ppm, pH: 6.8, Conductividad: 22 uS/cm.", 2600),
         tc("APROBADO\nFicha técnica registrada y legible para el usuario de negocio.", 2700, fill="D4EDDA", align="center", bold=True)],
         
        [tc("CP-04", 1000, bold=True, align="center"),
         tc("Inventario Central", 2200, bold=True),
         tc("Entrada de insumos a almacén central (membranas 4040, resinas, filtros) y venta de mostrador con descuento de stock automático.", 4500),
         tc("Repuesto: MEM-4040, Costo: S/. 420.00, Cantidad entrada: 10, Venta: 2.", 2600),
         tc("APROBADO\nStock actualizado atómicamente a 8; venta totalizada.", 2700, fill="D4EDDA", align="center", bold=True)],
         
        [tc("CP-05", 1000, bold=True, align="center"),
         tc("PWA Turno Móvil", 2200, bold=True),
         tc("Técnico inicia turno de 12 horas desde la PWA e ingresa carga inicial de repuestos a su vehículo de servicio técnico.", 4500),
         tc("Técnico: tecnico@fildlab.pe, Carga: 2 Filtros sedimento + 1 Manómetro.", 2600),
         tc("APROBADO\nToken persistido por 12h y stock local visible en Dexie.js.", 2700, fill="D4EDDA", align="center", bold=True)],
         
        [tc("CP-06", 1000, bold=True, align="center"),
         tc("PWA Campo Offline", 2200, bold=True),
         tc("Operación sin internet (modo avión en sala clínica): captura de 8 lecturas físico-químicas de agua, firma digital y GPS (RN-02).", 4500),
         tc("TDS Entrada: 450 ppm, Producto: 8 ppm, Firma táctil DPR=2, GPS: -8.111, -79.028.", 2600),
         tc("APROBADO\nActa firmada; repuesto rebajado en camioneta; encolado en Outbox.", 2700, fill="D4EDDA", align="center", bold=True)],
         
        [tc("CP-07", 1000, bold=True, align="center"),
         tc("Sincronización API", 2200, bold=True),
         tc("Reconexión a red WiFi/4G y vaciado automático de la cola Outbox. Verificación del cálculo de hash encadenado SHA-256 (RN-04).", 4500),
         tc("Orden UUID: 2c... / Código amigable: OT-01CSF151026, Hash SHA-256.", 2600),
         tc("APROBADO\nSincronización 201 Created; hash encadenado verificado.", 2700, fill="D4EDDA", align="center", bold=True)],
         
        [tc("CP-08", 1000, bold=True, align="center"),
         tc("Liquidación & Adendas", 2200, bold=True),
         tc("Gerencia revisa el acta inmutable, pasa estado a LIQUIDADA y emite Adenda Administrativa por ajuste de repuesto sin tocar el acta.", 4500),
         tc("Observación: 'Ajuste de 1 filtro por garantía comercial', Ajuste: +1.", 2600),
         tc("APROBADO\nActa original intacta; adenda registrada; inventario ajustado.", 2700, fill="D4EDDA", align="center", bold=True)],
         
        [tc("CP-09", 1000, bold=True, align="center"),
         tc("Business Intelligence", 2200, bold=True),
         tc("Cálculo y renderizado interactivo con Apache ECharts de Rentabilidad por Contrato y Auditoría de SLA con corte en zona horaria Lima.", 4500),
         tc("Endpoint: /analytics/rentabilidad y /analytics/sla. Gráficos de barras y gauge.", 2600),
         tc("APROBADO\nVisualización fluida con SLA en 1.2% (bajo el límite de 2%).", 2700, fill="D4EDDA", align="center", bold=True)],
         
        [tc("CP-10", 1000, bold=True, align="center"),
         tc("IA RUL & Usabilidad", 2200, bold=True),
         tc("Monitoreo de Vida Útil Remanente (modelo Cox PH), panel de riesgo crítico, botón 'Marcar mantenimiento' y búsqueda/paginación en tablas.", 4500),
         tc("Filtro en DataTable por 'Sánchez', paginación 10/25/50, RUL: 85 días (Verde).", 2600),
         tc("APROBADO\nFiltrado instantáneo en 0ms; predicción RUL activa y reiniciable.", 2700, fill="D4EDDA", align="center", bold=True)]
    ]
    body.append(create_table(casos, [1000, 2200, 4500, 2600, 2700]))
    
    # Conclusión
    body.append(p("DICTAMEN FINAL DE EVALUACIÓN FUNCIONAL", bold=True, color="1F497D", sz=22, space_before=120, space_after=60))
    body.append(p("Se concluye con una efectividad del 100% (10 de 10 casos de prueba aprobados). El sistema satisface todas las especificaciones de negocio (SRS), garantizando cero pérdida de actas en campo, estricta trazabilidad de repuestos hospitalarios y total conformidad operativa previa a la sustentación.", sz=19, space_after=120))
    
    # Firmas
    body.append(p("CONFORMIDAD DEL EQUIPO EVALUADOR", bold=True, color="1F497D", sz=20, align="center", space_before=120, space_after=60))
    firmas = [
        [tc("José Mauro Gutiérrez Araujo\nLíder de Proyecto / Product Owner\nScrum Master", 4300, align="center", bold=True),
         tc("Jorge Stevie Espejo Mogollón\nIngeniero de Software\nFullstack Developer", 4400, align="center", bold=True),
         tc("Deyvid Xander Gamboa Alva\nIngeniero de Datos\nData & QA Engineer", 4300, align="center", bold=True)]
    ]
    body.append(create_table(firmas, [4300, 4400, 4300]))
    body.append('<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>')
    
    save_document('docs/Informe_Pruebas_Funcionales_Fildlab.docx', ''.join(body))

if __name__ == '__main__':
    print("Iniciando generación de los tres documentos de calidad...")
    generar_plan_pruebas()
    generar_informe_pruebas_unitarias()
    generar_informe_pruebas_funcionales()
    print("¡Los tres documentos formales han sido generados exitosamente en la carpeta docs/!")

import zipfile
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils

def escape(t):
    return saxutils.escape(str(t))

def create_cell(text, width=2822, fill=None, bold=False, align="left", text_color="000000"):
    lines = text.split('\n')
    tc = ['<w:tc>']
    tc.append(f'<w:tcPr><w:tcW w:type="dxa" w:w="{width}"/>')
    if fill:
        tc.append(f'<w:shd w:fill="{fill}"/>')
    tc.append('<w:tcMar><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:left w:w="140" w:type="dxa"/><w:right w:w="140" w:type="dxa"/></w:tcMar>')
    tc.append('</w:tcPr>')
    
    for line in lines:
        tc.append('<w:p>')
        if align != "left":
            tc.append(f'<w:pPr><w:jc w:val="{align}"/></w:pPr>')
        tc.append('<w:r>')
        tc.append('<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>')
        if bold:
            tc.append('<w:b/>')
        tc.append(f'<w:color w:val="{text_color}"/><w:sz w:val="18"/></w:rPr>')
        tc.append(f'<w:t>{escape(line)}</w:t>')
        tc.append('</w:r></w:p>')
    tc.append('</w:tc>')
    return ''.join(tc)

def build_sprint2_docx():
    src_docx = 'docs/Sprint_1_Scrum_Kanban_Fildlab.docx'
    dst_docx = 'docs/Sprint_2_Scrum_Kanban_Fildlab.docx'
    
    # Read original document.xml to see body tags
    with zipfile.ZipFile(src_docx, 'r') as zin:
        xml_content = zin.read('word/document.xml').decode('utf-8')
        all_files = {name: zin.read(name) for name in zin.namelist()}
        
    # We will build a new document.xml for Sprint 2
    # Notice the user image format: SPRINT | HACER | EN ESPERA | HACIENDO | TERMINADO
    body = []
    body.append('<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:color w:val="0F2043"/><w:sz w:val="22"/></w:rPr><w:t>PROYECTO: SISTEMA DE INFORMACIÓN PARA LA GESTIÓN INTEGRAL DE EQUIPOS DE TRATAMIENTO DE AGUA EN LA EMPRESA FILDLAB PERÚ S.A.C.</w:t></w:r></w:p>')
    body.append('<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:color w:val="46505F"/><w:sz w:val="20"/></w:rPr><w:t>TABLERO KANBAN / SCRUM – SPRINT 2 (SEMANA 5)</w:t><w:br/><w:t>Periodo de Ejecución: 21/09/2026 al 25/09/2026 (Lunes a Viernes)</w:t></w:r></w:p>')
    body.append('<w:p><w:pPr><w:spacing w:after="80"/></w:pPr></w:p>')
    
    # Table start
    body.append('<w:tbl><w:tblPr><w:tblW w:type="auto" w:w="0"/><w:jc w:val="center"/><w:tblLayout w:type="fixed"/><w:tblLook w:firstColumn="1" w:firstRow="1" w:lastColumn="0" w:lastRow="0" w:noHBand="0" w:noVBand="1" w:val="04A0"/><w:tblBorders><w:top w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/><w:left w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/><w:bottom w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/><w:right w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="DCDCDC"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="DCDCDC"/></w:tblBorders></w:tblPr>')
    body.append('<w:tblGrid><w:gridCol w:w="2400"/><w:gridCol w:w="3000"/><w:gridCol w:w="2600"/><w:gridCol w:w="3000"/><w:gridCol w:w="3200"/></w:tblGrid>')
    
    # Header row: SPRINT | HACER | EN ESPERA | HACIENDO | TERMINADO
    body.append('<w:tr>')
    headers = [
        ('SPRINT / DÍA', 2400),
        ('HACER (To Do)', 3000),
        ('EN ESPERA / BLOQUEOS', 2600),
        ('HACIENDO (In Progress)', 3000),
        ('TERMINADO (Done)', 3200)
    ]
    for h_name, w in headers:
        body.append(f'<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="{w}"/><w:shd w:fill="1F497D"/><w:tcMar><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:left w:w="140" w:type="dxa"/><w:right w:w="140" w:type="dxa"/></w:tcMar></w:tcPr><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="19"/></w:rPr><w:t>{escape(h_name)}</w:t></w:r></w:p></w:tc>')
    body.append('</w:tr>')
    
    sprint2_days = [
        {
            "sprint": "Sprint 2 – Lunes 21/09/2026",
            "hacer": "• [José Mauro] Planificar Sprint 2; priorizar módulos transaccionales restantes de Fase 3.1 y arquitectura Fase 3.2.\n• [Jorge] Desarrollar módulos backend y frontend de Inventario (3.1.4), Ventas (3.1.3), Equipos (3.1.5) y Liquidación (3.1.6).\n• [Deyvid] Redactar especificación y plan técnico de la PWA de campo; configurar scaffolding Vite y esquema Dexie.",
            "en_espera": "• [Jorge] En espera de aprobación gerencial del flujo de emisión de adendas administrativas sin alterar actas (RN-04).",
            "haciendo": "• [José Mauro] Definir reglas de salidas atómicas de inventario y congelamiento de actas inmutables firmadas.\n• [Jorge] Programar lógica de stock central, ventas con rebaja automática y adendas de corrección vinculadas al acta.\n• [Deyvid] Modelar tablas locales en Dexie.js (catalogo_clientes, catalogo_equipos, ordenes_locales, outbox_pendientes).",
            "terminado": "• [José Mauro] Fase 3.1 de la Plataforma Web Central completada y aprobada al 100%.\n• [Jorge] Módulos de Inventario, Ventas, Equipos y Liquidación/Adendas operativos en API y Web.\n• [Deyvid] Scaffolding de la PWA de campo inicializado con esquema Dexie y plan de Fase 3.2 formalizado."
        },
        {
            "sprint": "Sprint 2 – Martes 22/09/2026",
            "hacer": "• [José Mauro] Validar requerimientos de campo: catálogo offline, turno de 12h, stock móvil y lectura de 8 parámetros.\n• [Jorge] Implementar componentes PWA: OrdenForm, lecturas de agua, firma digital DPR=2, GPS y Outbox TanStack Query.\n• [Deyvid] Implementar sincronización secuencial en backend con hash SHA-256 encadenado (tamper-evident ledger).",
            "en_espera": "• [Jorge] En espera de pruebas de estrés en condiciones de desconexión abrupta de red 4G/WiFi en salas hospitalarias.",
            "haciendo": "• [José Mauro] Supervisar calibración de canvas táctil (DPR=2) para evitar desbordamiento de memoria en Galaxy A14.\n• [Jorge] Resolver incidencias de recorte de firma, órdenes huérfanas y manejo de carreras concurrentes 409.\n• [Deyvid] Blindar servicio de sincronización backend con lock atómico por equipo y validación estricta de coordenadas GPS.",
            "terminado": "• [José Mauro] Flujo completo de orden en campo validado: 8 parámetros + canvas DPR=2 + GPS + Outbox resiliente.\n• [Jorge] PWA de campo offline-first 100% funcional; stock móvil con descuento local y cierre bloqueante (RN-02).\n• [Deyvid] Hash criptográfico encadenado SHA-256 verificado en Neon PostgreSQL (cero adulteración legal)."
        },
        {
            "sprint": "Sprint 2 – Miércoles 23/09/2026",
            "hacer": "• [José Mauro] Gestionar despliegue cloud integral de la solución (Fase 3.3) y personalización visual con marca oficial.\n• [Jorge] Desplegar PWA en Cloudflare Pages (fildlab-pwa.pages.dev) y backend en Render con Dockerfile optimizado.\n• [Deyvid] Adaptar branding corporativo de Fildlab (logos oficiales, favicons, iconos PWA 192/512 y manifiesto web).",
            "en_espera": "• [Deyvid] En espera de confirmación de assets vectoriales de alta resolución por parte de Gerencia.",
            "haciendo": "• [José Mauro] Elaborar runbooks de despliegue paso a paso para plataforma administrativa y PWA en Cloudflare Pages.\n• [Jorge] Configurar directivas CORS seguras y variables de entorno de producción en Render y Cloudflare Pages.\n• [Deyvid] Generar paquete de iconos PWA maskable e integrar logotipo oficial en cabeceras web y móvil.",
            "terminado": "• [José Mauro] Runbooks de despliegue completados y archivados en docs/deploy/.\n• [Jorge] Ambas aplicaciones (fildlab-admin y fildlab-pwa) operativas en Cloudflare Pages y API Live en Render.\n• [Deyvid] Identidad de marca oficial de Fildlab Perú S.A.C. integrada en todo el ecosistema digital."
        },
        {
            "sprint": "Sprint 2 – Jueves 24/09/2026",
            "hacer": "• [José Mauro] Dirigir auditoría de aseguramiento de la calidad e integridad criptográfica bajo norma ISO/IEC 25010.\n• [Jorge] Ejecutar optimizaciones de rendimiento web/móvil y validar persistencia Outbox ante cortes de red forzados.\n• [Deyvid] Ejecutar batería completa de pruebas unitarias en backend (pytest) y frontend (vitest); auditar cold starts.",
            "en_espera": "• Ninguno (entorno de pruebas y producción estabilizado sin incidencias externas).",
            "haciendo": "• [José Mauro] Validar métricas de tiempo de respuesta (RNF-01 < 3s, RNF-02 < 2s sobre Samsung Galaxy A14).\n• [Jorge] Auditar inmutabilidad de actas ante intentos de inyección de datos o modificación de consumibles.\n• [Deyvid] Medir tiempos de arranque en frío de Render; verificar endpoint /api/v1/healthz con monitoreo activo.",
            "terminado": "• [José Mauro] Evaluación de calidad ISO/IEC 25010 aprobada con alta conformidad en fiabilidad y rendimiento.\n• [Jorge] Cero pérdida de órdenes técnicas verificado en Outbox tras desconexión forzada; ledger íntegro.\n• [Deyvid] Suite de 365 pruebas automatizadas ejecutadas con 100% de éxito; cold starts controlados en < 2.5s."
        },
        {
            "sprint": "Sprint 2 – Viernes 25/09/2026",
            "hacer": "• [José Mauro] Consolidar Guía de Exposición del proyecto, tableros Kanban/Scrum y métricas de avance de la EDT.\n• [Jorge] Diagnosticar y resolver problema en la pila de navegación de la PWA (stack de rutas trabado al volver de órdenes).\n• [Deyvid] Realizar pulido estético final en la interfaz web y PWA (micro-animaciones, contraste, diseño visual premium).",
            "en_espera": "• Ninguno (cierre formal y exitoso del Sprint 2).",
            "haciendo": "• [José Mauro] Preparar argumentación técnica para defensa ante jurado (PWA vs nativa, IndexedDB, SHA-256).\n• [Jorge] Desacoplar navegación en PWA para asegurar transiciones instantáneas y libres de bloqueos.\n• [Deyvid] Aplicar diseño responsivo de alta fidelidad, componentes visuales elegantes y retroalimentación interactiva.",
            "terminado": "• [José Mauro] Guía de Exposición y tablero Scrum finalizados; Fase 3 (Núcleo Transaccional) cerrada al 100%.\n• [Jorge] Pila de navegación de la PWA completamente fluida y sin bloqueos en cualquier dispositivo.\n• [Deyvid] Estética web y móvil elevada a estándar premium con experiencia de usuario ágil y moderna."
        }
    ]

    for d in sprint2_days:
        body.append('<w:tr>')
        body.append(create_cell(d['sprint'], width=2400, fill="F2F4F7", bold=True, align="center"))
        body.append(create_cell(d['hacer'], width=3000))
        body.append(create_cell(d['en_espera'], width=2600, fill="FFF8DC"))
        body.append(create_cell(d['haciendo'], width=3000))
        body.append(create_cell(d['terminado'], width=3200, fill="F0FFF0"))
        body.append('</w:tr>')
        
    body.append('</w:tbl>')
    
    # Footer team
    body.append('<w:p><w:pPr><w:spacing w:before="120"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:color w:val="1F497D"/><w:sz w:val="18"/></w:rPr><w:t>Equipo de Trabajo: José Mauro Gutiérrez Araujo (Líder de Proyecto / Product Owner &amp; Scrum Master) | Jorge Stevie Espejo Mogollón (Fullstack Dev) | Deyvid Xander Gamboa Alva (Data &amp; QA Engineer)</w:t></w:r></w:p>')
    body.append('<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>')
    
    # Wrap in standard docx document xml
    header_xml = '''<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:mv="urn:schemas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 wp14"><w:body>'''
    
    full_doc_xml = header_xml + ''.join(body) + '</w:body></w:document>'
    
    all_files['word/document.xml'] = full_doc_xml.encode('utf-8')
    
    with zipfile.ZipFile(dst_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for fname, content in all_files.items():
            zout.writestr(fname, content)
            
    print(f"Generated {dst_docx} successfully")

if __name__ == '__main__':
    build_sprint2_docx()

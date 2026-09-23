"""Script para generar el documento Word (.docx) formal del Tablero Scrum / Kanban
para el Sprint 1 (Lunes 14/09/2026 al Domingo 20/09/2026) del proyecto Fildlab.
"""

from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DOCS_DIR = Path(r"c:\Users\Mauro\Proyectos\Fildlab\docs")
OUTPUT_PATH = DOCS_DIR / "Sprint_1_Scrum_Kanban_Fildlab.docx"

DIAS_DATA = [
    {
        "dia": "Sprint 1 — Lunes 14/09/2026",
        "hacer": (
            "• [José Mauro] Priorizar el Product Backlog del Sprint 1; estructurar el tablero Kanban en Notion.\n\n"
            "• [Jorge] Inicializar repositorio en GitHub; estructurar el cascarón backend en Python 3.12 / FastAPI y frontend en Vite + React 18 + TS.\n\n"
            "• [Deyvid] Diseñar el esquema relacional en Neon PostgreSQL para clientes corporativos, contratos, SLA."
        ),
        "haciendo": (
            "• [José Mauro] Liderar la sesión de planificación del Sprint 1; alinear requerimientos REQ-01 a REQ-03.\n\n"
            "• [Jorge] Configurar entorno virtual (.venv), dependencias base (pyproject.toml, FastAPI, SQLAlchemy, Tailwind).\n\n"
            "• [Deyvid] Mapear los campos del RUC (once dígitos), tipos de ósmosis inversa e insumos de Fildlab."
        ),
        "espera": (
            "• [Jorge] A la espera de confirmación de acceso a la rama de desarrollo en Neon PostgreSQL."
        ),
        "terminado": (
            "• [José Mauro] Acta de planificación del Sprint 1 formalizada junto con el equipo.\n\n"
            "• [Jorge] Entorno local inicializado con repositorio Git en GitHub configurado en ramas principales.\n\n"
            "• [Deyvid] Diccionario preliminar de datos para clientes corporativos y contratos completado."
        ),
    },
    {
        "dia": "Sprint 1 — Martes 15/09/2026",
        "hacer": (
            "• [José Mauro] Validar con Gerencia (Elva Acevedo) los formatos digitales de contratos con clínicas y niveles de SLA.\n\n"
            "• [Jorge] Desarrollar endpoints CRUD para gestión de clientes corporativos (REQ-01) y autenticación RBAC con Argon2 + JWT.\n\n"
            "• [Deyvid] Redactar scripts de migración con Alembic; configurar suite de pruebas automatizadas con pytest-asyncio."
        ),
        "haciendo": (
            "• [José Mauro] Especificar reglas de negocio RN-01 (aprobación gerencial de contratos) y RN-03 (trazabilidad).\n\n"
            "• [Jorge] Programar algoritmo de validación del RUC de once dígitos; controlar campos obligatorios (422/409).\n\n"
            "• [Deyvid] Desplegar la base de datos en Neon PostgreSQL; ejecutar migraciones automáticas iniciales."
        ),
        "espera": (
            "• [Deyvid] A la espera del catálogo definitivo de filtros, membranas y resinas provisto por Gerencia."
        ),
        "terminado": (
            "• [José Mauro] Matriz de reglas de negocio para contratos documentada formalmente.\n\n"
            "• [Jorge] Endpoints RESTful de autenticación y clientes probados en entorno de desarrollo local.\n\n"
            "• [Deyvid] Tablas maestras de usuarios, clientes y contratos creadas en el motor de base de datos Neon."
        ),
    },
    {
        "dia": "Sprint 1 — Miércoles 16/09/2026",
        "hacer": (
            "• [José Mauro] Realizar control de avance frente a la EDT; detectar posibles desviaciones de tiempo o costo.\n\n"
            "• [Jorge] Construir interfaz web administrativa para los módulos de clientes, contratos y SLA (REQ-02, REQ-03).\n\n"
            "• [Deyvid] Elaborar casos de prueba unitaria para validar integridad de datos comerciales y validación de RUC."
        ),
        "haciendo": (
            "• [José Mauro] Redactar la sección de justificación técnica y análisis de riesgos para el informe de avance semanal.\n\n"
            "• [Jorge] Conectar la interfaz web de clientes y contratos con la API FastAPI mediante llamadas HTTP asíncronas.\n\n"
            "• [Deyvid] Ejecutar pruebas unitarias automatizadas sobre las funciones de validación de RUC y vigencia de contratos."
        ),
        "espera": (
            "• Ninguno (flujo de trabajo operativo sin bloqueos externos)."
        ),
        "terminado": (
            "• [José Mauro] Verificación de avance técnico completada sin desviaciones críticas de cronograma.\n\n"
            "• [Jorge] Formulario web y vistas de registro de clientes totalmente operativos con validaciones activas.\n\n"
            "• [Deyvid] Batería de pruebas unitarias ejecutada con 100% de aserciones aprobadas sin fallos."
        ),
    },
    {
        "dia": "Sprint 1 — Jueves 17/09/2026",
        "hacer": (
            "• [José Mauro] Validar requerimientos de campo para la PWA de técnicos (RN-02: 8 parámetros de agua, firma y GPS).\n\n"
            "• [Jorge] Implementar almacenamiento local con Dexie.js (IndexedDB) en la PWA para soporte offline (REQ-06, REQ-10).\n\n"
            "• [Deyvid] Diseñar la matriz de aseguramiento de la calidad bajo el estándar internacional ISO/IEC 25010."
        ),
        "haciendo": (
            "• [José Mauro] Especificar protocolo de trazabilidad de repuestos en campo en dos fases (RN-03: descuento local inmediato).\n\n"
            "• [Jorge] Configurar el Service Worker (vite-plugin-pwa) para almacenamiento en caché local de vistas operativas.\n\n"
            "• [Deyvid] Simular escenarios de pérdida de conectividad en campo para validar la persistencia local en Dexie.js."
        ),
        "espera": (
            "• [Jorge] En espera de confirmación de dimensiones fijas del canvas táctil para evitar recortes en Samsung Galaxy A14."
        ),
        "terminado": (
            "• [José Mauro] Protocolo de captura técnica en campo (8 parámetros + canvas DPR=2 + GPS) formalizado.\n\n"
            "• [Jorge] Mecanismo de persistencia local en Dexie.js funcionando correctamente en navegador móvil.\n\n"
            "• [Deyvid] Matriz de aseguramiento de la calidad bajo el estándar ISO/IEC 25010 diseñada y aprobada."
        ),
    },
    {
        "dia": "Sprint 1 — Viernes 18/09/2026",
        "hacer": (
            "• [José Mauro] Supervisar pre-requisitos de infraestructura cloud bajo política de S/. 0.00 (Free Tier / Open Source).\n\n"
            "• [Jorge] Construir Dockerfile multi-stage optimizado para 512 MB de RAM y desplegar la API en Render.\n\n"
            "• [Deyvid] Ejecutar migración de producción en Neon PostgreSQL (alembic upgrade head); auditar conexión con pooler."
        ),
        "haciendo": (
            "• [José Mauro] Validar variables de entorno de producción (DATABASE_URL, JWT_SECRET) sin credenciales en el repositorio.\n\n"
            "• [Jorge] Configurar middleware CORS en FastAPI permitiendo orígenes *.pages.dev y healthcheck en /api/v1/healthz.\n\n"
            "• [Deyvid] Auditar el entorno cloud desplegado en Render; verificar cifrado HTTPS y TLS 1.3 de extremo a extremo."
        ),
        "espera": (
            "• Ninguno (despliegues de backend y base de datos ejecutados de forma fluida)."
        ),
        "terminado": (
            "• [José Mauro] Infraestructura en la nube Free Tier validada con costo S/. 0.00 en licencias.\n\n"
            "• [Jorge] Ecosistema backend desplegado en Render en estado Live, operando bajo protocolo seguro HTTPS.\n\n"
            "• [Deyvid] Base de datos Neon de producción migrada con todas las tablas maestras e índices de integridad."
        ),
    },
    {
        "dia": "Sprint 1 — Sábado 19/09/2026",
        "hacer": (
            "• [José Mauro] Consolidar datos de clientes reales (Bermalab, Escalabs, Sano del Norte, Detectalab, Inkamay) para validación.\n\n"
            "• [Jorge] Desplegar los dos proyectos en Cloudflare Pages (frontend administrativo y pwa de campo) con dominios *.pages.dev.\n\n"
            "• [Deyvid] Medir tiempos de respuesta en consultas de clientes (RNF-01: < 3s) y rendimiento en móviles (RNF-02: < 2s)."
        ),
        "haciendo": (
            "• [José Mauro] Coordinar la población de datos simulados en producción con los rangos químicos exactos de agua clínica.\n\n"
            "• [Jorge] Verificar reglas de enrutamiento SPA (_redirects) y compatibilidad de instalación PWA en dispositivos móviles.\n\n"
            "• [Deyvid] Ejecutar pruebas de humo e integración cruzada entre Cloudflare Pages y la API en Render."
        ),
        "espera": (
            "• Ninguno (pruebas en entorno real ejecutándose según lo planificado)."
        ),
        "terminado": (
            "• [José Mauro] Base de datos de producción poblada con 5 empresas clínicas y 10 equipos de tratamiento de agua.\n\n"
            "• [Jorge] Ambas aplicaciones web (fildlab-admin y fildlab-pwa) desplegadas y operativas en Cloudflare Pages.\n\n"
            "• [Deyvid] Registro de rendimiento obtenido: consultas en 1.1s promedio en web y < 1.8s en PWA (cumple RNF-01 y RNF-02)."
        ),
    },
    {
        "dia": "Sprint 1 — Domingo 20/09/2026",
        "hacer": (
            "• [José Mauro] Consolidar métricas de gestión de valor ganado (EVM: SPI, CPI) para el Primer Informe de Estado (Semana 4).\n\n"
            "• [Jorge] Documentar los runbooks de despliegue (docs/deploy/) y verificar documentación interactiva OpenAPI/Swagger.\n\n"
            "• [Deyvid] Elaborar el Reporte final de Aseguramiento de Calidad del Sprint 1 y verificar ausencia de defectos bloqueantes."
        ),
        "haciendo": (
            "• [José Mauro] Dirigir la sesión de Sprint Review (demostración funcional) y la Retrospectiva del Sprint con el equipo.\n\n"
            "• [Jorge] Realizar limpieza final de ramas Git; consolidar merge a la rama principal main en GitHub.\n\n"
            "• [Deyvid] Consolidar matriz de trazabilidad de requerimientos (REQ-01 a REQ-03, REQ-06, REQ-10, RNF-01 a RNF-05)."
        ),
        "espera": (
            "• Ninguno (cierre formal y exitoso del Sprint 1)."
        ),
        "terminado": (
            "• [José Mauro] Sprint Review y Retrospective concluidas con visto bueno del equipo; Primer Informe de Estado formalizado con SPI=1.0, CPI=1.0.\n\n"
            "• [Jorge] Código fuente consolidado en GitHub con suite completa de 365 pruebas automatizadas en verde.\n\n"
            "• [Deyvid] Reporte de aseguramiento de calidad del Sprint 1 aprobado sin defectos bloqueantes y con conformidad ISO/IEC 25010."
        ),
    },
]


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_cell_background(cell, color_hex):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))


def main():
    doc = Document()

    # Configurar orientación Horizontal (Landscape) para tabla de 5 columnas
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    new_width, new_height = section.page_height, section.page_width
    section.page_width = new_width
    section.page_height = new_height
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.6)
    section.right_margin = Inches(0.6)

    # Título principal
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = title.add_run("PROYECTO: SISTEMA DE INFORMACIÓN PARA LA GESTIÓN INTEGRAL DE EQUIPOS DE TRATAMIENTO DE AGUA EN LA EMPRESA FILDLAB PERÚ S.A.C.")
    r_title.bold = True
    r_title.font.size = Pt(11)
    r_title.font.name = "Arial"
    r_title.font.color.rgb = RGBColor(15, 32, 67)

    # Subtítulo / Metadatos
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = sub.add_run("TABLERO KANBAN / SCRUM — SPRINT 1 (SEMANA 4)\nPeriodo de Ejecución: 14/09/2026 al 20/09/2026 (Lunes a Domingo)")
    r_sub.bold = True
    r_sub.font.size = Pt(10)
    r_sub.font.name = "Arial"
    r_sub.font.color.rgb = RGBColor(70, 80, 95)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # Crear tabla: 5 columnas (SPRINT/DÍA, HACER, HACIENDO, EN ESPERA, TERMINADO)
    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Anchos de columnas en pulgadas (Total ~10.0 pulgadas para página horizontal de 11")
    col_widths = [Inches(1.8), Inches(2.2), Inches(2.2), Inches(1.6), Inches(2.2)]

    # Encabezados
    headers = ["SPRINT / DÍA", "HACER (To Do)", "HACIENDO (In Progress)", "EN ESPERA / BLOQUEOS", "TERMINADO (Done)"]
    hdr_cells = table.rows[0].cells
    for i, h_text in enumerate(headers):
        hdr_cells[i].width = col_widths[i]
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h_text)
        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(hdr_cells[i], "1F497D")  # Azul ejecutivo oscuro
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)

    # Filas de cada día (Lunes a Domingo)
    for row_idx, data in enumerate(DIAS_DATA):
        row_cells = table.add_row().cells
        bg_color = "F2F5F9" if row_idx % 2 == 1 else "FFFFFF"

        # Columna 1: Día
        row_cells[0].width = col_widths[0]
        p0 = row_cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r0 = p0.add_run(data["dia"])
        r0.bold = True
        r0.font.name = "Arial"
        r0.font.size = Pt(9)
        r0.font.color.rgb = RGBColor(31, 73, 125)
        set_cell_background(row_cells[0], "E8EEF5")
        set_cell_margins(row_cells[0], top=100, bottom=100, left=120, right=120)

        # Columnas 2 a 5: HACER, HACIENDO, EN ESPERA, TERMINADO
        content_cols = [data["hacer"], data["haciendo"], data["espera"], data["terminado"]]
        for col_i, text in enumerate(content_cols, start=1):
            cell = row_cells[col_i]
            cell.width = col_widths[col_i]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(text)
            r.font.name = "Arial"
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(40, 40, 40)
            set_cell_background(cell, bg_color)
            set_cell_margins(cell, top=100, bottom=100, left=120, right=120)

    # Añadir bordes limpios a la tabla
    tblPr = table._tbl.tblPr
    borders_xml = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>\n'
        f'  <w:top w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/>\n'
        f'  <w:left w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/>\n'
        f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/>\n'
        f'  <w:right w:val="single" w:sz="6" w:space="0" w:color="B0C4DE"/>\n'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="DCDCDC"/>\n'
        f'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="DCDCDC"/>\n'
        f'</w:tblBorders>'
    )
    tblPr.append(borders_xml)

    # Pie de página / Resumen de integrantes
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_foot = footer_p.add_run(
        "Equipo de Trabajo: José Mauro Gutiérrez Araujo (Líder de Proyecto / Product Owner & Scrum Master) | "
        "Jorge Stevie Espejo Mogollón (Fullstack Dev) | Deyvid Xander Gamboa Alva (Data & QA Engineer)"
    )
    r_foot.font.name = "Arial"
    r_foot.font.size = Pt(8.5)
    r_foot.font.italic = True
    r_foot.font.color.rgb = RGBColor(100, 100, 100)

    # Guardar documento
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT_PATH)
    print(f"[+] Documento generado exitosamente en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

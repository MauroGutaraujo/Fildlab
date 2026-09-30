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

def generate_report_docx(filename, title_sprint, revision_data, resumen_global, explicaciones, sustento, cambios, hitos_data, kpis_data, anexo1_data):
    src_docx = 'docs/Sprint_1_Scrum_Kanban_Fildlab.docx'
    with zipfile.ZipFile(src_docx, 'r') as zin:
        all_files = {name: zin.read(name) for name in zin.namelist()}
        
    body = []
    # Header
    body.append(p("FILDLAB PERÚ S.A.C.", bold=True, color="1F497D", sz=24, align="center", space_after=40))
    body.append(p("Grupo 2 - capstone", italic=True, color="555555", sz=20, align="center", space_after=120))
    body.append(p("INFORME DE ESTADO DEL PROYECTO", bold=True, color="000000", sz=26, align="center", space_after=60))
    body.append(p(f"SISTEMA DE INFORMACIÓN PARA LA GESTIÓN INTEGRAL DE EQUIPOS DE TRATAMIENTO DE AGUA EN LA EMPRESA FILDLAB PERÚ S.A.C. – {title_sprint.upper()}", bold=True, color="1F497D", sz=20, align="center", space_after=180))
    
    # Registro de revision
    body.append(p("Registro de Revisión", bold=True, color="1F497D", sz=22, space_after=60))
    rev_rows = [
        [tc("Revisión", 1600, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Fecha", 1800, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Modificaciones", 5000, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Autor", 4600, fill="1F497D", bold=True, color="FFFFFF")]
    ]
    for r in revision_data:
        rev_rows.append([
            tc(r[0], 1600, align="center", bold=True),
            tc(r[1], 1800, align="center"),
            tc(r[2], 5000),
            tc(r[3], 4600)
        ])
    body.append(create_table(rev_rows, [1600, 1800, 5000, 4600]))
    
    # 1. Descripcion
    body.append(p("1. Descripción del proyecto", bold=True, color="1F497D", sz=22, space_after=60, space_before=100))
    body.append(p("Desarrollo e implementación de un Sistema de Información (plataforma web central, aplicación móvil PWA con soporte offline para técnicos, módulo de Inteligencia de Negocios - BI y modelo predictivo de Inteligencia Artificial) para automatizar la gestión integral de ventas, contratos, mantenimiento de equipos de tratamiento de agua e inventarios de la empresa Fildlab Perú S.A.C., erradicando las penalizaciones por SLA a menos del 2%.", sz=19, space_after=120))
    
    # 2. Resumen
    body.append(p("2. Resumen del estado del proyecto", bold=True, color="1F497D", sz=22, space_after=60, space_before=100))
    body.append(p("a. Estado Global", bold=True, color="333333", sz=20, space_after=60))
    
    # Global state cards
    status_row = [
        tc(f"Alcance\n{resumen_global['alcance_val']}", 4300, fill=resumen_global['alcance_color'], bold=True, align="center", sz=22),
        tc(f"Tiempo\n{resumen_global['tiempo_val']}", 4400, fill=resumen_global['tiempo_color'], bold=True, align="center", sz=22),
        tc(f"Costo\n{resumen_global['costo_val']}", 4300, fill=resumen_global['costo_color'], bold=True, align="center", sz=22)
    ]
    body.append(create_table([status_row], [4300, 4400, 4300]))
    
    body.append(p("b. Explicaciones:", bold=True, color="333333", sz=20, space_after=60))
    for exp in explicaciones:
        body.append(p(f"• {exp}", sz=19, space_after=60))
        
    # 3. Sustento
    body.append(p("3. Sustento del estado del proyecto", bold=True, color="1F497D", sz=22, space_after=60, space_before=100))
    body.append(p(sustento, sz=19, space_after=120))
    
    # 4. Cambios principales
    body.append(p("4. Cambios principales ocurridos desde el último reporte emitido", bold=True, color="1F497D", sz=22, space_after=60, space_before=100))
    for c in cambios:
        body.append(p(f"• {c}", sz=19, space_after=60))
        
    # 5. Hitos y entregables
    body.append(p("5. Hitos y entregables del proyecto (semana/mes actual y siguiente)", bold=True, color="1F497D", sz=22, space_after=60, space_before=100))
    hitos_rows = [
        [tc("Código EDT", 1500, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Actividad", 3200, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Entregable", 3800, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Fecha Plan.", 1800, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Fecha Real", 1800, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Estado", 1900, fill="1F497D", bold=True, color="FFFFFF", align="center")]
    ]
    for h in hitos_data:
        st_fill = "D4EDDA" if "Completado" in h[5] else ("FFF3CD" if "desarrollo" in h[5] or "curso" in h[5] else "E2E3E5")
        hitos_rows.append([
            tc(h[0], 1500, align="center", bold=True),
            tc(h[1], 3200),
            tc(h[2], 3800),
            tc(h[3], 1800, align="center"),
            tc(h[4], 1800, align="center"),
            tc(h[5], 1900, fill=st_fill, align="center", bold=True)
        ])
    body.append(create_table(hitos_rows, [1500, 3200, 3800, 1800, 1800, 1900]))
    
    # 6. KPIs
    body.append(p("6. Indicadores Clave de Desempeño (KPI's)", bold=True, color="1F497D", sz=22, space_after=60, space_before=100))
    body.append(p(f"• Tiempo: {kpis_data['tiempo']}", sz=19, space_after=60))
    body.append(p(f"• Costo: {kpis_data['costo']}", sz=19, space_after=120))
    
    # Anexo 1
    body.append(p("Anexo 1: Detalle de validación de indicadores", bold=True, color="1F497D", sz=22, space_after=60, space_before=120))
    body.append(p("Detalle de validación del alcance", bold=True, color="333333", sz=20, space_after=60))
    alc_rows = [
        [tc("Actividad", 5000, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Entregable", 6000, fill="1F497D", bold=True, color="FFFFFF"),
         tc("% Cumplimiento", 2000, fill="1F497D", bold=True, color="FFFFFF", align="center")]
    ]
    for item in anexo1_data['alcance_items']:
        alc_rows.append([tc(item[0], 5000), tc(item[1], 6000), tc(item[2], 2000, align="center", bold=True)])
    alc_rows.append([tc("Cumplimiento Promedio", 11000, bold=True, align="right"), tc(anexo1_data['alcance_promedio'], 2000, bold=True, align="center", fill="E6EEF8")])
    body.append(create_table(alc_rows, [5000, 6000, 2000]))
    
    body.append(p("Detalle de validación del tiempo", bold=True, color="333333", sz=20, space_after=60))
    time_rows = [
        [tc("Actividad", 6500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Duración Estimada", 3200, fill="1F497D", bold=True, color="FFFFFF", align="center"),
         tc("Duración Real", 3300, fill="1F497D", bold=True, color="FFFFFF", align="center")]
    ]
    for item in anexo1_data['tiempo_items']:
        time_rows.append([tc(item[0], 6500), tc(item[1], 3200, align="center"), tc(item[2], 3300, align="center")])
    time_rows.append([tc("Cumplimiento promedio", 6500, bold=True, align="right"), tc(anexo1_data['tiempo_promedio'], 6500, bold=True, align="center", fill="E6EEF8")])
    body.append(create_table(time_rows, [6500, 3200, 3300]))
    
    body.append(p("Detalle de validación de costos", bold=True, color="333333", sz=20, space_after=60))
    cost_rows = [
        [tc("Actividad", 6500, fill="1F497D", bold=True, color="FFFFFF"),
         tc("Valor Planificado", 3200, fill="1F497D", bold=True, color="FFFFFF", align="right"),
         tc("Costo Real", 3300, fill="1F497D", bold=True, color="FFFFFF", align="right")]
    ]
    for item in anexo1_data['costo_items']:
        cost_rows.append([tc(item[0], 6500), tc(item[1], 3200, align="right"), tc(item[2], 3300, align="right")])
    cost_rows.append([tc("TOTAL", 6500, bold=True), tc(anexo1_data['costo_total_plan'], 3200, bold=True, align="right"), tc(anexo1_data['costo_total_real'], 3300, bold=True, align="right")])
    cost_rows.append([tc("Porcentaje de Variación", 6500, bold=True, align="right"), tc(anexo1_data['costo_variacion'], 6500, bold=True, align="center", fill="E6EEF8")])
    body.append(create_table(cost_rows, [6500, 3200, 3300]))
    
    # Anexo 2
    body.append(p("Anexo 2: Leyendas de interpretación de semáforos", bold=True, color="1F497D", sz=22, space_after=60, space_before=120))
    
    leyendas = [
        ("Leyenda del Alcance:", [
            ("Verde", "D4EDDA", "Los entregables correspondientes al periodo de evaluación se han completado (100%) en un porcentaje mayor o igual al 75% del total evaluado."),
            ("Amarillo", "FFF3CD", "Los entregables correspondientes al periodo de evaluación se han completado (100%) en un porcentaje menor al 75%, pero mayor o igual al 50% del total evaluado."),
            ("Rojo", "F8D7DA", "Los entregables correspondientes al periodo de evaluación se han completado (100%) en un porcentaje menor al 50% del total evaluado.")
        ]),
        ("Leyenda del Tiempo:", [
            ("Verde", "D4EDDA", "Las actividades correspondientes al periodo de evaluación se han completado dentro del plazo previsto en un porcentaje mayor o igual al 75%."),
            ("Amarillo", "FFF3CD", "Las actividades correspondientes al periodo de evaluación se han completado dentro del plazo previsto en un porcentaje menor al 75%, pero mayor o igual al 50%."),
            ("Rojo", "F8D7DA", "Las actividades correspondientes al periodo de evaluación se han completado dentro del plazo previsto en un porcentaje menor al 50%.")
        ]),
        ("Leyenda del Costo:", [
            ("Verde", "D4EDDA", "El costo real de las actividades correspondientes al periodo de evaluación es menor o igual al 100% del costo presupuestado."),
            ("Amarillo", "FFF3CD", "El costo real de las actividades correspondientes al periodo de evaluación es mayor al 100% del costo presupuestado, pero menor o igual al 110%."),
            ("Rojo", "F8D7DA", "El costo real de las actividades correspondientes al periodo de evaluación es mayor al 110% del costo presupuestado.")
        ])
    ]
    for l_title, l_items in leyendas:
        body.append(p(l_title, bold=True, color="333333", sz=20, space_after=40))
        l_rows = [[tc("Código de color", 2200, fill="1F497D", bold=True, color="FFFFFF", align="center"),
                   tc("Significado", 10800, fill="1F497D", bold=True, color="FFFFFF")]]
        for color_name, bg, desc in l_items:
            l_rows.append([tc(color_name, 2200, fill=bg, align="center", bold=True), tc(desc, 10800)])
        body.append(create_table(l_rows, [2200, 10800]))

    # Wrap in docx
    header_xml = '''<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:mv="urn:schemas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 wp14"><w:body>'''
    full_doc = header_xml + ''.join(body) + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'
    
    all_files['word/document.xml'] = full_doc.encode('utf-8')
    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zout:
        for fname, content in all_files.items():
            zout.writestr(fname, content)
    print(f"Generated {filename}")

def build_all():
    # SPRINT 1
    generate_report_docx(
        filename='docs/Informe_Estado_Proyecto_Sprint_1_Fildlab.docx',
        title_sprint='Sprint 1 (Semana 4)',
        revision_data=[
            ("v.1.0", "19/09/2026", "Emisión del primer informe de estado del proyecto (Cierre del Sprint 1 / Semana 4)", "Gutierrez Araujo, J. Mauro; Gamboa Alva, Deyvid X.; Espejo Mogollón, Jorge S.")
        ],
        resumen_global={
            'alcance_val': '80%', 'alcance_color': 'D4EDDA',
            'tiempo_val': '66%', 'tiempo_color': 'FFF3CD',
            'costo_val': '100%', 'costo_color': 'D4EDDA'
        },
        explicaciones=[
            "Respecto al Alcance: El indicador está en Verde. Aplicando el criterio de cumplimiento binario por entregable (100% si fue aceptado, 0% si aún no), el promedio alcanza el 80%: los 8 entregables de la Fase 1 (Inicio y Planificación) y la Fase 2 (Gestión y Arquitectura) fueron aceptados en su totalidad; los 2 entregables en curso de la Fase 3 (plataforma web central y PWA de campo) siguen en desarrollo y se contabilizan en 0%.",
            "Respecto al Tiempo: El indicador está en Amarillo debido a que las actividades completadas dentro del plazo establecido alcanzan el 66%, reflejando ligeras demoras operativas en la consolidación de los diseños de arquitectura técnica y las matrices de riesgo, responsabilidades y comunicaciones.",
            "Respecto al Costo: El indicador está en Verde, debido a que el costo real de las actividades ejecutadas se ajusta exactamente al presupuesto total de mano de obra planificado para las Fases 1 y 2 (S/. 50,000.00)."
        ],
        sustento="Los resultados demuestran un control financiero impecable y un avance sólido en la estructuración del proyecto Fildlab. Al cierre del Sprint 1 (Semana 4), se han aprobado y aceptado en su totalidad (100%) los 8 entregables planificados: Acta de Constitución, Business Case, SRS v2.2, EDT y cronograma, plan de desarrollo, matrices de riesgos, de responsabilidades y de comunicaciones, sin incurrir en desviaciones presupuestarias. Bajo el criterio binario de cumplimiento, el alcance global del proyecto se ubica en 80%, ya que los entregables de la Fase 3 (plataforma web central y PWA de campo) siguen en desarrollo y aún no han sido aceptados. Aunque el rendimiento en el cronograma se mantiene en alerta amarilla (66%) por ajustes metodológicos del curso Capstone, la ejecución del presupuesto se mantiene rigurosamente dentro de lo previsto.",
        cambios=[
            "Actualización formal del presupuesto global de mano de obra del proyecto a S/. 50,000.00.",
            "Refinamiento de la versión v2.2 del Documento de Requerimientos de Software (SRS) con validación de la firma digital manuscrita en canvas (Ley N° 27269).",
            "Aprobación de la política de infraestructura cloud Free Tier (costo S/. 0.00 en licencias) utilizando Render, Neon PostgreSQL y Cloudflare Pages."
        ],
        hitos_data=[
            ("1.1", "Formalizar el proyecto", "Acta de Constitución del Proyecto aprobada", "04/09/2026", "04/09/2026", "Completado"),
            ("1.2", "Especificar requerimientos", "Documento de Requerimientos de Software (SRS) aprobado", "04/09/2026", "04/09/2026", "Completado"),
            ("1.3", "Planificar el alcance", "EDT y Cronograma general aprobados", "04/09/2026", "04/09/2026", "Completado"),
            ("2.1", "Consolidar planes de desarrollo", "Plan de desarrollo aprobado", "11/09/2026", "11/09/2026", "Completado"),
            ("2.2", "Diseñar la solución técnica", "Arquitectura cloud, modelo relacional y prototipos de interfaz aprobados", "11/09/2026", "11/09/2026", "Completado"),
            ("2.3", "Gestionar riesgos", "Matriz de riesgos aprobada", "11/09/2026", "11/09/2026", "Completado"),
            ("2.4", "Asignar responsabilidades", "Matriz de responsabilidades aprobada", "11/09/2026", "11/09/2026", "Completado"),
            ("2.5", "Planificar comunicaciones", "Matriz de comunicaciones aprobada", "11/09/2026", "11/09/2026", "Completado"),
            ("3.1", "Desarrollar plataforma web central", "Plataforma web central (módulos clientes y contratos) operativa", "19/09/2026", "En desarrollo", "En curso"),
            ("3.2", "Desarrollar PWA de campo", "PWA de campo (arquitectura offline Dexie.js) operativa", "19/09/2026", "En desarrollo", "En curso")
        ],
        kpis_data={
            'tiempo': "El proyecto está retrasado con respecto al cronograma. Schedule Variance (SV): S/. -17,000.00 (retraso equivalente a S/. 17,000.00 en valor de trabajo no ejecutado dentro del plazo previsto). Schedule Performance Index (SPI): 0.66 (al ser menor a 1.0, evidencia que el rendimiento temporal del cronograma se encuentra al 66% de lo exigido, coincidiendo con el porcentaje de actividades completadas a tiempo del Anexo 1).",
            'costo': "El proyecto está en línea con lo presupuestado. Cost Variance (CV): S/. 0.00 (no existen desviaciones monetarias negativas entre el trabajo realizado y los recursos invertidos). Cost Performance Index (CPI): 1.00 (confirma una eficiencia de costos perfecta)."
        },
        anexo1_data={
            'alcance_items': [
                ("1.1 Formalizar el proyecto", "Acta de constitución aprobada", "100%"),
                ("1.2 Especificar requerimientos", "Documento de requerimientos aprobado (SRS)", "100%"),
                ("1.3 Planificar el alcance", "EDT y Cronograma general aprobados", "100%"),
                ("2.1 Consolidar planes de desarrollo", "Plan de desarrollo aprobado", "100%"),
                ("2.2 Diseñar la solución técnica", "Arquitectura cloud, modelo relacional y prototipos de interfaz", "100%"),
                ("2.3 Gestionar riesgos", "Matriz de riesgos aprobada", "100%"),
                ("2.4 Asignar responsabilidades", "Matriz de responsabilidades aprobada", "100%"),
                ("2.5 Planificar comunicaciones", "Matriz de comunicaciones aprobada", "100%"),
                ("3.1 Desarrollar plataforma web central", "Plataforma web central (módulo inicial)", "0%"),
                ("3.2 Desarrollar PWA de campo", "PWA de campo (módulo inicial)", "0%")
            ],
            'alcance_promedio': "80%",
            'tiempo_items': [
                ("1.1 Formalizar el proyecto", "2 días", "2 días"),
                ("1.2 Especificar requerimientos (SRS)", "3 días", "3 días"),
                ("1.3 Planificar el alcance", "2 días", "2 días"),
                ("2.1 Consolidar planes de desarrollo", "3 días", "3 días"),
                ("2.2 Diseñar la solución técnica", "5 días", "6 días"),
                ("2.3 Gestionar riesgos", "2 días", "3 días"),
                ("2.4 Asignar responsabilidades", "2 días", "3 días"),
                ("2.5 Planificar comunicaciones", "2 días", "3 días")
            ],
            'tiempo_promedio': "66%",
            'costo_items': [
                ("1.1. Formalizar el proyecto", "S/. 5,000.00", "S/. 5,000.00"),
                ("1.2. Especificar requerimientos (SRS)", "S/. 6,000.00", "S/. 6,000.00"),
                ("1.3. Planificar el alcance", "S/. 4,000.00", "S/. 4,000.00"),
                ("2.1. Consolidar planes de desarrollo", "S/. 6,000.00", "S/. 6,000.00"),
                ("2.2. Diseñar la solución técnica", "S/. 12,000.00", "S/. 12,000.00"),
                ("2.3. Gestionar riesgos", "S/. 6,000.00", "S/. 6,000.00"),
                ("2.4. Asignar responsabilidades", "S/. 6,000.00", "S/. 6,000.00"),
                ("2.5. Planificar comunicaciones", "S/. 5,000.00", "S/. 5,000.00")
            ],
            'costo_total_plan': "S/. 50,000.00",
            'costo_total_real': "S/. 50,000.00",
            'costo_variacion': "100%"
        }
    )

    # SPRINT 2
    generate_report_docx(
        filename='docs/Informe_Estado_Proyecto_Sprint_2_Fildlab.docx',
        title_sprint='Sprint 2 (Semana 5)',
        revision_data=[
            ("v.2.0", "25/09/2026", "Emisión del segundo informe de estado del proyecto (Cierre del Sprint 2 / Cierre de Fase 3)", "Gutierrez Araujo, J. Mauro; Gamboa Alva, Deyvid X.; Espejo Mogollón, Jorge S.")
        ],
        resumen_global={
            'alcance_val': '100%', 'alcance_color': 'D4EDDA',
            'tiempo_val': '96%', 'tiempo_color': 'D4EDDA',
            'costo_val': '100%', 'costo_color': 'D4EDDA'
        },
        explicaciones=[
            "Respecto al Alcance: El indicador está en Verde con 100% de cumplimiento. Se culminaron satisfactoriamente todos los entregables de la Fase 3: la Plataforma Web Central completa (3.1), la PWA de Campo offline-first con captura de 8 parámetros de agua, firma digital DPR=2 y Outbox resiliente (3.2), y el Despliegue Cloud en producción en Render y Cloudflare Pages (3.3).",
            "Respecto al Tiempo: El indicador se recuperó totalmente y pasa a Verde con un 96% de cumplimiento. La aceleración técnica durante el Sprint 2 y el cierre de las tareas críticas de desarrollo permitieron recuperar la desviación del cronograma de la semana anterior (SV = S/. 0.00, SPI = 1.00).",
            "Respecto al Costo: El indicador se mantiene en Verde con 100% de cumplimiento. El costo real acumulado se ajusta exactamente al presupuesto planificado de mano de obra (S/. 78,000.00 acumulados), manteniendo un gasto de S/. 0.00 en infraestructura gracias al aprovechamiento del Free Tier."
        ],
        sustento="El Sprint 2 consolida un salto cualitativo definitivo en el proyecto Fildlab. Al cierre de la Semana 5 (25/09/2026), se ha completado en su totalidad (100%) el Núcleo Transaccional (Fase 3 de la EDT), erradicando el desfase temporal previo y situando el desempeño del cronograma en Verde (SPI = 1.00). Se entregó la plataforma web con sus 7 submódulos administrativos (Clientes, Contratos, Inventario Central, Ventas, Equipos, Liquidación de Órdenes y Adendas de Corrección), así como la PWA de campo offline-first capaz de operar en salas clínicas sin conectividad a internet mediante Dexie.js, registrando las 8 variables físico-químicas obligatorias del agua y sellando cada acta con un hash SHA-256 encadenado inmutable. Todo el ecosistema se encuentra desplegado y operativo en producción en Cloudflare Pages y Render.",
        cambios=[
            "Cierre y aceptación formal del 100% de los entregables de la Fase 3 (Núcleo Transaccional: Web Central, PWA de Campo y Despliegue Cloud).",
            "Implementación y validación del mecanismo de inmutabilidad y ledger criptográfico (tamper-evident) con hashes SHA-256 encadenados por equipo en Neon PostgreSQL.",
            "Despliegue en producción en Cloudflare Pages (fildlab-admin.pages.dev y fildlab-pwa.pages.dev) y Render (fildlab-api.onrender.com) con protocolo HTTPS/TLS 1.3 nativo.",
            "Corrección de la pila de navegación en la PWA móvil y elevación del estándar estético visual en toda la plataforma.",
            "Integración de la identidad visual oficial (logotipo corporativo, favicon e iconos PWA adaptativos) de Fildlab Perú S.A.C.",
            "Habilitación formal de los pre-requisitos de datos para el inicio de la Fase 4: Inteligencia de Negocios (Apache ECharts) e Inteligencia Artificial (Modelo predictivo RUL)."
        ],
        hitos_data=[
            ("1.1-2.5", "Fases 1 y 2 (Inicio, Planif., Arquitectura)", "8 Entregables aprobados de gestión y diseño", "11/09/2026", "11/09/2026", "Completado"),
            ("3.1", "Desarrollar plataforma web central", "Plataforma web con 7 submódulos administrativos 100% operativa", "25/09/2026", "25/09/2026", "Completado"),
            ("3.2", "Desarrollar PWA de campo", "PWA offline-first (8 parámetros, firma DPR=2, GPS y Outbox) operativa", "25/09/2026", "25/09/2026", "Completado"),
            ("3.3", "Despliegue del Sistema Cloud", "Despliegue en producción en Render y Cloudflare Pages operativo", "25/09/2026", "25/09/2026", "Completado"),
            ("4.1", "Módulo de Business Intelligence (BI)", "Tableros de rentabilidad y alertas SLA con Apache ECharts", "09/10/2026", "Programado", "En espera"),
            ("4.2", "Módulo de Inteligencia Artificial (RUL)", "Pipeline de supervivencia Cox PH y alertas predictivas", "16/10/2026", "Programado", "En espera")
        ],
        kpis_data={
            'tiempo': "El proyecto ha corregido el retraso previo y se encuentra alineado al cronograma. Schedule Variance (SV): S/. 0.00 (se recuperó la totalidad del valor rezagado). Schedule Performance Index (SPI): 1.00 (el rendimiento temporal del cronograma alcanza el 100% de lo programado para la Semana 5).",
            'costo': "El proyecto mantiene una disciplina presupuestaria perfecta. Cost Variance (CV): S/. 0.00 (cero sobrecostos en recursos). Cost Performance Index (CPI): 1.00 (eficiencia de costos óptima en mano de obra e infraestructura Free Tier de S/. 0.00)."
        },
        anexo1_data={
            'alcance_items': [
                ("1.1-1.3 Fase 1: Inicio y Planificación", "Acta, SRS v2.2, EDT y Cronograma aprobados", "100%"),
                ("2.1-2.5 Fase 2: Gestión y Arquitectura", "Planes, arquitectura técnica, matrices de riesgo y comunicaciones", "100%"),
                ("3.1 Plataforma Web Central", "Módulos de Clientes, Contratos, Inventario, Ventas, Equipos y Liquidación", "100%"),
                ("3.2 PWA de Campo (Offline-First)", "PWA con IndexedDB, 8 lecturas de agua, firma DPR=2, GPS y Outbox", "100%"),
                ("3.3 Despliegue en la Nube (Free Tier)", "Producción en Render (API) y Cloudflare Pages (Web y PWA)", "100%")
            ],
            'alcance_promedio': "100%",
            'tiempo_items': [
                ("1.1-1.3 Fase 1: Inicio y Planificación", "7 días", "7 días"),
                ("2.1-2.5 Fase 2: Gestión y Arquitectura", "14 días", "15 días"),
                ("3.1 Desarrollar plataforma web central", "5 días", "5 días"),
                ("3.2 Desarrollar PWA de campo offline", "5 días", "5 días"),
                ("3.3 Despliegue y optimización cloud", "3 días", "3 días")
            ],
            'tiempo_promedio': "96%",
            'costo_items': [
                ("Fase 1 y Fase 2: Gestión y Arquitectura", "S/. 50,000.00", "S/. 50,000.00"),
                ("3.1. Plataforma Web Central", "S/. 12,000.00", "S/. 12,000.00"),
                ("3.2. PWA de Campo Offline-First", "S/. 12,000.00", "S/. 12,000.00"),
                ("3.3. Despliegue en la Nube y Pruebas", "S/. 4,000.00", "S/. 4,000.00")
            ],
            'costo_total_plan': "S/. 78,000.00",
            'costo_total_real': "S/. 78,000.00",
            'costo_variacion': "100%"
        }
    )

if __name__ == '__main__':
    build_all()

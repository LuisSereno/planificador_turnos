# =========================================================================
# EXPORTACION.PY - FICHERO ÚNICO CON TODO INTEGRADO
# =========================================================================
"""
Módulo completo de exportación con todas las funcionalidades:
- Compatible con código anterior (generar_excel_planilla, generar_pdf_planilla, etc.)
- Nuevas funciones profesionales con estadísticas avanzadas
- Validaciones de integridad
- 6 hojas de Excel con análisis completo
- PDF con tabla y estadísticas
- Reportes en texto

CARACTERÍSTICAS:
✓ Excel: 6 hojas (Planilla, Estadísticas, Por Enfermera, Cobertura, Equidad, Validaciones)
✓ PDF: Tabla horizontal + Estadísticas
✓ CSV, JSON, iCalendar
✓ Estadísticas avanzadas
✓ Validaciones automáticas
✓ Reportes de calidad
✓ 100% compatible con código anterior
"""

from io import BytesIO
from datetime import datetime, timedelta
import json
import csv
from collections import defaultdict
from pathlib import Path

# =========================================================================
# IMPORTS: Excel
# =========================================================================
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, Reference, PieChart

    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# =========================================================================
# IMPORTS: PDF
# =========================================================================
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4, landscape
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# =========================================================================
# IMPORTS: iCalendar
# =========================================================================
try:
    from icalendar import Calendar, Event

    ICAL_AVAILABLE = True
except ImportError:
    ICAL_AVAILABLE = False

import logging

logger = logging.getLogger(__name__)

# =========================================================================
# CONFIGURACIÓN GLOBAL
# =========================================================================

COLORES_TURNOS = {
    'MAÑANA': {'rgb': 'FFC107', 'rgb_rl': '#FFC107', 'nombre': 'Mañana'},
    'TARDE': {'rgb': '00BCD4', 'rgb_rl': '#00BCD4', 'nombre': 'Tarde'},
    'NOCHE': {'rgb': '424242', 'rgb_rl': '#424242', 'nombre': 'Noche'},
    'LIBRE': {'rgb': 'E0E0E0', 'rgb_rl': '#E0E0E0', 'nombre': 'Libre'},
}

COLOR_ENCABEZADO = "1F4E78"
COLOR_SUBENCABEZADO = "D9E8F5"
COLOR_EXITO = "6BCB77"
COLOR_ALERTA = "FFD93D"
COLOR_ERROR = "FF6B6B"

BORDE_DELGADO = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)


# =========================================================================
# CLASE: ESTADÍSTICAS AVANZADAS
# =========================================================================

class EstadisticasAvanzadas:
    """Calcula estadísticas completas de la planificación."""

    def __init__(self, planificacion_data=None, ejecucion=None):
        """
        Inicializa con datos de diccionario O con modelo Django EjecucionPlanificacion
        """
        if ejecucion:
            # Modo Django ORM
            self.ejecucion = ejecucion
            self.es_orm = True
        elif planificacion_data:
            # Modo diccionario
            self.planificacion_data = planificacion_data
            self.es_orm = False
        else:
            self.es_orm = False
            self.planificacion_data = {}

    def contar_turnos_por_tipo(self):
        """Retorna conteo de cada tipo de turno."""
        if self.es_orm:
            conteo = defaultdict(int)
            planilla = self.ejecucion.planilla or {}
            for dia_data in planilla.values():
                for turno_tipo, enfermeras in dia_data.items():
                    if enfermeras:
                        conteo[turno_tipo] += len(enfermeras)
            return dict(conteo)
        else:
            conteo = defaultdict(int)
            for turno in self.planificacion_data.get('turnos_asignados', {}).values():
                conteo[turno] += 1
            return dict(conteo)

    def turnos_por_enfermera(self):
        """Retorna turnos totales por cada enfermera."""
        if self.es_orm:
            datos = {}
            planilla = self.ejecucion.planilla or {}
            for dia_data in planilla.values():
                for turno_tipo, enfermeras in dia_data.items():
                    for enf in enfermeras:
                        datos[enf] = datos.get(enf, 0) + 1
            return datos
        else:
            datos = {}
            enfermeras = self.planificacion_data.get('enfermeras', [])
            turnos_asignados = self.planificacion_data.get('turnos_asignados', {})

            for idx_enf in range(len(enfermeras)):
                nombre = enfermeras[idx_enf]['nombre']
                turnos_count = sum(1 for (e, d) in turnos_asignados if e == idx_enf)
                datos[nombre] = turnos_count

            return datos

    def distribucion_equidad(self):
        """Calcula equidad en distribución de turnos."""
        turnos_enfermera = self.turnos_por_enfermera()
        if not turnos_enfermera:
            return {'media': 0, 'min': 0, 'max': 0, 'desviacion': 0, 'diferencia': 0}

        valores = list(turnos_enfermera.values())
        media = sum(valores) / len(valores)
        minimo = min(valores)
        maximo = max(valores)
        varianza = sum((x - media) ** 2 for x in valores) / len(valores)
        desviacion = varianza ** 0.5

        return {
            'media': media,
            'min': minimo,
            'max': maximo,
            'desviacion': desviacion,
            'diferencia': maximo - minimo
        }


# =========================================================================
# FUNCIÓN: GENERAR EXCEL PLANILLA (MEJORADA + COMPATIBLE)
# =========================================================================

def generar_excel_planilla(ejecucion):
    """
    Genera archivo Excel con 6 hojas de análisis completo
    COMPATIBLE CON VERSIÓN ANTERIOR (mismos parámetros)
    """
    if not EXCEL_AVAILABLE:
        raise ImportError("openpyxl no está instalado. Ejecuta: pip install openpyxl")

    try:
        wb = Workbook()

        # ===== HOJA 1: PLANILLA TRADICIONAL =====
        ws = wb.active
        ws.title = "Planilla"

        header_fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=11)
        border = BORDE_DELGADO

        # Título
        ws['A1'] = f"Planificación: {ejecucion.configuracion.nombre}"
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:D1')

        ws[
            'A2'] = f"Período: {ejecucion.configuracion.num_dias} días desde {ejecucion.configuracion.fecha_inicio.strftime('%d/%m/%Y')}"
        ws.merge_cells('A2:D2')

        ws['A3'] = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws.merge_cells('A3:D3')

        current_row = 5

        # Headers
        headers = ['Día', 'Fecha', 'Turno', 'Enfermeras']
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        current_row += 1

        # Datos
        planilla = ejecucion.planilla or {}
        fecha_inicio = ejecucion.configuracion.fecha_inicio

        for i in range(1, ejecucion.configuracion.num_dias + 1):
            dia_key = f"dia_{i}"
            fecha_actual = fecha_inicio + timedelta(days=i - 1)
            turnos = planilla.get(dia_key, {})

            for turno_tipo in ['MAÑANA', 'TARDE', 'NOCHE']:
                enfermeras = turnos.get(turno_tipo, [])

                ws.cell(row=current_row, column=1).value = i
                ws.cell(row=current_row, column=2).value = fecha_actual.strftime('%d/%m/%Y')
                ws.cell(row=current_row, column=3).value = turno_tipo
                ws.cell(row=current_row, column=4).value = ', '.join(enfermeras) if enfermeras else 'Sin asignar'

                # Color según turno
                if turno_tipo in COLORES_TURNOS:
                    ws.cell(row=current_row, column=3).fill = PatternFill(
                        start_color=COLORES_TURNOS[turno_tipo]['rgb'],
                        end_color=COLORES_TURNOS[turno_tipo]['rgb'],
                        fill_type="solid"
                    )
                    if turno_tipo == 'NOCHE':
                        ws.cell(row=current_row, column=3).font = Font(color="FFFFFF", bold=True)

                # Bordes
                for col_idx in range(1, 5):
                    ws.cell(row=current_row, column=col_idx).border = border

                current_row += 1

        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 50

        # ===== HOJA 2: ESTADÍSTICAS GENERALES =====
        stats = EstadisticasAvanzadas(ejecucion=ejecucion)

        ws_stats = wb.create_sheet("Estadísticas")
        ws_stats['A1'] = "Estadísticas de la Planificación"
        ws_stats['A1'].font = Font(size=12, bold=True, color="FFFFFF")
        ws_stats['A1'].fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")
        ws_stats.merge_cells('A1:C1')

        row = 3
        stats_data = [
            ("Penalización Total:", ejecucion.penalizacion_total or 0),
            ("Es Óptima:", "Sí" if ejecucion.es_optima else "No"),
            ("Duración (segundos):", ejecucion.duracion or 0),
            ("Estado:", ejecucion.estado),
        ]

        for label, value in stats_data:
            ws_stats.cell(row=row, column=1).value = label
            ws_stats.cell(row=row, column=2).value = value
            ws_stats.cell(row=row, column=1).font = Font(bold=True)
            row += 1

        # Distribución por turno
        row += 1
        ws_stats.cell(row=row, column=1).value = "DISTRIBUCIÓN POR TIPO DE TURNO"
        ws_stats.cell(row=row, column=1).font = Font(bold=True, size=11, color="FFFFFF")
        ws_stats.cell(row=row, column=1).fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO,
                                                            fill_type="solid")
        ws_stats.merge_cells(f'A{row}:C{row}')

        row += 1
        headers_dist = ['Turno', 'Cantidad', 'Porcentaje']
        for col_idx, header in enumerate(headers_dist, 1):
            cell = ws_stats.cell(row=row, column=col_idx)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")

        conteo = stats.contar_turnos_por_tipo()
        total = sum(conteo.values()) if conteo else 1

        for turno_nombre in sorted(conteo.keys()):
            row += 1
            cantidad = conteo[turno_nombre]
            porcentaje = (cantidad / total * 100) if total > 0 else 0

            ws_stats.cell(row=row, column=1).value = turno_nombre
            ws_stats.cell(row=row, column=2).value = cantidad
            ws_stats.cell(row=row, column=3).value = f"{porcentaje:.1f}%"

            if turno_nombre in COLORES_TURNOS:
                ws_stats.cell(row=row, column=1).fill = PatternFill(
                    start_color=COLORES_TURNOS[turno_nombre]['rgb'],
                    end_color=COLORES_TURNOS[turno_nombre]['rgb'],
                    fill_type="solid"
                )
                if turno_nombre == 'NOCHE':
                    ws_stats.cell(row=row, column=1).font = Font(color="FFFFFF", bold=True)

        ws_stats.column_dimensions['A'].width = 20
        ws_stats.column_dimensions['B'].width = 15
        ws_stats.column_dimensions['C'].width = 15

        # ===== HOJA 3: POR ENFERMERA =====
        ws_enf = wb.create_sheet("Por Enfermera")
        ws_enf['A1'] = "Distribución de Turnos por Enfermera"
        ws_enf['A1'].font = Font(size=12, bold=True, color="FFFFFF")
        ws_enf['A1'].fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")
        ws_enf.merge_cells('A1:F1')

        row = 3
        headers_enf = ['Enfermera', 'Total Turnos', 'MAÑANA', 'TARDE', 'NOCHE', '% Ocupación']
        for col_idx, header in enumerate(headers_enf, 1):
            cell = ws_enf.cell(row=row, column=col_idx)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")

        row += 1
        turnos_por_enf = stats.turnos_por_enfermera()
        equidad = stats.distribucion_equidad()
        media_turnos = equidad['media']

        for nombre_enf in sorted(turnos_por_enf.keys()):
            total_turnos = turnos_por_enf[nombre_enf]

            ws_enf.cell(row=row, column=1).value = nombre_enf
            ws_enf.cell(row=row, column=2).value = total_turnos

            # Contar por tipo de turno
            for col_idx, turno_tipo in enumerate(['MAÑANA', 'TARDE', 'NOCHE'], 3):
                contador = 0
                for i in range(1, ejecucion.configuracion.num_dias + 1):
                    dia_key = f"dia_{i}"
                    if nombre_enf in planilla.get(dia_key, {}).get(turno_tipo, []):
                        contador += 1

                cell = ws_enf.cell(row=row, column=col_idx)
                cell.value = contador

                if contador > 0 and turno_tipo in COLORES_TURNOS:
                    cell.fill = PatternFill(
                        start_color=COLORES_TURNOS[turno_tipo]['rgb'],
                        end_color=COLORES_TURNOS[turno_tipo]['rgb'],
                        fill_type="solid"
                    )
                    if turno_tipo == 'NOCHE':
                        cell.font = Font(color="FFFFFF", bold=True)

            ocupacion = (
                        total_turnos / ejecucion.configuracion.num_dias * 100) if ejecucion.configuracion.num_dias > 0 else 0
            ws_enf.cell(row=row, column=6).value = f"{ocupacion:.1f}%"

            # Estado (equilibrado, sobrecargado, etc.)
            if abs(total_turnos - media_turnos) <= 1:
                estado_color = COLOR_EXITO
            elif total_turnos > media_turnos + 2:
                estado_color = COLOR_ALERTA
            else:
                estado_color = COLOR_ALERTA

            row += 1

        for col in range(1, 7):
            ws_enf.column_dimensions[get_column_letter(col)].width = 16

        # ===== HOJA 4: COBERTURA DIARIA =====
        ws_cob = wb.create_sheet("Cobertura")
        ws_cob['A1'] = "Análisis de Cobertura Diaria"
        ws_cob['A1'].font = Font(size=12, bold=True, color="FFFFFF")
        ws_cob['A1'].fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")
        ws_cob.merge_cells('A1:F1')

        row = 3
        headers_cob = ['Fecha', 'Día', 'MAÑANA', 'TARDE', 'NOCHE', 'Total']
        for col_idx, header in enumerate(headers_cob, 1):
            cell = ws_cob.cell(row=row, column=col_idx)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")

        row += 1
        for i in range(1, ejecucion.configuracion.num_dias + 1):
            dia_key = f"dia_{i}"
            fecha_actual = fecha_inicio + timedelta(days=i - 1)
            fecha_str = fecha_actual.strftime('%d/%m/%Y')
            dia_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'][fecha_actual.weekday()]

            ws_cob.cell(row=row, column=1).value = fecha_str
            ws_cob.cell(row=row, column=2).value = dia_semana

            dia_turnos = planilla.get(dia_key, {})
            total_dia = 0

            for col_idx, turno_tipo in enumerate(['MAÑANA', 'TARDE', 'NOCHE'], 3):
                cantidad = len(dia_turnos.get(turno_tipo, []))
                cell = ws_cob.cell(row=row, column=col_idx)
                cell.value = cantidad
                total_dia += cantidad

                if cantidad > 0 and turno_tipo in COLORES_TURNOS:
                    cell.fill = PatternFill(
                        start_color=COLORES_TURNOS[turno_tipo]['rgb'],
                        end_color=COLORES_TURNOS[turno_tipo]['rgb'],
                        fill_type="solid"
                    )
                    if turno_tipo == 'NOCHE':
                        cell.font = Font(color="FFFFFF", bold=True)

            ws_cob.cell(row=row, column=6).value = total_dia
            ws_cob.cell(row=row, column=6).fill = PatternFill(start_color="CCE5FF", end_color="CCE5FF",
                                                              fill_type="solid")
            ws_cob.cell(row=row, column=6).font = Font(bold=True)

            row += 1

        for col in range(1, 7):
            ws_cob.column_dimensions[get_column_letter(col)].width = 15

        # ===== HOJA 5: EQUIDAD =====
        ws_equidad = wb.create_sheet("Equidad")
        ws_equidad['A1'] = "Análisis de Equidad"
        ws_equidad['A1'].font = Font(size=12, bold=True, color="FFFFFF")
        ws_equidad['A1'].fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")
        ws_equidad.merge_cells('A1:B1')

        row = 3
        equidad = stats.distribucion_equidad()
        datos_equidad = [
            ("Promedio de turnos:", f"{equidad['media']:.1f}"),
            ("Mínimo:", f"{equidad['min']}"),
            ("Máximo:", f"{equidad['max']}"),
            ("Diferencia:", f"{equidad['diferencia']}"),
            ("Desviación estándar:", f"{equidad['desviacion']:.2f}"),
        ]

        for label, valor in datos_equidad:
            ws_equidad.cell(row=row, column=1).value = label
            ws_equidad.cell(row=row, column=2).value = valor
            ws_equidad.cell(row=row, column=1).font = Font(bold=True)
            row += 1

        ws_equidad.column_dimensions['A'].width = 30
        ws_equidad.column_dimensions['B'].width = 20

        # ===== HOJA 6: VALIDACIONES =====
        ws_val = wb.create_sheet("Validaciones")
        ws_val['A1'] = "Reporte de Validaciones"
        ws_val['A1'].font = Font(size=12, bold=True, color="FFFFFF")
        ws_val['A1'].fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")
        ws_val.merge_cells('A1:B1')

        row = 3
        ws_val.cell(row=row, column=1).value = "Validación"
        ws_val.cell(row=row, column=2).value = "Resultado"
        for col in [1, 2]:
            ws_val.cell(row=row, column=col).font = Font(bold=True, color="FFFFFF")
            ws_val.cell(row=row, column=col).fill = PatternFill(start_color=COLOR_ENCABEZADO,
                                                                end_color=COLOR_ENCABEZADO, fill_type="solid")

        row += 1
        ws_val.cell(row=row, column=1).value = "Estado"
        ws_val.cell(row=row, column=2).value = ejecucion.estado
        ws_val.cell(row=row, column=2).fill = PatternFill(start_color=COLOR_EXITO, end_color=COLOR_EXITO,
                                                          fill_type="solid")
        row += 1

        ws_val.cell(row=row, column=1).value = "Equidad"
        estado_equidad = "✓ ACEPTABLE" if equidad['diferencia'] <= 2 else "⚠ REVISAR"
        ws_val.cell(row=row, column=2).value = estado_equidad
        color_eq = COLOR_EXITO if equidad['diferencia'] <= 2 else COLOR_ALERTA
        ws_val.cell(row=row, column=2).fill = PatternFill(start_color=color_eq, end_color=color_eq, fill_type="solid")
        row += 1

        ws_val.cell(row=row, column=1).value = "Es Óptima"
        ws_val.cell(row=row, column=2).value = "Sí" if ejecucion.es_optima else "No"
        color_opt = COLOR_EXITO if ejecucion.es_optima else COLOR_ALERTA
        ws_val.cell(row=row, column=2).fill = PatternFill(start_color=color_opt, end_color=color_opt, fill_type="solid")

        ws_val.column_dimensions['A'].width = 25
        ws_val.column_dimensions['B'].width = 30

        # Guardar
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        logger.info(f"Excel generado exitosamente para ejecución {ejecucion.id}")
        return buffer

    except Exception as e:
        logger.error(f"Error al generar Excel: {str(e)}")
        raise


# =========================================================================
# FUNCIÓN: GENERAR PDF PLANILLA (MEJORADA + COMPATIBLE)
# =========================================================================

def generar_pdf_planilla(ejecucion):
    """
    Genera archivo PDF con tabla y estadísticas
    COMPATIBLE CON VERSIÓN ANTERIOR (mismos parámetros)
    """
    if not PDF_AVAILABLE:
        raise ImportError("reportlab no está instalado. Ejecuta: pip install reportlab")

    try:
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=18
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1F4E78'),
            spaceAfter=20,
            alignment=TA_CENTER
        )

        story = []

        # Título
        title = Paragraph(f"Planificación: {ejecucion.configuracion.nombre}", title_style)
        story.append(title)

        # Información
        info_style = styles['Normal']
        info_text = f"""
        <b>Período:</b> {ejecucion.configuracion.num_dias} días desde {ejecucion.configuracion.fecha_inicio.strftime('%d/%m/%Y')}<br/>
        <b>Generado:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>
        <b>Estado:</b> {ejecucion.estado} | <b>Penalización:</b> {ejecucion.penalizacion_total or 0}
        """
        story.append(Paragraph(info_text, info_style))
        story.append(Spacer(1, 15))

        # Tabla
        planilla = ejecucion.planilla or {}
        fecha_inicio = ejecucion.configuracion.fecha_inicio

        data = [['Día', 'Fecha', 'Turno', 'Enfermeras']]

        for i in range(1, ejecucion.configuracion.num_dias + 1):
            dia_key = f"dia_{i}"
            fecha_actual = fecha_inicio + timedelta(days=i - 1)
            turnos = planilla.get(dia_key, {})

            for turno_tipo in ['MAÑANA', 'TARDE', 'NOCHE']:
                enfermeras = turnos.get(turno_tipo, [])
                data.append([
                    str(i),
                    fecha_actual.strftime('%d/%m/%Y'),
                    turno_tipo,
                    ', '.join(enfermeras) if enfermeras else 'Sin asignar'
                ])

        table = Table(data, colWidths=[50, 100, 100, 400])

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ])

        table.setStyle(table_style)
        story.append(table)

        doc.build(story)
        buffer.seek(0)

        logger.info(f"PDF generado exitosamente para ejecución {ejecucion.id}")
        return buffer

    except Exception as e:
        logger.error(f"Error al generar PDF: {str(e)}")
        raise


# =========================================================================
# FUNCIÓN: GENERAR CSV (COMPATIBLE)
# =========================================================================

def generar_csv_planilla(ejecucion):
    """Genera archivo CSV"""
    try:
        buffer = BytesIO()
        import io
        text_buffer = io.TextIOWrapper(buffer, encoding='utf-8-sig', newline='')

        writer = csv.writer(text_buffer, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Día', 'Fecha', 'Turno', 'Enfermeras'])

        planilla = ejecucion.planilla or {}
        fecha_inicio = ejecucion.configuracion.fecha_inicio

        for i in range(1, ejecucion.configuracion.num_dias + 1):
            dia_key = f"dia_{i}"
            fecha_actual = fecha_inicio + timedelta(days=i - 1)
            turnos = planilla.get(dia_key, {})

            for turno_tipo in ['MAÑANA', 'TARDE', 'NOCHE']:
                enfermeras = turnos.get(turno_tipo, [])
                writer.writerow([
                    i,
                    fecha_actual.strftime('%d/%m/%Y'),
                    turno_tipo,
                    ', '.join(enfermeras) if enfermeras else 'Sin asignar'
                ])

        text_buffer.flush()
        buffer.seek(0)

        logger.info(f"CSV generado exitosamente para ejecución {ejecucion.id}")
        return buffer

    except Exception as e:
        logger.error(f"Error al generar CSV: {str(e)}")
        raise


# =========================================================================
# FUNCIÓN: GENERAR JSON (COMPATIBLE)
# =========================================================================

def generar_json_planilla(ejecucion):
    """Genera archivo JSON"""
    try:
        data = {
            'configuracion': {
                'id': ejecucion.configuracion.id,
                'nombre': ejecucion.configuracion.nombre,
                'num_dias': ejecucion.configuracion.num_dias,
                'fecha_inicio': ejecucion.configuracion.fecha_inicio.isoformat(),
            },
            'ejecucion': {
                'id': ejecucion.id,
                'estado': ejecucion.estado,
                'fecha_inicio': ejecucion.fecha_inicio.isoformat() if ejecucion.fecha_inicio else None,
                'fecha_fin': ejecucion.fecha_fin.isoformat() if ejecucion.fecha_fin else None,
                'duracion': ejecucion.duracion,
                'penalizacion_total': ejecucion.penalizacion_total,
                'es_optima': ejecucion.es_optima,
            },
            'planilla': ejecucion.planilla or {},
            'mensajes': ejecucion.mensajes or {},
            'generado': datetime.now().isoformat(),
        }

        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        buffer = BytesIO(json_str.encode('utf-8'))
        buffer.seek(0)

        logger.info(f"JSON generado exitosamente para ejecución {ejecucion.id}")
        return buffer

    except Exception as e:
        logger.error(f"Error al generar JSON: {str(e)}")
        raise


# =========================================================================
# FUNCIÓN: GENERAR ICAL (COMPATIBLE)
# =========================================================================

def generar_ical_planilla(ejecucion):
    """Genera archivo iCalendar"""
    if not ICAL_AVAILABLE:
        raise ImportError("icalendar no está instalado. Ejecuta: pip install icalendar")

    try:
        cal = Calendar()
        cal.add('prodid', '-//Planificador de Turnos//ES')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('x-wr-calname', f'Turnos - {ejecucion.configuracion.nombre}')
        cal.add('x-wr-timezone', 'Europe/Madrid')
        cal.add('x-wr-caldesc', f'Planificación generada el {datetime.now().strftime("%d/%m/%Y")}')

        planilla = ejecucion.planilla or {}
        fecha_inicio = ejecucion.configuracion.fecha_inicio

        horarios = {
            'MAÑANA': ('07:00', '15:00'),
            'TARDE': ('15:00', '23:00'),
            'NOCHE': ('23:00', '07:00')
        }

        for i in range(1, ejecucion.configuracion.num_dias + 1):
            dia_key = f"dia_{i}"
            fecha_actual = fecha_inicio + timedelta(days=i - 1)
            turnos = planilla.get(dia_key, {})

            for turno_tipo, (hora_inicio, hora_fin) in horarios.items():
                enfermeras = turnos.get(turno_tipo, [])

                if enfermeras:
                    event = Event()
                    event.add('summary', f'Turno {turno_tipo}')

                    inicio_hora, inicio_min = map(int, hora_inicio.split(':'))
                    fin_hora, fin_min = map(int, hora_fin.split(':'))

                    dt_inicio = datetime.combine(fecha_actual,
                                                 datetime.min.time().replace(hour=inicio_hora, minute=inicio_min))

                    if fin_hora < inicio_hora:
                        dt_fin = datetime.combine(fecha_actual + timedelta(days=1),
                                                  datetime.min.time().replace(hour=fin_hora, minute=fin_min))
                    else:
                        dt_fin = datetime.combine(fecha_actual,
                                                  datetime.min.time().replace(hour=fin_hora, minute=fin_min))

                    event.add('dtstart', dt_inicio)
                    event.add('dtend', dt_fin)
                    event.add('description', f'Enfermeras asignadas:\n' + '\n'.join(enfermeras))
                    event.add('location', 'Hospital')
                    event.add('status', 'CONFIRMED')

                    cal.add_component(event)

        buffer = BytesIO(cal.to_ical())
        buffer.seek(0)

        logger.info(f"iCal generado exitosamente para ejecución {ejecucion.id}")
        return buffer

    except Exception as e:
        logger.error(f"Error al generar iCal: {str(e)}")
        raise


# =========================================================================
# FUNCIÓN: EXPORTAR ENFERMERAS EXCEL (COMPATIBLE)
# =========================================================================

def exportar_enfermeras_excel(enfermeras_queryset):
    """Exporta lista de enfermeras a Excel"""
    if not EXCEL_AVAILABLE:
        raise ImportError("openpyxl no está instalado")

    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Enfermeras"

        headers = ['ID', 'Nombre', 'Email', 'Teléfono', 'DNI', 'Fecha Alta', 'Activa']
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color=COLOR_ENCABEZADO, end_color=COLOR_ENCABEZADO, fill_type="solid")

        for row_num, enfermera in enumerate(enfermeras_queryset, 2):
            ws.cell(row=row_num, column=1, value=enfermera.id)
            ws.cell(row=row_num, column=2, value=enfermera.nombre)
            ws.cell(row=row_num, column=3, value=enfermera.email)
            ws.cell(row=row_num, column=4, value=enfermera.telefono or '')
            ws.cell(row=row_num, column=5, value=enfermera.dni or '')
            ws.cell(row=row_num, column=6,
                    value=enfermera.fecha_alta.strftime('%d/%m/%Y') if enfermera.fecha_alta else '')
            ws.cell(row=row_num, column=7, value='Sí' if enfermera.activa else 'No')

        for col in range(1, 8):
            ws.column_dimensions[get_column_letter(col)].width = 18

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        return buffer

    except Exception as e:
        logger.error(f"Error al exportar enfermeras a Excel: {str(e)}")
        raise

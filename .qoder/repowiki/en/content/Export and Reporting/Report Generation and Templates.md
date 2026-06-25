# Report Generation and Templates

<cite>
**Referenced Files in This Document**
- [exportacion.py](file://turnos/utils/exportacion.py)
- [exportador_profesional.py](file://turnos/utils/exportador_profesional.py)
- [planilla.html](file://turnos/templates/turnos/pdf/planilla.html)
- [views.py](file://turnos/views.py)
- [tasks.py](file://turnos/tasks.py)
- [reportes.html](file://turnos/templates/turnos/reportes.html)
- [models.py](file://turnos/models.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains the report generation system, focusing on professional PDF templates and multi-format export capabilities. It covers:
- Template structure for header, data tables, and footers
- Customization and branding options
- Integration between Django templates and export functions
- Report scheduling via asynchronous tasks and batch processing
- Examples of report types and guidance for creating custom templates

## Project Structure
The report generation system spans three layers:
- Django views orchestrate export requests and build context
- Export utilities transform execution data into Excel, PDF, CSV, JSON, and iCalendar
- Django templates render printable PDFs with consistent branding

```mermaid
graph TB
subgraph "Django Views"
V1["ExportarEjecucionPDFView<br/>render_to_string + WeasyPrint"]
V2["ExportarEjecucionExcelView<br/>reuses exportacion.py"]
V3["ExportarPlanillaPDFView<br/>delegates to execution view"]
V4["ExportarPlanillaExcelView<br/>delegates to execution view"]
V5["DescargarPDFView<br/>uses exportacion.py + exportador_profesional.py"]
end
subgraph "Export Utilities"
U1["exportacion.py<br/>Excel, CSV, JSON, iCal, PDF (via ExportadorProfesional)"]
U2["exportador_profesional.py<br/>Professional exporter (Excel + PDF)"]
end
subgraph "Templates"
T1["planilla.html<br/>landscape A4, header, matrix table, legend"]
end
V1 --> T1
V1 --> U1
V2 --> U1
V5 --> U1
U1 --> U2
```

**Diagram sources**
- [views.py:1759-1810](file://turnos/views.py#L1759-L1810)
- [views.py:2036-2052](file://turnos/views.py#L2036-L2052)
- [views.py:2327-2348](file://turnos/views.py#L2327-L2348)
- [exportacion.py:515-528](file://turnos/utils/exportacion.py#L515-L528)
- [exportador_profesional.py:256-272](file://turnos/utils/exportador_profesional.py#L256-L272)
- [planilla.html:1-283](file://turnos/templates/turnos/pdf/planilla.html#L1-L283)

**Section sources**
- [views.py:1759-1810](file://turnos/views.py#L1759-L1810)
- [views.py:2036-2052](file://turnos/views.py#L2036-L2052)
- [views.py:2327-2348](file://turnos/views.py#L2327-L2348)
- [exportacion.py:515-528](file://turnos/utils/exportacion.py#L515-L528)
- [exportador_profesional.py:256-272](file://turnos/utils/exportador_profesional.py#L256-L272)
- [planilla.html:1-283](file://turnos/templates/turnos/pdf/planilla.html#L1-L283)

## Core Components
- Professional Excel exporter: Generates a single workbook with seven sheets covering vertical/horizontal matrices, statistics, per-nurse distribution, daily coverage, equity metrics, and validation outcomes.
- Professional PDF exporter: Produces a two-page PDF with a matrix table and statistics using ReportLab.
- Django PDF template: Renders a printable, branded matrix layout with page footers and legends.
- Multi-format export utilities: Provide CSV, JSON, iCalendar, and Excel exports for a given execution.
- Asynchronous scheduling: Celery tasks execute planning and produce downloadable reports.

Key responsibilities:
- Data translation: Transform ORM-backed assignments into export-friendly structures.
- Formatting: Apply consistent colors, borders, and typography across formats.
- Validation: Include integrity checks and coverage diagnostics.

**Section sources**
- [exportacion.py:135-467](file://turnos/utils/exportacion.py#L135-L467)
- [exportacion.py:515-582](file://turnos/utils/exportacion.py#L515-L582)
- [exportador_profesional.py:256-915](file://turnos/utils/exportador_profesional.py#L256-L915)
- [planilla.html:1-283](file://turnos/templates/turnos/pdf/planilla.html#L1-L283)

## Architecture Overview
The system integrates Django views, export utilities, and templates to deliver reports.

```mermaid
sequenceDiagram
participant User as "User"
participant View as "ExportarEjecucionPDFView"
participant Template as "planilla.html"
participant Engine as "WeasyPrint"
participant Buffer as "BytesIO"
User->>View : GET /export/pdf/{execution_id}
View->>View : _build_matrix_context(execution)
View->>Template : render_to_string(context)
Template-->>View : HTML string
View->>Engine : HTML(string).write_pdf()
Engine-->>View : PDF bytes
View-->>User : HttpResponse(PDF, attachment)
```

**Diagram sources**
- [views.py:1759-1784](file://turnos/views.py#L1759-L1784)
- [planilla.html:1-283](file://turnos/templates/turnos/pdf/planilla.html#L1-L283)

## Detailed Component Analysis

### Professional PDF Template (planilla.html)
Structure and styling:
- Header section with title, configuration name, and period range
- Two-row day headers: letters and numeric days
- Matrix table: first column for nurse names, subsequent columns for days
- Footer with page number and generation timestamp
- Color-coded cells for shift types and special statuses
- Legend for shift codes and special statuses

Customization and branding:
- Colors and typography are embedded in the stylesheet
- Page size is A4 in landscape orientation
- Footer content is templated for dynamic generation date

```mermaid
flowchart TD
Start(["Render Template"]) --> Header["Render Header<br/>Title + Config Name + Period"]
Header --> DayHeaders["Render Day Headers<br/>Letters + Numbers"]
DayHeaders --> Matrix["Render Matrix Table<br/>Nurses vs Days"]
Matrix --> Footer["Render Footer<br/>Page Counter + Generated At"]
Footer --> Legend["Render Legend<br/>Shift Codes + Special Statuses"]
Legend --> End(["Final HTML"])
```

**Diagram sources**
- [planilla.html:213-283](file://turnos/templates/turnos/pdf/planilla.html#L213-L283)

**Section sources**
- [planilla.html:1-283](file://turnos/templates/turnos/pdf/planilla.html#L1-L283)

### Export Utilities: Excel, PDF, CSV, JSON, iCal
Excel exporter:
- Seven-sheet workbook: vertical matrix, horizontal matrix, statistics, per-nurse summary, coverage, equity, validations
- Uses openpyxl for styling, colors, and sheet creation
- Translates ORM assignments into dictionaries for tabular representation

PDF exporter:
- Two-page PDF: matrix table and statistics
- Uses ReportLab for tables, styles, and page breaks
- Integrates with the professional exporter for consistent visuals

CSV/JSON/iCal exporters:
- CSV: vertical matrix format with semicolon-separated values
- JSON: structured export of configuration and planilla data
- iCal: calendar events per shift with start/end times

```mermaid
classDiagram
class ExportadorProfesional {
+exportar_excel(file)
+exportar_pdf(file)
+exportar_ambos(base_name)
+generar_reporte_txt(file)
-_generar_matriz_datos()
-_generar_pagina_tabla()
-_generar_pagina_estadisticas()
}
class EstadisticasAvanzadas {
+contar_turnos_por_tipo()
+turnos_por_enfermera()
+turnos_por_enfermera_y_tipo()
+dias_libres_por_enfermera()
+cobertura_diaria_por_turno()
+distribucion_equidad()
+equipos_mas_ocupados(top)
+equipos_menos_ocupados(top)
+cobertura_minima_garantizada(turno)
+validar_integridad()
}
class ValidadorPlani {
+generar_reporte_validacion(stats)
}
ExportadorProfesional --> EstadisticasAvanzadas : "uses"
ExportadorProfesional --> ValidadorPlani : "uses"
```

**Diagram sources**
- [exportador_profesional.py:80-210](file://turnos/utils/exportador_profesional.py#L80-L210)
- [exportador_profesional.py:256-915](file://turnos/utils/exportador_profesional.py#L256-L915)

**Section sources**
- [exportacion.py:135-467](file://turnos/utils/exportacion.py#L135-L467)
- [exportacion.py:515-582](file://turnos/utils/exportacion.py#L515-L582)
- [exportador_profesional.py:256-915](file://turnos/utils/exportador_profesional.py#L256-L915)

### Django Views: Export Orchestration
- ExportarEjecucionPDFView: renders a printable PDF using the Django template and WeasyPrint
- ExportarEjecucionExcelView: generates Excel via exportacion.py
- ExportarPlanillaPDFView and ExportarPlanillaExcelView: convenience wrappers delegating to execution-level views
- DescargarPDFView: generates PDF using exportacion.py and exportador_profesional.py

Context processing:
- Builds a matrix context with nurses, days, totals, and special statuses
- Passes dynamic metadata such as generation date and period

**Section sources**
- [views.py:1759-1810](file://turnos/views.py#L1759-L1810)
- [views.py:2036-2052](file://turnos/views.py#L2036-L2052)
- [views.py:2327-2348](file://turnos/views.py#L2327-L2348)

### Report Types and Examples
- Execution-level exports: PDF, Excel, CSV, JSON, iCal
- Professional exporter: Excel with six sheets plus PDF with matrix and statistics
- Report cards: KPI dashboards for workload, conflicts, and trends

Examples:
- Horizontal matrix: nurse rows × day columns
- Vertical matrix: day × shift × nurse aggregation
- Statistics: counts, percentages, and coverage diagnostics
- Equity: deviation metrics and top/bottom loaded nurses
- Validations: integrity checks and coverage guarantees

**Section sources**
- [exportacion.py:135-467](file://turnos/utils/exportacion.py#L135-L467)
- [exportador_profesional.py:256-915](file://turnos/utils/exportador_profesional.py#L256-L915)
- [reportes.html:1-298](file://turnos/templates/turnos/reportes.html#L1-L298)

### Creating Custom Report Templates
Guidance:
- Extend the existing planilla.html pattern: header, day headers, matrix, footer, legend
- Use consistent color codes for shift types and special statuses
- Keep typography small and readable for dense matrices
- Add optional branding elements (logo, colors) within the stylesheet
- For new formats, mirror the view-to-template-to-export pattern

**Section sources**
- [planilla.html:1-283](file://turnos/templates/turnos/pdf/planilla.html#L1-L283)
- [views.py:1759-1784](file://turnos/views.py#L1759-L1784)

## Dependency Analysis
Inter-module dependencies:
- Views depend on export utilities and templates
- Export utilities depend on ORM models and third-party libraries
- Professional exporter depends on both Excel and PDF engines

```mermaid
graph LR
Views["turnos/views.py"] --> Exportacion["turnos/utils/exportacion.py"]
Views --> Prof["turnos/utils/exportador_profesional.py"]
Prof --> OpenPyXL["openpyxl"]
Prof --> ReportLab["reportlab"]
Exportacion --> OpenPyXL
Exportacion --> ReportLab
Views --> Template["turnos/templates/turnos/pdf/planilla.html"]
```

**Diagram sources**
- [views.py:1759-1810](file://turnos/views.py#L1759-L1810)
- [exportacion.py:31-48](file://turnos/utils/exportacion.py#L31-L48)
- [exportador_profesional.py:26-42](file://turnos/utils/exportador_profesional.py#L26-L42)
- [planilla.html:1-283](file://turnos/templates/turnos/pdf/planilla.html#L1-L283)

**Section sources**
- [views.py:1759-1810](file://turnos/views.py#L1759-L1810)
- [exportacion.py:31-48](file://turnos/utils/exportacion.py#L31-L48)
- [exportador_profesional.py:26-42](file://turnos/utils/exportador_profesional.py#L26-L42)

## Performance Considerations
- Excel generation: Uses openpyxl with explicit styling; large periods increase memory usage. Consider reducing sheet count or splitting exports for very long periods.
- PDF generation: ReportLab builds tables and styles; avoid excessive repetition rows. The professional exporter consolidates into two pages.
- CSV/JSON: Lightweight; suitable for large datasets.
- iCal: Creates one event per shift-day; keep periods reasonable to limit event count.
- Asynchronous processing: Celery tasks offload heavy computation; ensure queue capacity matches workload.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Missing dependencies: Ensure openpyxl, reportlab, and icalendar are installed for full export support.
- Empty or missing planilla: Verify the execution has a generated planilla and assigned assignments.
- Large downloads: For very long periods, prefer CSV or split exports into smaller chunks.
- Styling inconsistencies: Confirm color hex codes and font sizes match template expectations.

**Section sources**
- [exportacion.py:22-48](file://turnos/utils/exportacion.py#L22-L48)
- [exportador_profesional.py:26-42](file://turnos/utils/exportador_profesional.py#L26-L42)

## Conclusion
The report generation system combines robust export utilities with reusable Django templates to produce professional, branded reports. It supports multiple formats, integrates seamlessly with the planning pipeline, and offers customization hooks for diverse organizational needs. Asynchronous task execution enables scalable batch processing and scheduled deliveries.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Report Scheduling and Automated Delivery
- Asynchronous execution: Celery tasks run planning and expose downloadable artifacts.
- Batch processing: Tasks for cleaning old executions and generating monthly statistics.
- Email notifications: Completion and error notifications include export options.

**Section sources**
- [tasks.py:17-240](file://turnos/tasks.py#L17-L240)
- [tasks.py:242-314](file://turnos/tasks.py#L242-L314)
- [tasks.py:333-696](file://turnos/tasks.py#L333-L696)

### Data Models Involved in Reports
- Execution and Planilla: container for planning results and assignments
- Enfermera and TipoTurno: source of identities and shift definitions
- AsignacionTurno: assignment records linking nurses, shifts, and dates

**Section sources**
- [models.py:1-200](file://turnos/models.py#L1-L200)
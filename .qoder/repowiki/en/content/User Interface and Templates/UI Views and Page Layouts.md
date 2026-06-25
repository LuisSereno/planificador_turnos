# UI Views and Page Layouts

<cite>
**Referenced Files in This Document**
- [base.html](file://turnos/templates/base.html)
- [dashboard.html](file://turnos/templates/turnos/dashboard.html)
- [wizard/base.html](file://turnos/templates/turnos/wizard/base.html)
- [ejecutar_planificacion.html](file://turnos/templates/turnos/ejecutar_planificacion.html)
- [enfermera_list.html](file://turnos/templates/turnos/enfermera_list.html)
- [reportes.html](file://turnos/templates/turnos/reportes.html)
- [estadisticas.html](file://turnos/templates/turnos/partials/estadisticas.html)
- [planilla_tabla.html](file://turnos/templates/turnos/partials/planilla_tabla.html)
- [resultado_calendario.html](file://turnos/templates/turnos/resultado_calendario.html)
- [tipo_turno_list.html](file://turnos/templates/turnos/tipo_turno_list.html)
- [workspace_selector.html](file://turnos/templates/includes/workspace_selector.html)
- [dashboard.css](file://static/css/dashboard.css)
- [wizard.css](file://static/css/wizard.css)
- [calendario.css](file://static/css/calendario.css)
- [dashboard.js](file://static/js/dashboard.js)
- [main.js](file://static/js/main.js)
- [calendario.js](file://static/js/calendario.js)
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

## Introduction
This document describes the user interface views and page layouts across the application. It covers the dashboard with statistics widgets, the step-by-step planning wizard, staff management interfaces, and reporting pages. It also explains layout patterns, navigation structures, user workflows, form and table layouts, calendar views, modal dialogs, responsive behavior, accessibility features, and the integration between server-side rendering and client-side interactivity.

## Project Structure
The UI is built with Django templates extending a shared base layout. Styles are organized per view (dashboard, wizard, calendar) and global utilities live in a main stylesheet and JavaScript module. Client-side scripts handle interactive features such as animated counters, calendar rendering, and workspace switching.

```mermaid
graph TB
subgraph "Base Template"
base["base.html"]
end
subgraph "Views"
dash["dashboard.html"]
wizard["wizard/base.html"]
exec["ejecutar_planificacion.html"]
nurses["enfermera_list.html"]
reports["reportes.html"]
cal["resultado_calendario.html"]
types["tipo_turno_list.html"]
end
subgraph "Partials"
stats["partials/estadisticas.html"]
timetable["partials/planilla_tabla.html"]
end
subgraph "Assets"
css_dash["dashboard.css"]
css_wiz["wizard.css"]
css_cal["calendario.css"]
js_main["main.js"]
js_dash["dashboard.js"]
js_cal["calendario.js"]
end
base --> dash
base --> wizard
base --> exec
base --> nurses
base --> reports
base --> cal
base --> types
dash --> stats
dash --> timetable
base --> css_dash
base --> css_wiz
base --> css_cal
base --> js_main
dash --> js_dash
cal --> js_cal
```

**Diagram sources**
- [base.html](file://turnos/templates/base.html)
- [dashboard.html](file://turnos/templates/turnos/dashboard.html)
- [wizard/base.html](file://turnos/templates/turnos/wizard/base.html)
- [ejecutar_planificacion.html](file://turnos/templates/turnos/ejecutar_planificacion.html)
- [enfermera_list.html](file://turnos/templates/turnos/enfermera_list.html)
- [reportes.html](file://turnos/templates/turnos/reportes.html)
- [resultado_calendario.html](file://turnos/templates/turnos/resultado_calendario.html)
- [tipo_turno_list.html](file://turnos/templates/turnos/tipo_turno_list.html)
- [estadisticas.html](file://turnos/templates/turnos/partials/estadisticas.html)
- [planilla_tabla.html](file://turnos/templates/turnos/partials/planilla_tabla.html)
- [dashboard.css](file://static/css/dashboard.css)
- [wizard.css](file://static/css/wizard.css)
- [calendario.css](file://static/css/calendario.css)
- [dashboard.js](file://static/js/dashboard.js)
- [main.js](file://static/js/main.js)
- [calendario.js](file://static/js/calendario.js)

**Section sources**
- [base.html](file://turnos/templates/base.html)
- [dashboard.html](file://turnos/templates/turnos/dashboard.html)
- [wizard/base.html](file://turnos/templates/turnos/wizard/base.html)
- [ejecutar_planificacion.html](file://turnos/templates/turnos/ejecutar_planificacion.html)
- [enfermera_list.html](file://turnos/templates/turnos/enfermera_list.html)
- [reportes.html](file://turnos/templates/turnos/reportes.html)
- [resultado_calendario.html](file://turnos/templates/turnos/resultado_calendario.html)
- [tipo_turno_list.html](file://turnos/templates/turnos/tipo_turno_list.html)
- [estadisticas.html](file://turnos/templates/turnos/partials/estadisticas.html)
- [planilla_tabla.html](file://turnos/templates/turnos/partials/planilla_tabla.html)
- [dashboard.css](file://static/css/dashboard.css)
- [wizard.css](file://static/css/wizard.css)
- [calendario.css](file://static/css/calendario.css)
- [dashboard.js](file://static/js/dashboard.js)
- [main.js](file://static/js/main.js)
- [calendario.js](file://static/js/calendario.js)

## Core Components
- Base layout with navigation, breadcrumbs, and global messages
- Dashboard with statistics cards, recent executions, and quick actions
- Planning wizard with step indicators, help panel, and dynamic restriction editing
- Staff management list with filtering, pagination, and card-based entries
- Reporting hub with KPI cards, report cards, and system status
- Calendar view with FullCalendar integration, filters, and modal details
- Turn types management with predefined creation and status badges
- Partial components for execution statistics and printable timetable

Key interactive features:
- Animated counters on dashboard
- Bootstrap-based modals and alerts
- Sticky table headers and scrollable areas
- Workspace selector with AJAX post

**Section sources**
- [base.html](file://turnos/templates/base.html)
- [dashboard.html](file://turnos/templates/turnos/dashboard.html)
- [wizard/base.html](file://turnos/templates/turnos/wizard/base.html)
- [enfermera_list.html](file://turnos/templates/turnos/enfermera_list.html)
- [reportes.html](file://turnos/templates/turnos/reportes.html)
- [resultado_calendario.html](file://turnos/templates/turnos/resultado_calendario.html)
- [tipo_turno_list.html](file://turnos/templates/turnos/tipo_turno_list.html)
- [estadisticas.html](file://turnos/templates/turnos/partials/estadisticas.html)
- [planilla_tabla.html](file://turnos/templates/turnos/partials/planilla_tabla.html)
- [workspace_selector.html](file://turnos/templates/includes/workspace_selector.html)
- [dashboard.css](file://static/css/dashboard.css)
- [wizard.css](file://static/css/wizard.css)
- [calendario.css](file://static/css/calendario.css)
- [dashboard.js](file://static/js/dashboard.js)
- [main.js](file://static/js/main.js)
- [calendario.js](file://static/js/calendario.js)

## Architecture Overview
The UI follows a layered pattern:
- Server-side rendering generates HTML with Django templates
- Shared base layout injects global CSS and JS
- View-specific CSS and JS enhance interactivity
- Bootstrap 5 provides responsive components and modals
- FullCalendar powers the calendar view

```mermaid
graph TB
user["User"]
nav["Navbar<br/>Breadcrumbs"]
dash["Dashboard"]
wizard["Wizard Steps"]
staff["Staff List"]
reports["Reports Hub"]
calendar["Calendar View"]
partials["Partials"]
user --> nav
nav --> dash
nav --> wizard
nav --> staff
nav --> reports
nav --> calendar
dash --> partials
reports --> partials
```

**Diagram sources**
- [base.html](file://turnos/templates/base.html)
- [dashboard.html](file://turnos/templates/turnos/dashboard.html)
- [wizard/base.html](file://turnos/templates/turnos/wizard/base.html)
- [enfermera_list.html](file://turnos/templates/turnos/enfermera_list.html)
- [reportes.html](file://turnos/templates/turnos/reportes.html)
- [resultado_calendario.html](file://turnos/templates/turnos/resultado_calendario.html)
- [estadisticas.html](file://turnos/templates/turnos/partials/estadisticas.html)

## Detailed Component Analysis

### Dashboard Interface
The dashboard presents a summary of system activity with:
- Statistics cards for configurations, successful runs, active nurses, and planned days
- Recent executions table with status badges and duration
- Quick actions buttons for common tasks
- Responsive grid layout with animations and hover effects

```mermaid
flowchart TD
Start(["Page Load"]) --> Stats["Render Stat Cards"]
Stats --> Anim["Animate Counters"]
Stats --> Exec["Load Recent Executions"]
Exec --> Quick["Show Quick Actions"]
Quick --> End(["Ready"])
```

**Diagram sources**
- [dashboard.html](file://turnos/templates/turnos/dashboard.html)
- [dashboard.css](file://static/css/dashboard.css)
- [dashboard.js](file://static/js/dashboard.js)

**Section sources**
- [dashboard.html](file://turnos/templates/turnos/dashboard.html)
- [dashboard.css](file://static/css/dashboard.css)
- [dashboard.js](file://static/js/dashboard.js)

### Planning Wizard
The wizard guides users through four steps:
- Step indicators with active/completed states and help content
- Dynamic restriction editing (hard and soft constraints)
- Navigation controls and progress bar
- Sticky sidebar for improved usability on long forms

```mermaid
sequenceDiagram
participant U as "User"
participant W as "Wizard Base"
participant P1 as "Step 1"
participant P2 as "Step 2"
participant P3 as "Step 3"
participant P4 as "Step 4"
U->>W : Open Wizard
W->>P1 : Render Step 1
U->>P1 : Fill Basic Info
P1-->>W : Next
W->>P2 : Render Step 2
U->>P2 : Set Demand
P2-->>W : Next
W->>P3 : Render Step 3
U->>P3 : Add Hard Constraints
P3-->>W : Next
W->>P4 : Render Step 4
U->>P4 : Add Soft Constraints
P4-->>W : Submit
```

**Diagram sources**
- [wizard/base.html](file://turnos/templates/turnos/wizard/base.html)
- [wizard.css](file://static/css/wizard.css)

**Section sources**
- [wizard/base.html](file://turnos/templates/turnos/wizard/base.html)
- [wizard.css](file://static/css/wizard.css)

### Staff Management Interfaces
The staff list uses a card grid with:
- Search and filter controls (status, order)
- Pagination with page links
- Hover and selection effects
- Inline actions per staff member

```mermaid
flowchart TD
View["Staff List View"] --> Filters["Apply Filters"]
Filters --> Results["Render Card Grid"]
Results --> Actions["Inline Actions"]
Actions --> Edit["Edit/Delete"]
Actions --> View["View Details"]
```

**Diagram sources**
- [enfermera_list.html](file://turnos/templates/turnos/enfermera_list.html)
- [main.js](file://static/js/main.js)

**Section sources**
- [enfermera_list.html](file://turnos/templates/turnos/enfermera_list.html)
- [main.js](file://static/js/main.js)

### Reporting Pages
The reporting hub provides:
- KPI summary cards
- Report cards for workload, conflicts, and trends
- System status and last update timestamps
- Quick navigation to related lists

```mermaid
flowchart TD
Reports["Reports Hub"] --> KPIS["KPI Cards"]
Reports --> Cards["Report Cards"]
Reports --> Status["System Status"]
Reports --> Nav["Quick Links"]
```

**Diagram sources**
- [reportes.html](file://turnos/templates/turnos/reportes.html)
- [reportes.html](file://turnos/templates/turnos/reportes.html)

**Section sources**
- [reportes.html](file://turnos/templates/turnos/reportes.html)

### Execution Result Views
Execution details include:
- Statistics cards for runtime, days, nurses, and assignments
- Quality metrics (optimal/facible solution, total penalty)
- Distribution of shifts by type
- Workload distribution per nurse with progress bars

```mermaid
flowchart TD
Exec["Execution Detail"] --> Stats["Stats Cards"]
Exec --> Metrics["Quality Metrics"]
Exec --> Dist["Shift Distribution"]
Exec --> Load["Workload per Nurse"]
```

**Diagram sources**
- [estadisticas.html](file://turnos/templates/turnos/partials/estadisticas.html)

**Section sources**
- [estadisticas.html](file://turnos/templates/turnos/partials/estadisticas.html)

### Timetable Display
The printable timetable uses:
- Sticky headers and first column for nurse names
- Scrollable viewport with responsive adjustments
- Color-coded shift badges and time labels

```mermaid
flowchart TD
Timetable["Timetable Tab"] --> Sticky["Sticky Headers"]
Timetable --> Scroll["Scrollable Container"]
Timetable --> Badges["Color-coded Shift Badges"]
```

**Diagram sources**
- [planilla_tabla.html](file://turnos/templates/turnos/partials/planilla_tabla.html)
- [planilla_tabla.html](file://turnos/templates/turnos/partials/planilla_tabla.html)

**Section sources**
- [planilla_tabla.html](file://turnos/templates/turnos/partials/planilla_tabla.html)

### Calendar View
The calendar integrates FullCalendar:
- Month/week/day view toggles
- Filter by nurse and shift type
- Legend for shift types
- Modal dialog for event details

```mermaid
sequenceDiagram
participant U as "User"
participant C as "Calendar View"
participant FC as "FullCalendar"
participant M as "Modal"
U->>C : Select View (month/week/day)
C->>FC : Change View
U->>C : Apply Filters
C->>FC : Reload Events
U->>FC : Click Event
FC->>M : Show Event Details
U->>M : Close
```

**Diagram sources**
- [resultado_calendario.html](file://turnos/templates/turnos/resultado_calendario.html)
- [calendario.css](file://static/css/calendario.css)
- [calendario.js](file://static/js/calendario.js)

**Section sources**
- [resultado_calendario.html](file://turnos/templates/turnos/resultado_calendario.html)
- [calendario.css](file://static/css/calendario.css)
- [calendario.js](file://static/js/calendario.js)

### Turn Types Management
Turn types are presented as:
- Card-based list with color-coded headers
- Status badges and usage counts
- Quick-create presets for common shifts
- Edit/delete actions with safety checks

```mermaid
flowchart TD
Types["Turn Types List"] --> Cards["Card Grid"]
Cards --> Presets["Quick Create Presets"]
Cards --> Actions["Edit/Delete"]
```

**Diagram sources**
- [tipo_turno_list.html](file://turnos/templates/turnos/tipo_turno_list.html)

**Section sources**
- [tipo_turno_list.html](file://turnos/templates/turnos/tipo_turno_list.html)

### Workspace Selector
The workspace selector enables switching workspaces via AJAX:
- Dropdown with current selection
- POST request with CSRF token
- Automatic reload on success

```mermaid
sequenceDiagram
participant U as "User"
participant WS as "Workspace Selector"
participant S as "Server"
U->>WS : Change Workspace
WS->>S : POST workspace_id (+ CSRF)
S-->>WS : JSON {success : true}
WS->>U : Reload Page
```

**Diagram sources**
- [workspace_selector.html](file://turnos/templates/includes/workspace_selector.html)

**Section sources**
- [workspace_selector.html](file://turnos/templates/includes/workspace_selector.html)

## Dependency Analysis
The UI relies on:
- Bootstrap 5 for responsive components and modals
- Font Awesome for icons
- FullCalendar for calendar interactions
- Localized date/time formatting
- Sticky positioning for headers and sidebars
- CSS custom properties for theme colors

```mermaid
graph LR
base["base.html"] --> bootstrap["Bootstrap 5"]
base --> icons["Font Awesome"]
dash["dashboard.html"] --> dashCSS["dashboard.css"]
wizard["wizard/base.html"] --> wizCSS["wizard.css"]
cal["resultado_calendario.html"] --> calCSS["calendario.css"]
cal --> fc["FullCalendar"]
mainJS["main.js"] --> bs["Bootstrap JS"]
dashJS["dashboard.js"] --> dashCSS
calJS["calendario.js"] --> fc
```

**Diagram sources**
- [base.html](file://turnos/templates/base.html)
- [dashboard.html](file://turnos/templates/turnos/dashboard.html)
- [wizard/base.html](file://turnos/templates/turnos/wizard/base.html)
- [resultado_calendario.html](file://turnos/templates/turnos/resultado_calendario.html)
- [dashboard.css](file://static/css/dashboard.css)
- [wizard.css](file://static/css/wizard.css)
- [calendario.css](file://static/css/calendario.css)
- [main.js](file://static/js/main.js)
- [dashboard.js](file://static/js/dashboard.js)
- [calendario.js](file://static/js/calendario.js)

**Section sources**
- [base.html](file://turnos/templates/base.html)
- [dashboard.css](file://static/css/dashboard.css)
- [wizard.css](file://static/css/wizard.css)
- [calendario.css](file://static/css/calendario.css)
- [main.js](file://static/js/main.js)
- [dashboard.js](file://static/js/dashboard.js)
- [calendario.js](file://static/js/calendario.js)

## Performance Considerations
- Use sticky headers and scrollable containers judiciously to avoid layout thrashing
- Lazy-load heavy calendars and tables when possible
- Minimize DOM updates during animations and filters
- Leverage Bootstrap’s compiled bundle to reduce script overhead
- Cache frequently accessed data (e.g., workspace preferences) client-side

## Troubleshooting Guide
Common UI issues and resolutions:
- Alerts not dismissing: Verify Bootstrap Alert initialization and auto-close timing
- Wizard step navigation: Ensure step indicator click handlers are attached after DOMContentLoaded
- Calendar view not updating: Confirm FullCalendar view change triggers and event reload
- Table sorting/filtering: Check column indices and text content normalization
- Workspace switch failing: Validate CSRF token presence and POST response handling

**Section sources**
- [base.html](file://turnos/templates/base.html)
- [main.js](file://static/js/main.js)
- [dashboard.js](file://static/js/dashboard.js)
- [calendario.js](file://static/js/calendario.js)

## Conclusion
The application’s UI combines a robust base layout with specialized views for planning, staff management, reporting, and calendar visualization. The design emphasizes responsiveness, accessibility, and user-friendly workflows, integrating server-side rendering with Bootstrap components and targeted JavaScript enhancements for interactivity.
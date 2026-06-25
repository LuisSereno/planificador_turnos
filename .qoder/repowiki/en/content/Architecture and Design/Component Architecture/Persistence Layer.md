# Persistence Layer

<cite>
**Referenced Files in This Document**
- [models.py](file://turnos/models.py)
- [admin.py](file://turnos/admin.py)
- [tasks.py](file://turnos/tasks.py)
- [celery.py](file://proyecto_turnos/celery.py)
- [exportacion.py](file://turnos/utils/exportacion.py)
- [exportador_profesional.py](file://turnos/utils/exportador_profesional.py)
- [0001_initial.py](file://turnos/migrations/0001_initial.py)
- [0009_add_domain_models.py](file://turnos/migrations/0009_add_domain_models.py)
- [0014_tipoturno_sustituto_libre.py](file://turnos/migrations/0014_tipoturno_sustituto_libre.py)
- [init.sql](file://docker/postgres/init.sql)
- [views.py](file://turnos/views.py)
- [mixins.py](file://turnos/mixins.py)
- [decorators.py](file://turnos/decorators.py)
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
This document provides a comprehensive guide to the Persistence Layer of the Nursing Shift Scheduler application. It covers Django ORM integration, database schema design, model relationships, indexing strategies, and multi-workspace data isolation. It also documents the Django Admin configuration, asynchronous task processing via Celery, export processing workflows, database migration strategy, model validation rules, and data integrity constraints. Guidance on performance, caching, and scalability is included.

## Project Structure
The persistence layer spans several Django app modules:
- Models define the domain and relational schema.
- Admin provides a tailored Django Admin interface.
- Tasks orchestrate asynchronous execution of planning and exports.
- Migrations encode schema evolution.
- Utilities implement export workflows to Excel, PDF, CSV, JSON, and iCalendar.
- PostgreSQL initialization script configures extensions, search, views, indices, and policies.

```mermaid
graph TB
subgraph "Django App"
M["Models<br/>turnos/models.py"]
A["Admin<br/>turnos/admin.py"]
T["Tasks<br/>turnos/tasks.py"]
U1["Export Utils<br/>turnos/utils/exportacion.py"]
U2["Professional Exporter<br/>turnos/utils/exportador_profesional.py"]
V["Views<br/>turnos/views.py"]
X["Mixins & Decorators<br/>turnos/mixins.py, turnos/decorators.py"]
end
subgraph "Migrations"
MI["Initial Migration<br/>0001_initial.py"]
MD["Domain Models Migration<br/>0009_add_domain_models.py"]
MT["Type Field Migration<br/>0014_tipoturno_sustituto_libre.py"]
end
subgraph "Celery"
CAPP["Celery App<br/>proyecto_turnos/celery.py"]
end
subgraph "PostgreSQL"
SQL["Init Script<br/>docker/postgres/init.sql"]
end
M --> A
M --> T
M --> U1
M --> U2
M --> V
T --> CAPP
MI --> M
MD --> M
MT --> M
SQL -.-> M
```

**Diagram sources**
- [models.py:12-825](file://turnos/models.py#L12-L825)
- [admin.py:1-449](file://turnos/admin.py#L1-L449)
- [tasks.py:1-716](file://turnos/tasks.py#L1-L716)
- [celery.py:1-14](file://proyecto_turnos/celery.py#L1-L14)
- [exportacion.py:1-665](file://turnos/utils/exportacion.py#L1-L665)
- [exportador_profesional.py:1-990](file://turnos/utils/exportador_profesional.py#L1-L990)
- [0001_initial.py:1-140](file://turnos/migrations/0001_initial.py#L1-L140)
- [0009_add_domain_models.py:1-123](file://turnos/migrations/0009_add_domain_models.py#L1-L123)
- [0014_tipoturno_sustituto_libre.py:1-19](file://turnos/migrations/0014_tipoturno_sustituto_libre.py#L1-L19)
- [init.sql:1-508](file://docker/postgres/init.sql#L1-L508)

**Section sources**
- [models.py:12-825](file://turnos/models.py#L12-L825)
- [admin.py:1-449](file://turnos/admin.py#L1-L449)
- [tasks.py:1-716](file://turnos/tasks.py#L1-L716)
- [celery.py:1-14](file://proyecto_turnos/celery.py#L1-L14)
- [exportacion.py:1-665](file://turnos/utils/exportacion.py#L1-L665)
- [exportador_profesional.py:1-990](file://turnos/utils/exportador_profesional.py#L1-L990)
- [0001_initial.py:1-140](file://turnos/migrations/0001_initial.py#L1-L140)
- [0009_add_domain_models.py:1-123](file://turnos/migrations/0009_add_domain_models.py#L1-L123)
- [0014_tipoturno_sustituto_libre.py:1-19](file://turnos/migrations/0014_tipoturno_sustituto_libre.py#L1-L19)
- [init.sql:1-508](file://docker/postgres/init.sql#L1-L508)

## Core Components
- Workspace: Tenant container isolating data per user group.
- Domain Entities: Enfermera, TipoTurno, ConfiguracionPlanificacion, Ejecucion, Planilla, AsignacionTurno.
- Advanced Domain: ContratoEnfermera, RotacionBase, CeldaRotacion, AsignacionRotacionEnfermera, Incidencia, BalanceHistoricoEnfermera.
- Admin: Tailored ModelAdmin configurations with custom lists, filters, and badges.
- Tasks: Asynchronous planning execution and export generation.
- Exports: Multi-format export pipeline (Excel, PDF, CSV, JSON, iCal) with validation and statistics.

**Section sources**
- [models.py:12-825](file://turnos/models.py#L12-L825)
- [admin.py:1-449](file://turnos/admin.py#L1-L449)
- [tasks.py:17-716](file://turnos/tasks.py#L17-L716)
- [exportacion.py:1-665](file://turnos/utils/exportacion.py#L1-L665)
- [exportador_profesional.py:1-990](file://turnos/utils/exportador_profesional.py#L1-L990)

## Architecture Overview
The persistence layer integrates Django ORM with PostgreSQL, supports multi-workspace isolation, and leverages Celery for asynchronous processing. Admin provides operational controls, while export utilities transform persisted planning results into multiple formats.

```mermaid
classDiagram
class Workspace {
+string nombre
+string descripcion
+boolean activo
+datetime fecha_creacion
+users : ManyToMany
}
class Enfermera {
+string nombre
+string email
+string telefono
+string dni
+boolean activa
+date fecha_alta
+JSON preferencias
+string notas
+workspace : ForeignKey
}
class TipoTurno {
+string nombre
+string codigo_corto
+time hora_inicio
+time hora_fin
+string descripcion
+boolean activo
+boolean es_incidencia
+boolean es_sustituto_libre
+workspace : ForeignKey
}
class ConfiguracionPlanificacion {
+string nombre
+string descripcion
+boolean activa
+int num_dias
+date fecha_inicio
+JSON demanda_por_turno
+JSON restricciones_duras
+JSON restricciones_blandas
+JSON patrones_turnos_json
+int num_trabajadores
+int tiempo_maximo_segundos
+int seed
+datetime fecha_creacion
+datetime fecha_modificacion
+workspace : ForeignKey
+enfermeras : ManyToMany
+turnos : ManyToMany
+patrones_turnos : ManyToMany
}
class Ejecucion {
+ESTADO_CHOICES
+FK configuracion
+string estado
+datetime fecha_inicio
+datetime fecha_fin
+boolean es_optima
+float penalizacion_total
+JSON resultado
+JSON mensajes
+workspace : ForeignKey
}
class Planilla {
+string nombre
+string descripcion
+FK ejecucion
+date fecha_inicio
+date fecha_fin
+int num_dias
+workspace : ForeignKey
}
class AsignacionTurno {
+FK planilla
+FK enfermera
+date fecha
+FK turno
+boolean es_dia_libre
+string observaciones
+string tipo_celda
+unique_together : (planilla, enfermera, fecha)
+workspace : ForeignKey
}
class ContratoEnfermera {
+decimal horas_semana_objetivo
+decimal horas_anuales_objetivo
+decimal porcentaje_jornada
+date fecha_inicio_vigencia
+date fecha_fin_vigencia
+FK enfermera
}
class RotacionBase {
+string nombre
+string descripcion
+int ciclo_dias
+workspace : ForeignKey
}
class CeldaRotacion {
+int orden
+boolean es_libre
+FK turno
+FK rotacion
+unique_together : (rotacion, orden)
}
class AsignacionRotacionEnfermera {
+int desfase
+date fecha_inicio
+date fecha_fin
+FK enfermera
+FK rotacion
}
class Incidencia {
+string tipo
+date fecha_inicio
+date fecha_fin
+string observaciones
+FK enfermera
+FK turno_fijo
}
class BalanceHistoricoEnfermera {
+string periodo_referencia
+decimal horas_acumuladas_previas
+int noches_acumuladas
+int fines_semana_acumulados
+int festivos_acumulados
+date ultimo_turno_fecha
+FK ultimo_turno_tipo
+unique_together : (enfermera, periodo_referencia)
}
Workspace "1" <-- "many" Enfermera
Workspace "1" <-- "many" TipoTurno
Workspace "1" <-- "many" ConfiguracionPlanificacion
Workspace "1" <-- "many" Ejecucion
Workspace "1" <-- "many" Planilla
Workspace "1" <-- "many" AsignacionTurno
Workspace "1" <-- "many" RotacionBase
Workspace "1" <-- "many" BalanceHistoricoEnfermera
ConfiguracionPlanificacion "1" --> "many" Ejecucion
Ejecucion "1" --> "1" Planilla
Planilla "1" --> "many" AsignacionTurno
Enfermera "1" --> "many" AsignacionTurno
TipoTurno "1" --> "many" AsignacionTurno
Enfermera "1" --> "1" ContratoEnfermera
Enfermera "1" --> "many" Incidencia
RotacionBase "1" --> "many" CeldaRotacion
Enfermera "1" --> "many" AsignacionRotacionEnfermera
RotacionBase "1" --> "many" AsignacionRotacionEnfermera
```

**Diagram sources**
- [models.py:12-825](file://turnos/models.py#L12-L825)

## Detailed Component Analysis

### Database Schema Design and Relationships
- Workspace acts as the tenant boundary; all major entities include a workspace foreign key (with exceptions noted below).
- Enfermera and TipoTurno support workspace scoping; legacy admin comments indicate future workspace enforcement.
- ConfiguracionPlanificacion links Enfermera and TipoTurno sets and holds planning metadata.
- Ejecucion captures planning runs with state transitions and results.
- Planilla stores generated schedules and AsignacionTurno records individual assignments.
- Advanced domain models extend planning capabilities:
  - ContratoEnfermera defines contractual hours.
  - RotacionBase and CeldaRotacion define cyclic patterns.
  - AsignacionRotacionEnfermera assigns rotations to nurses with offsets.
  - Incidencia records absence events.
  - BalanceHistoricoEnfermera tracks cumulative metrics per nurse and period.

```mermaid
erDiagram
WORKSPACE ||--o{ ENFERMERA : "contains"
WORKSPACE ||--o{ TIPO_TURNO : "contains"
WORKSPACE ||--o{ CONFIGURACION_PLANIFICACION : "contains"
WORKSPACE ||--o{ EJECUCION : "contains"
WORKSPACE ||--o{ PLANILLA : "contains"
WORKSPACE ||--o{ ASIGNACION_TURNO : "contains"
WORKSPACE ||--o{ ROTACION_BASE : "contains"
WORKSPACE ||--o{ BALANCE_HISTORICO_ENFERMERA : "contains"
CONFIGURACION_PLANIFICACION }o--o{ ENFERMERA : "selected"
CONFIGURACION_PLANIFICACION }o--o{ TIPO_TURNO : "selected"
EJECUCION }o--|| CONFIGURACION_PLANIFICACION : "references"
PLANILLA }o--|| EJECUCION : "generated_from"
ASIGNACION_TURNO }o--|| PLANILLA : "belongs_to"
ASIGNACION_TURNO }o--|| ENFERMERA : "assigned_to"
ASIGNACION_TURNO }o--|| TIPO_TURNO : "assigned_turn"
CONTRATO_ENFERMERA }o--|| ENFERMERA : "defines_for"
INCIDENCIA }o--|| ENFERMERA : "records_for"
ROTACION_BASE ||--o{ CELDA_ROTACION : "defines_pattern"
ASIGNACION_ROTACION_ENFERMERA }o--|| ENFERMERA : "assigns_to"
ASIGNACION_ROTACION_ENFERMERA }o--|| ROTACION_BASE : "uses_pattern"
```

**Diagram sources**
- [models.py:12-825](file://turnos/models.py#L12-L825)

**Section sources**
- [models.py:12-825](file://turnos/models.py#L12-L825)

### Multi-Workspace Data Isolation
- Workspace is the tenant discriminator. New models include workspace foreign keys; legacy models lack this field but admin comments indicate future migration plans.
- Admin configurations reflect current state, with comments noting workspace-enabled lists pending migration completion.
- PostgreSQL initialization script outlines Row Level Security (RLS) policy examples for future enforcement, although RLS is not enabled in the provided script.

Recommendations:
- Enforce workspace filtering at query time using middleware or per-view scopes.
- Add workspace-aware permissions and enforce RLS in production environments.

**Section sources**
- [models.py:12-825](file://turnos/models.py#L12-L825)
- [admin.py:270-294](file://turnos/admin.py#L270-L294)
- [init.sql:265-276](file://docker/postgres/init.sql#L265-L276)

### Django Admin Interface Configuration
Key customizations:
- TipoTurnoAdmin: Color badges, inline fields, and computed duration and night shift detection.
- PatronTurnosAdmin: Dynamic textarea hints for configuration JSON based on selected type.
- ConfiguracionPlanificacionAdmin: Horizontal filters for ManyToMany relations, readonly audit fields, and detail link.
- EjecucionAdmin: Status badges, result link, readonly durations and messages.
- PlanillaAdmin: Inline count of assignments.
- AsignacionTurnoAdmin: Date hierarchy and search by nurse and plan.
- WorkspaceAdmin: Horizontal filter for users.
- Advanced domain admins: Inline editing for rotation cycles, contract validity, incidence periods, and historical balances.

**Section sources**
- [admin.py:16-449](file://turnos/admin.py#L16-L449)

### Celery Integration for Asynchronous Processing
Celery app configuration:
- Autodiscovers tasks and binds to Django settings.

Planning tasks:
- Shared task executes planning asynchronously, validates inputs, manages atomic transactions, updates Ejecucion states, persists Planilla and AsignacionTurno entries, and handles retries with exponential backoff.
- Alternative motor task orchestrates a new pipeline with richer domain models, including contracts, historical balances, and rotation patterns.
- Utility tasks include cleanup of old executions and statistics reporting.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Celery as "Celery Worker"
participant Task as "ejecutar_planificacion_async"
participant ORM as "Django ORM"
participant Gen as "GeneradorTurnos"
participant DB as "PostgreSQL"
Client->>Celery : send "ejecutar_planificacion_async(configuracion_id)"
Celery->>Task : bind and execute
Task->>ORM : select_related ConfiguracionPlanificacion
ORM-->>Task : Config object
Task->>ORM : transaction.atomic() create Ejecucion(PROCESSING)
Task->>Gen : initialize and generate()
Gen-->>Task : result dict
Task->>ORM : transaction.atomic() update Ejecucion(COMPLETADA/ERROR/INVIABLE)
alt success
Task->>ORM : create Planilla
Task->>ORM : bulk_create AsignacionTurno
end
Task-->>Celery : return structured result
Celery-->>Client : task result
```

**Diagram sources**
- [tasks.py:17-240](file://turnos/tasks.py#L17-L240)
- [celery.py:1-14](file://proyecto_turnos/celery.py#L1-L14)

**Section sources**
- [tasks.py:17-716](file://turnos/tasks.py#L17-L716)
- [celery.py:1-14](file://proyecto_turnos/celery.py#L1-L14)

### Export Processing System
Export utilities:
- Excel exporter: Seven-sheet workbook (vertical/horizontal plan, statistics, per-nurse distribution, coverage, equity, validations).
- Professional exporter: Advanced Excel/PDF with statistics, charts, and validation reports.
- CSV/JSON/iCal exporters: Lightweight formats for interoperability.

Workflow:
- Views trigger export functions using persisted Ejecucion and Planilla data.
- Exporters translate ORM objects into structured dictionaries and render to target formats.

```mermaid
flowchart TD
Start(["Export Request"]) --> Validate["Validate Ejecucion presence"]
Validate --> |OK| BuildData["Build export data from Planilla and Assignments"]
Validate --> |Missing| Error["Return error response"]
BuildData --> ChooseFormat{"Choose format"}
ChooseFormat --> |Excel| Excel["Generate 7-sheet Excel"]
ChooseFormat --> |PDF| Pdf["Generate PDF matrix + stats"]
ChooseFormat --> |CSV| Csv["Generate CSV"]
ChooseFormat --> |JSON| Json["Generate JSON"]
ChooseFormat --> |iCal| Ical["Generate iCalendar"]
Excel --> Deliver["Return file stream"]
Pdf --> Deliver
Csv --> Deliver
Json --> Deliver
Ical --> Deliver
Deliver --> End(["Done"])
```

**Diagram sources**
- [exportacion.py:135-665](file://turnos/utils/exportacion.py#L135-L665)
- [exportador_profesional.py:256-990](file://turnos/utils/exportador_profesional.py#L256-L990)
- [views.py:26-48](file://turnos/views.py#L26-L48)

**Section sources**
- [exportacion.py:1-665](file://turnos/utils/exportacion.py#L1-L665)
- [exportador_profesional.py:1-990](file://turnos/utils/exportador_profesional.py#L1-L990)
- [views.py:26-48](file://turnos/views.py#L26-L48)

### Database Migration Strategy
- Initial migration establishes core entities and relationships.
- Domain models migration adds advanced planning entities and fields.
- Type field migration introduces “sustituto_libre” flag for flexible absence modeling.
- These migrations evolve the schema while preserving data integrity.

```mermaid
graph LR
A["0001_initial.py"] --> B["0009_add_domain_models.py"]
B --> C["0014_tipoturno_sustituto_libre.py"]
```

**Diagram sources**
- [0001_initial.py:1-140](file://turnos/migrations/0001_initial.py#L1-L140)
- [0009_add_domain_models.py:1-123](file://turnos/migrations/0009_add_domain_models.py#L1-L123)
- [0014_tipoturno_sustituto_libre.py:1-19](file://turnos/migrations/0014_tipoturno_sustituto_libre.py#L1-L19)

**Section sources**
- [0001_initial.py:1-140](file://turnos/migrations/0001_initial.py#L1-L140)
- [0009_add_domain_models.py:1-123](file://turnos/migrations/0009_add_domain_models.py#L1-L123)
- [0014_tipoturno_sustituto_libre.py:1-19](file://turnos/migrations/0014_tipoturno_sustituto_libre.py#L1-L19)

### Model Validation Rules and Data Integrity Constraints
- Unique constraints on TipoTurno for workspace-scoped name and code.
- Unique constraint on CeldaRotacion for rotation+order uniqueness.
- Unique constraint on BalanceHistoricoEnfermera for nurse+period combination.
- Model-level clean/validation methods enforce business rules (e.g., turn timing, substitute-free constraints).
- Ejecucion state machine and atomic transaction boundaries ensure consistency during planning.

**Section sources**
- [models.py:113-124](file://turnos/models.py#L113-L124)
- [models.py:712-720](file://turnos/models.py#L712-L720)
- [models.py:818-822](file://turnos/models.py#L818-L822)
- [models.py:126-168](file://turnos/models.py#L126-L168)
- [tasks.py:70-126](file://turnos/tasks.py#L70-L126)

### Examples of Queries, Task Scheduling, and Transactions
- Queries:
  - Select related configuration and prefetch related entities for efficient rendering.
  - Filter recent executions and distinct dates for dashboard statistics.
  - Use unique constraints and unique together tuples to prevent duplicates.
- Task scheduling:
  - Use shared_task to enqueue planning jobs.
  - Retry with bounded attempts and delays for transient failures.
- Transactions:
  - Wrap planning result persistence and plan creation in atomic blocks.
  - Update Ejecucion state and results atomically.

**Section sources**
- [views.py:64-95](file://turnos/views.py#L64-L95)
- [tasks.py:17-240](file://turnos/tasks.py#L17-L240)
- [tasks.py:563-639](file://turnos/tasks.py#L563-L639)

## Dependency Analysis
- Models depend on Django ORM and Python standard libraries.
- Admin depends on models and Django admin components.
- Tasks depend on models and external libraries for export formats.
- Celery app depends on Django settings and autodiscovers tasks.
- PostgreSQL init script configures extensions, search, views, and indices.

```mermaid
graph TB
M["Models"] --> A["Admin"]
M --> T["Tasks"]
T --> C["Celery App"]
M --> V["Views"]
M --> U["Export Utils"]
SQL["PostgreSQL Init"] --> M
```

**Diagram sources**
- [models.py:12-825](file://turnos/models.py#L12-L825)
- [admin.py:1-449](file://turnos/admin.py#L1-L449)
- [tasks.py:1-716](file://turnos/tasks.py#L1-L716)
- [celery.py:1-14](file://proyecto_turnos/celery.py#L1-L14)
- [exportacion.py:1-665](file://turnos/utils/exportacion.py#L1-L665)
- [init.sql:1-508](file://docker/postgres/init.sql#L1-L508)

**Section sources**
- [models.py:12-825](file://turnos/models.py#L12-L825)
- [admin.py:1-449](file://turnos/admin.py#L1-L449)
- [tasks.py:1-716](file://turnos/tasks.py#L1-L716)
- [celery.py:1-14](file://proyecto_turnos/celery.py#L1-L14)
- [exportacion.py:1-665](file://turnos/utils/exportacion.py#L1-L665)
- [init.sql:1-508](file://docker/postgres/init.sql#L1-L508)

## Performance Considerations
- PostgreSQL Extensions and Search:
  - Extensions: uuid-ossp, pg_trgm, unaccent, hstore, pgcrypto.
  - Text search configuration for Spanish without accents.
  - Additional TRGM indices on name/email fields for improved search performance.
- Indices:
  - Django auto-generated indices plus TRGM indices for text search.
  - Consider composite indices for frequent filter/sort patterns (e.g., Ejecucion state+date).
- Views:
  - Materialized or regular views for common aggregates (e.g., active nurses, configuration stats).
- Auditing and Maintenance:
  - Audit triggers capture create/update/delete actions.
  - Automated maintenance functions for reindexing and statistics updates.
- Application-Level:
  - Use select_related/prefetch_related in views to reduce N+1 queries.
  - Bulk operations for assignment creation.
  - Caching for repeated computations (e.g., throttling decorator).

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Workspace Isolation:
  - Symptom: Cross-tenant data visibility.
  - Resolution: Enforce workspace filtering in views and admin; consider enabling RLS.
- Planning Failures:
  - Symptom: Ejecucion marked ERROR with messages.
  - Resolution: Inspect task logs, validate configuration constraints, retry with corrected inputs.
- Export Errors:
  - Symptom: Missing optional dependencies (openpyxl, reportlab, icalendar).
  - Resolution: Install extras and rerun export.
- Index/Query Performance:
  - Symptom: Slow searches or aggregates.
  - Resolution: Review TRGM indices and consider adding composite indices; analyze query plans.

**Section sources**
- [tasks.py:204-240](file://turnos/tasks.py#L204-L240)
- [init.sql:233-249](file://docker/postgres/init.sql#L233-L249)
- [mixins.py:110-138](file://turnos/mixins.py#L110-L138)
- [decorators.py:110-142](file://turnos/decorators.py#L110-L142)

## Conclusion
The Persistence Layer integrates Django ORM with PostgreSQL to support multi-workspace planning, robust model validation, and scalable asynchronous execution via Celery. Admin customization streamlines operations, while comprehensive export utilities deliver actionable outputs. The migration strategy and PostgreSQL enhancements lay a solid foundation for performance and maintainability.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Indexing Strategies
- TRGM indices on textual fields for fuzzy search.
- Unique constraints for business integrity (type codes, rotation cells, historical balances).
- Consider composite indices for common query patterns.

**Section sources**
- [init.sql:233-249](file://docker/postgres/init.sql#L233-L249)
- [models.py:113-124](file://turnos/models.py#L113-L124)
- [models.py:712-720](file://turnos/models.py#L712-L720)
- [models.py:818-822](file://turnos/models.py#L818-L822)

### Transaction Handling Patterns
- Atomic blocks around Ejecucion state updates and Planilla/AsignacionTurno creation.
- Bulk creation to minimize round-trips.

**Section sources**
- [tasks.py:70-126](file://turnos/tasks.py#L70-L126)
- [tasks.py:563-639](file://turnos/tasks.py#L563-L639)
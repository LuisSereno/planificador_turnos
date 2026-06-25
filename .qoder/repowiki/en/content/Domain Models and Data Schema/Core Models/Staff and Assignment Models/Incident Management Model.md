# Incident Management Model

<cite>
**Referenced Files in This Document**
- [models.py](file://turnos/models.py)
- [dtos.py](file://turnos/dominio/dtos.py)
- [vocabulario.py](file://turnos/dominio/vocabulario.py)
- [incidencias.py](file://turnos/motor/incidencias.py)
- [overlay_incidencias.py](file://turnos/motor/overlay_incidencias.py)
- [pipeline.py](file://turnos/motor/pipeline.py)
- [admin.py](file://turnos/admin.py)
- [adaptadores.py](file://turnos/dominio/adaptadores.py)
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
This document explains the Incidencia model and its integration with the planning system. It covers the six incident types (vacaciones, permiso, baja médica, formación, libranza bloqueada, asignación fija), date range management, and how incidents override normal scheduling. It also documents fixed assignment scenarios, the post-generation overlay mechanism, and the impact on coverage calculations. Practical examples illustrate incident creation, conflict resolution with planned shifts, and incident-based schedule modifications.

## Project Structure
The incident management spans three layers:
- Domain model and DTOs define the canonical types and data structures.
- Motor (pipeline) applies hard constraints during generation and overlays soft overrides after generation.
- Django models persist incidents and expose them via admin and forms.

```mermaid
graph TB
subgraph "Domain Layer"
DT["dtos.py<br/>Incidencia, MatrizPlanificacion, TurnoInfo"]
VOC["vocabulario.py<br/>TIPOS_INCIDENCIA, TIPOS_CELDA"]
AD["adaptadores.py<br/>AdaptadorIncidenciasLegacy"]
end
subgraph "Motor Layer"
AP["incidencias.py<br/>AplicadorIncidencias (hard block)"]
OV["overlay_incidencias.py<br/>OverlayIncidencias (post-gen)"]
PL["pipeline.py<br/>PipelinePlanificacion orchestrates"]
end
subgraph "Persistence Layer"
MD["models.py<br/>Incidencia (Django model)"]
ADM["admin.py<br/>IncidenciaAdmin"]
end
MD --> DT
DT --> AP
DT --> OV
AP --> PL
OV --> PL
AD --> DT
ADM --> MD
```

**Diagram sources**
- [dtos.py:169-181](file://turnos/dominio/dtos.py#L169-L181)
- [vocabulario.py:61-70](file://turnos/dominio/vocabulario.py#L61-L70)
- [incidencias.py:21-98](file://turnos/motor/incidencias.py#L21-L98)
- [overlay_incidencias.py:24-76](file://turnos/motor/overlay_incidencias.py#L24-L76)
- [pipeline.py:31-267](file://turnos/motor/pipeline.py#L31-L267)
- [models.py:749-784](file://turnos/models.py#L749-L784)
- [admin.py:386-415](file://turnos/admin.py#L386-L415)
- [adaptadores.py:149-203](file://turnos/dominio/adaptadores.py#L149-L203)

**Section sources**
- [models.py:749-784](file://turnos/models.py#L749-L784)
- [dtos.py:169-181](file://turnos/dominio/dtos.py#L169-L181)
- [vocabulario.py:61-70](file://turnos/dominio/vocabulario.py#L61-L70)
- [incidencias.py:21-98](file://turnos/motor/incidencias.py#L21-L98)
- [overlay_incidencias.py:24-76](file://turnos/motor/overlay_incidencias.py#L24-L76)
- [pipeline.py:31-267](file://turnos/motor/pipeline.py#L31-L267)
- [admin.py:386-415](file://turnos/admin.py#L386-L415)
- [adaptadores.py:149-203](file://turnos/dominio/adaptadores.py#L149-L203)

## Core Components
- Incidencia Django model: stores event metadata, links to a nurse, and optional fixed shift.
- DTO Incidencia: canonical domain representation used across the pipeline.
- AplicadorIncidencias: hard-blocks cells during generation (phase 2).
- OverlayIncidencias: post-generation deterministic overlay (phase 6) that replaces or blocks turns and detects coverage deficits.
- PipelinePlanificacion: orchestrates the five core phases; overlay is applied after solver completion.
- Vocabulary: canonical definitions for incident types and cell types.

Key responsibilities:
- Date range management: inclusive start and end dates per incident.
- Override behavior: hard block vs. soft overlay depending on phase.
- Fixed assignment: optional fixed shift for ASIGNACION_FIJA.
- Coverage impact: overlay detects deficits against configured minimum coverage.

**Section sources**
- [models.py:749-784](file://turnos/models.py#L749-L784)
- [dtos.py:169-181](file://turnos/dominio/dtos.py#L169-L181)
- [incidencias.py:21-98](file://turnos/motor/incidencias.py#L21-L98)
- [overlay_incidencias.py:24-76](file://turnos/motor/overlay_incidencias.py#L24-L76)
- [pipeline.py:31-267](file://turnos/motor/pipeline.py#L31-L267)
- [vocabulario.py:61-70](file://turnos/dominio/vocabulario.py#L61-L70)

## Architecture Overview
The pipeline separates hard constraints (during generation) from soft overrides (after generation). Incidents are not part of automatic generation; they are applied as a post-processing overlay.

```mermaid
sequenceDiagram
participant Planner as "PipelinePlanificacion"
participant Solver as "CP-SAT Solver"
participant Overlay as "OverlayIncidencias"
participant Matrix as "MatrizPlanificacion"
Planner->>Solver : "Generate base matrix (5 phases)"
Solver-->>Planner : "Matrix with regular assignments"
Planner->>Overlay : "Apply overlay with Incidencia list"
Overlay->>Matrix : "Clone matrix"
Overlay->>Matrix : "For each date in incidence range : <br/>- Replace/Block cell<br/>- Track overwritten cells<br/>- Detect coverage deficits"
Overlay-->>Planner : "Final matrix + metrics"
```

**Diagram sources**
- [pipeline.py:92-234](file://turnos/motor/pipeline.py#L92-L234)
- [overlay_incidencias.py:45-75](file://turnos/motor/overlay_incidencias.py#L45-L75)

**Section sources**
- [pipeline.py:31-267](file://turnos/motor/pipeline.py#L31-L267)
- [overlay_incidencias.py:24-76](file://turnos/motor/overlay_incidencias.py#L24-L76)

## Detailed Component Analysis

### Incidencia Django Model
- Fields:
  - nurse relation, type choice, inclusive date range, optional fixed shift, free-text observations.
  - Ordered by start date for chronological processing.
- Behavior:
  - String representation includes nurse name, type, and date range.
  - Admin exposes duration in days and whether a fixed shift is set.

```mermaid
classDiagram
class IncidenciaModel {
+enfermera_id
+tipo
+fecha_inicio
+fecha_fin
+turno_fijo_id
+observaciones
+__str__()
}
class IncidenciaDTO {
+enfermera_id
+enfermera_nombre
+tipo
+fecha_inicio
+fecha_fin
+turno_fijo
+afecta_fecha(date) bool
}
IncidenciaModel --> IncidenciaDTO : "converted by AdaptadorIncidenciasLegacy"
```

**Diagram sources**
- [models.py:749-784](file://turnos/models.py#L749-L784)
- [dtos.py:169-181](file://turnos/dominio/dtos.py#L169-L181)
- [adaptadores.py:149-203](file://turnos/dominio/adaptadores.py#L149-L203)

**Section sources**
- [models.py:749-784](file://turnos/models.py#L749-L784)
- [admin.py:386-415](file://turnos/admin.py#L386-L415)
- [adaptadores.py:149-203](file://turnos/dominio/adaptadores.py#L149-L203)

### Incident Types and Cell Types
- Canonical incident types: VACACIONES, PERMISO, BAJA, FORMACION, LIBRANZA_BLOQUEADA, ASIGNACION_FIJA.
- Canonical cell types: TURNO, LIBRE, VACACIONES, PERMISO, BAJA, FORMACION, ASIGNACION_FIJA.
- These definitions ensure consistent behavior across legacy conversions and overlay logic.

```mermaid
flowchart TD
A["Incidente DTO"] --> B{"Tipo"}
B --> |VACACIONES| C["Cell: VACACIONES<br/>Turno=None<br/>No modifiable"]
B --> |PERMISO| D["Cell: PERMISO<br/>Turno=None<br/>No modifiable"]
B --> |BAJA| E["Cell: BAJA<br/>Turno=None<br/>No modifiable"]
B --> |FORMACION| F["Cell: FORMACION<br/>Keep existing turno if any<br/>No modifiable"]
B --> |LIBRANZA_BLOQUEADA| G["Cell: LIBRE<br/>Turno=None<br/>No modifiable"]
B --> |ASIGNACION_FIJA| H{"Has turno_fijo?"}
H --> |Yes| I["Cell: ASIGNACION_FIJA<br/>Set fixed turno<br/>No modifiable"]
H --> |No| J["Cell: LIBRE<br/>Turno=None<br/>No modifiable"]
```

**Diagram sources**
- [dtos.py:33-41](file://turnos/dominio/dtos.py#L33-L41)
- [dtos.py:22-31](file://turnos/dominio/dtos.py#L22-L31)
- [overlay_incidencias.py:109-151](file://turnos/motor/overlay_incidencias.py#L109-L151)

**Section sources**
- [vocabulario.py:61-70](file://turnos/dominio/vocabulario.py#L61-L70)
- [dtos.py:33-41](file://turnos/dominio/dtos.py#L33-L41)
- [dtos.py:22-31](file://turnos/dominio/dtos.py#L22-L31)
- [overlay_incidencias.py:109-151](file://turnos/motor/overlay_incidencias.py#L109-L151)

### Hard Block During Generation (AplicadorIncidencias)
- Purpose: mark affected cells as non-modifiable and set cell type during generation (phase 2).
- Behavior:
  - Iterates over the date range for each incident.
  - Finds matching cell in the base matrix and applies type-specific rules.
  - Sets observaciones for traceability.

```mermaid
flowchart TD
Start(["Start AplicadorIncidencias.aplicar"]) --> LoopInc["For each Incidencia"]
LoopInc --> Range["Iterate dates from inicio to fin"]
Range --> Find["Find cell in MatrizPlanificacion"]
Find --> Exists{"Cell exists?"}
Exists --> |No| NextDate["Next date"]
Exists --> |Yes| Apply["Apply type rule:<br/>- VAC/PERM/BAJA → VAC/PERM/BAJA<br/>- FORM → FORM<br/>- LIBRANZA → LIBRE<br/>- ASIGNACION_FIJA → set fixed turno"]
Apply --> Block["Mark cell as non-modifiable"]
Block --> NextDate
NextDate --> Done{"More dates?"}
Done --> |Yes| Range
Done --> |No| End(["Return modified matrix"])
```

**Diagram sources**
- [incidencias.py:37-98](file://turnos/motor/incidencias.py#L37-L98)

**Section sources**
- [incidencias.py:21-98](file://turnos/motor/incidencias.py#L21-L98)

### Post-Generation Overlay (OverlayIncidencias)
- Purpose: apply deterministic overlay after solver completion (phase 6).
- Behavior:
  - Clones the matrix to avoid mutating the original.
  - For each incident date, overwrites or blocks the cell and records overwritten cells.
  - Computes hours lost per overwrite and detects coverage deficits compared to configured minimums.

```mermaid
sequenceDiagram
participant O as "OverlayIncidencias"
participant M as "MatrizPlanificacion"
participant R as "ResultadoOverlay"
O->>M : "clone()"
loop For each Incidencia
O->>O : "_aplicar_incidencia(M, incidencia)"
O->>M : "obtener_celda(enfermera_id, fecha)"
O->>O : "_sobrescribir_celda(celda, incidencia)"
O->>O : "track overwritten cell + hours lost"
end
O->>O : "_detectar_huecos_cobertura(M)"
O-->>R : "matriz_final, celdas_sobreescritas, huecos_cobertura"
```

**Diagram sources**
- [overlay_incidencias.py:45-75](file://turnos/motor/overlay_incidencias.py#L45-L75)
- [overlay_incidencias.py:77-94](file://turnos/motor/overlay_incidencias.py#L77-L94)
- [overlay_incidencias.py:96-164](file://turnos/motor/overlay_incidencias.py#L96-L164)
- [overlay_incidencias.py:166-205](file://turnos/motor/overlay_incidencias.py#L166-L205)

**Section sources**
- [overlay_incidencias.py:24-76](file://turnos/motor/overlay_incidencias.py#L24-L76)
- [overlay_incidencias.py:166-205](file://turnos/motor/overlay_incidencias.py#L166-L205)

### Date Range Management
- Both the Django model and the DTO store inclusive date ranges.
- The pipeline and overlay iterate from start to end date, applying the incident to each date in the range.
- Legacy adapters normalize old keys to canonical DTO types.

```mermaid
flowchart TD
A["Incidencia DTO"] --> B["Iterate date from fecha_inicio to fecha_fin"]
B --> C["Lookup cell in MatrizPlanificacion"]
C --> D{"Cell exists?"}
D --> |Yes| E["Apply incident rule"]
D --> |No| F["Skip (no-op)"]
```

**Diagram sources**
- [dtos.py:179-181](file://turnos/dominio/dtos.py#L179-L181)
- [overlay_incidencias.py:83-94](file://turnos/motor/overlay_incidencias.py#L83-L94)
- [adaptadores.py:178-183](file://turnos/dominio/adaptadores.py#L178-L183)

**Section sources**
- [dtos.py:179-181](file://turnos/dominio/dtos.py#L179-L181)
- [overlay_incidencias.py:83-94](file://turnos/motor/overlay_incidencias.py#L83-L94)
- [adaptadores.py:178-183](file://turnos/dominio/adaptadores.py#L178-L183)

### Fixed Assignment Scenarios (ASIGNACION_FIJA)
- If a fixed shift is provided, the cell becomes ASIGNACION_FIJA and is non-modifiable.
- If no fixed shift is provided, the cell becomes LIBRE (blocked).
- Overlay preserves the intent: either a fixed shift is enforced or the day is blocked.

```mermaid
flowchart TD
A["ASIGNACION_FIJA"] --> B{"turno_fijo present?"}
B --> |Yes| C["Set turno = fixed<br/>tipo_celda = ASIGNACION_FIJA<br/>non-modifiable"]
B --> |No| D["Set tipo_celda = LIBRE<br/>non-modifiable"]
```

**Diagram sources**
- [overlay_incidencias.py:139-151](file://turnos/motor/overlay_incidencias.py#L139-L151)
- [incidencias.py:85-91](file://turnos/motor/incidencias.py#L85-L91)

**Section sources**
- [overlay_incidencias.py:139-151](file://turnos/motor/overlay_incidencias.py#L139-L151)
- [incidencias.py:85-91](file://turnos/motor/incidencias.py#L85-L91)

### Impact on Coverage Calculations
- Overlay detects coverage deficits by counting assigned persons per turno in each date and comparing to configured minimums.
- Deficit entries include date, turno_id, deficit, assigned, and required counts.

```mermaid
flowchart TD
Start(["Overlay complete"]) --> Scan["For each date"]
Scan --> Count["Count assigned persons per turno<br/>(only TURNO and ASIGNACION_FIJA count)"]
Count --> Compare{"Assigned < Required?"}
Compare --> |Yes| Record["Record deficit entry"]
Compare --> |No| NextDate["Next date"]
Record --> NextDate
NextDate --> Done(["Return huecos_cobertura"])
```

**Diagram sources**
- [overlay_incidencias.py:166-205](file://turnos/motor/overlay_incidencias.py#L166-L205)

**Section sources**
- [overlay_incidencias.py:166-205](file://turnos/motor/overlay_incidencias.py#L166-L205)

### Examples

#### Example: Creating an Incident
- Use the Django admin to create an Incidencia with:
  - Nurse, type, inclusive start and end dates.
  - Optional fixed shift for ASIGNACION_FIJA.
  - Observations for auditability.

Admin UI highlights:
- Duration in days computed automatically.
- Toggle for fixed shift presence.

**Section sources**
- [admin.py:386-415](file://turnos/admin.py#L386-L415)
- [models.py:749-784](file://turnos/models.py#L749-L784)

#### Example: Conflict Resolution with Planned Shifts
- If a planned shift conflicts with an incident (e.g., VACACIONES), the overlay replaces the planned shift with a VACACIONES cell and marks it non-modifiable.
- The solver’s prior decisions are preserved; overlay only affects cells that existed before.

**Section sources**
- [overlay_incidencias.py:109-114](file://turnos/motor/overlay_incidencias.py#L109-L114)
- [pipeline.py:92-102](file://turnos/motor/pipeline.py#L92-L102)

#### Example: Incident-Based Schedule Modification
- For FORMACION, if the nurse was scheduled for a shift, the overlay keeps the existing turno (they may be training while working).
- For LIBRANZA_BLOQUEADA, the overlay sets the cell to LIBRE and non-modifiable.
- For ASIGNACION_FIJA without a fixed shift, the overlay sets LIBRE; with a fixed shift, it sets ASIGNACION_FIJA.

**Section sources**
- [overlay_incidencias.py:127-131](file://turnos/motor/overlay_incidencias.py#L127-L131)
- [overlay_incidencias.py:133-151](file://turnos/motor/overlay_incidencias.py#L133-L151)

## Dependency Analysis
- The Django model Incidencia is converted to the DTO Incidencia for use in the pipeline.
- AplicadorIncidencias and OverlayIncidencias both depend on the DTO definitions for types and matrices.
- Pipeline orchestration does not include incidents in the solver; overlay is the separate post-generation step.

```mermaid
graph LR
MD["models.py: Incidencia"] --> AD["adaptadores.py: AdaptadorIncidenciasLegacy"]
AD --> DT["dtos.py: Incidencia"]
DT --> AP["incidencias.py: AplicadorIncidencias"]
DT --> OV["overlay_incidencias.py: OverlayIncidencias"]
AP --> PL["pipeline.py: PipelinePlanificacion"]
OV --> PL
```

**Diagram sources**
- [models.py:749-784](file://turnos/models.py#L749-L784)
- [adaptadores.py:149-203](file://turnos/dominio/adaptadores.py#L149-L203)
- [dtos.py:169-181](file://turnos/dominio/dtos.py#L169-L181)
- [incidencias.py:21-98](file://turnos/motor/incidencias.py#L21-L98)
- [overlay_incidencias.py:24-76](file://turnos/motor/overlay_incidencias.py#L24-L76)
- [pipeline.py:31-267](file://turnos/motor/pipeline.py#L31-L267)

**Section sources**
- [models.py:749-784](file://turnos/models.py#L749-L784)
- [adaptadores.py:149-203](file://turnos/dominio/adaptadores.py#L149-L203)
- [dtos.py:169-181](file://turnos/dominio/dtos.py#L169-L181)
- [incidencias.py:21-98](file://turnos/motor/incidencias.py#L21-L98)
- [overlay_incidencias.py:24-76](file://turnos/motor/overlay_incidencias.py#L24-L76)
- [pipeline.py:31-267](file://turnos/motor/pipeline.py#L31-L267)

## Performance Considerations
- Overlay clones the matrix; memory usage scales with number of nurses × number of days.
- Overwrite detection and coverage deficit scanning are linear in the number of cells processed.
- Prefer limiting incident ranges to necessary periods to reduce iteration overhead.

## Troubleshooting Guide
- Incidents not applied:
  - Verify the incident date range overlaps with the planning period.
  - Confirm the nurse exists in the current planilla.
- Unexpected LIBRE cells:
  - Check if ASIGNACION_FIJA lacks a fixed shift; absence implies LIBRE.
- Coverage deficits:
  - Review configured minimum coverage per turno and compare to actual assignments after overlay.
- Audit trail:
  - Use observaciones and overwritten cells logs to track changes.

**Section sources**
- [overlay_incidencias.py:166-205](file://turnos/motor/overlay_incidencias.py#L166-L205)
- [overlay_incidencias.py:156-164](file://turnos/motor/overlay_incidencias.py#L156-L164)

## Conclusion
The Incidencia model integrates tightly with the planning pipeline by separating hard constraints during generation from soft overlays after generation. Six canonical incident types are supported, with clear override semantics and coverage impact detection. Admin and DTO layers ensure consistent behavior across legacy formats and runtime operations.
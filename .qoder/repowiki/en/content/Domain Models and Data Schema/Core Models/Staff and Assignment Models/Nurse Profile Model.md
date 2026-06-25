# Nurse Profile Model

<cite>
**Referenced Files in This Document**
- [models.py](file://turnos/models.py)
- [forms.py](file://turnos/forms.py)
- [views.py](file://turnos/views.py)
- [urls.py](file://turnos/urls.py)
- [admin.py](file://turnos/admin.py)
- [enfermera_detail.html](file://turnos/templates/turnos/enfermera_detail.html)
- [enfermera_form.html](file://turnos/templates/turnos/enfermera_form.html)
- [enfermera_list.html](file://turnos/templates/turnos/enfermera_list.html)
- [demo_enfermeras.json](file://turnos/fixtures/demo_enfermeras.json)
- [importar_enfermeras.py](file://turnos/management/commands/importar_enfermeras.py)
- [init.sql](file://docker/postgres/init.sql)
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
This document provides comprehensive documentation for the Enfermera (Nurse) model that represents nurse profiles in the turnos system. The Enfermera model serves as the central entity for managing nurse information, employment status, preferences, and multi-tenancy isolation through Workspace relationships. This documentation covers the complete lifecycle of nurse profiles including registration, validation, URL generation, querying patterns, and integration with the broader scheduling system.

## Project Structure
The Enfermera model is part of the turnos Django application and integrates with several key components:

```mermaid
graph TB
subgraph "Django Application Structure"
Models[turnos/models.py]
Forms[turnos/forms.py]
Views[turnos/views.py]
Admin[turnos/admin.py]
URLs[turnos/urls.py]
end
subgraph "Templates"
Detail[turnos/templates/turnos/enfermera_detail.html]
Form[turnos/templates/turnos/enfermera_form.html]
List[turnos/templates/turnos/enfermera_list.html]
end
subgraph "Data Management"
Demo[demo_enfermeras.json]
Import[importar_enfermeras.py]
SQL[init.sql]
end
Models --> Forms
Forms --> Views
Views --> Templates
Views --> URLs
Admin --> Models
Demo --> Models
Import --> Models
SQL --> Models
```

**Diagram sources**
- [models.py:30-58](file://turnos/models.py#L30-L58)
- [forms.py:14-73](file://turnos/forms.py#L14-L73)
- [views.py:814-968](file://turnos/views.py#L814-L968)

**Section sources**
- [models.py:1-825](file://turnos/models.py#L1-L825)
- [urls.py:1-108](file://turnos/urls.py#L1-L108)

## Core Components

### Enfermera Model Definition
The Enfermera model serves as the primary representation of nurse profiles with comprehensive field definitions and validation rules:

```mermaid
classDiagram
class Enfermera {
+Integer id
+ForeignKey Workspace workspace
+CharField nombre
+EmailField email
+CharField telefono
+CharField dni
+BooleanField activa
+DateField fecha_alta
+JSONField preferencias
+TextField notas
+String __str__()
+String get_absolute_url()
}
class Workspace {
+Integer id
+CharField nombre
+TextField descripcion
+ForeignKey User creado_por
+ManyToManyField usuarios
+BooleanField activo
+DateTimeField fecha_creacion
}
Enfermera --> Workspace : "belongs to"
```

**Diagram sources**
- [models.py:30-58](file://turnos/models.py#L30-L58)
- [models.py:12-28](file://turnos/models.py#L12-L28)

### Key Field Specifications
The Enfermera model includes the following essential fields:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `nombre` | CharField | max_length=200 | Full name of the nurse |
| `email` | EmailField | unique=True | Contact email address |
| `telefono` | CharField | max_length=20, blank=True | Phone number |
| `dni` | CharField | max_length=20, unique=True, null=True, blank=True | Spanish national identity number |
| `activa` | BooleanField | default=True | Employment status flag |
| `fecha_alta` | DateField | auto_now_add=True | Registration date |
| `preferencias` | JSONField | default=dict, blank=True | Flexible preference storage |

**Section sources**
- [models.py:30-58](file://turnos/models.py#L30-L58)

## Architecture Overview

### Multi-Tenant Isolation Architecture
The system implements multi-tenancy through Workspace relationships, ensuring data isolation between different organizational units:

```mermaid
graph TB
subgraph "Workspace Isolation"
WS1[Workspace A]
WS2[Workspace B]
WS3[Workspace C]
end
subgraph "Enfermera Collections"
E1[Enfermera A1<br/>WS1]
E2[Enfermera A2<br/>WS1]
E3[Enfermera B1<br/>WS2]
E4[Enfermera B2<br/>WS2]
E5[Enfermera C1<br/>WS3]
end
subgraph "Cross-Workspace Access"
Access[Cross-Workspace Access<br/>Restricted]
end
WS1 --> E1
WS1 --> E2
WS2 --> E3
WS2 --> E4
WS3 --> E5
WS1 -.-> Access
WS2 -.-> Access
WS3 -.-> Access
```

**Diagram sources**
- [models.py:32-38](file://turnos/models.py#L32-L38)
- [models.py:12-28](file://turnos/models.py#L12-L28)

### URL Generation and Navigation
The system generates dynamic URLs for nurse detail pages using Django's reverse URL resolution:

```mermaid
sequenceDiagram
participant User as User Interface
participant View as EnfermeraDetailView
participant Model as Enfermera Model
participant URL as URL Resolver
participant Template as Detail Template
User->>View : GET /turnos/enfermeras/{id}/
View->>Model : get_object()
Model->>Model : get_absolute_url()
Model-->>View : reverse('turnos : enfermera_detalle', kwargs={'pk' : self.pk})
View->>Template : render_with_context
Template-->>User : HTML Response
```

**Diagram sources**
- [models.py:56-57](file://turnos/models.py#L56-L57)
- [urls.py:55](file://turnos/urls.py#L55)
- [views.py:840-875](file://turnos/views.py#L840-L875)

**Section sources**
- [models.py:56-57](file://turnos/models.py#L56-L57)
- [urls.py:52-59](file://turnos/urls.py#L52-L59)

## Detailed Component Analysis

### Registration Process Workflow
The nurse registration process follows a structured workflow from form submission to database persistence:

```mermaid
flowchart TD
Start([User Accesses Registration Form]) --> FormLoad["Form Loads with Fields:<br/>• Nombre<br/>• Email<br/>• Teléfono<br/>• DNI<br/>• Preferencias"]
FormLoad --> UserInput["User Enters Information"]
UserInput --> Validation["Server-Side Validation:<br/>• Email uniqueness<br/>• DNI format<br/>• Required fields"]
Validation --> Valid{"Validation Passes?"}
Valid --> |No| ShowErrors["Display Validation Errors<br/>• Email already exists<br/>• Invalid DNI format<br/>• Missing required fields"]
ShowErrors --> UserInput
Valid --> |Yes| SaveToDB["Save to Database"]
SaveToDB --> Success["Registration Complete<br/>• Success Message<br/>• Redirect to List View"]
Success --> End([End])
```

**Diagram sources**
- [forms.py:14-73](file://turnos/forms.py#L14-L73)
- [views.py:878-907](file://turnos/views.py#L878-L907)

### Validation Rules Implementation
The system implements comprehensive validation rules at both form and model levels:

#### Email Validation
- Unique constraint enforcement
- Django's built-in email validation
- Cross-instance validation during updates

#### DNI Validation (Spanish Format)
- Length validation (9 characters)
- Format validation (8 digits + 1 letter)
- Case normalization and whitespace removal

#### Employment Status Tracking
- Boolean field with default True
- Filterable in admin interface
- Impact on scheduling eligibility

**Section sources**
- [forms.py:52-72](file://turnos/forms.py#L52-L72)
- [models.py:40-46](file://turnos/models.py#L40-L46)

### Preference Management Through JSONField
The `preferencias` field provides flexible storage for nurse preferences:

```mermaid
erDiagram
ENFERMERA {
integer id PK
string nombre
string email UK
string telefono
string dni
boolean activa
date fecha_alta
json preferencias
text notas
}
PREFERENCES {
string tipo
string valor
string detalles
}
ENFERMERA ||--o{ PREFERENCES : "has_preferences"
```

**Diagram sources**
- [models.py:45](file://turnos/models.py#L45)

The JSONField allows for storing various preference types including:
- Preferred shift patterns
- Available days off
- Special accommodations
- Training preferences

**Section sources**
- [models.py:45](file://turnos/models.py#L45)

### Staff Management Query Patterns
The system provides multiple query patterns for staff management scenarios:

#### Basic Filtering and Sorting
```python
# Active nurses only
active_nurses = Enfermera.objects.filter(activa=True)

# Search by name or email
search_results = Enfermera.objects.filter(
    Q(nombre__icontains=search_term) | 
    Q(email__icontains=search_term)
)

# Order by name
ordered_nurses = Enfermera.objects.order_by('nombre')
```

#### Advanced Filtering Scenarios
```python
# Nurses with specific availability
available_nurses = Enfermera.objects.filter(
    activa=True,
    preferencias__icontains='disponible'
)

# Recent hires
recent_hires = Enfermera.objects.filter(
    fecha_alta__gte=timezone.now().date() - timedelta(days=30)
)
```

**Section sources**
- [views.py:823-837](file://turnos/views.py#L823-L837)
- [admin.py:278-288](file://turnos/admin.py#L278-L288)

### URL Generation and Navigation
The system generates SEO-friendly URLs for nurse profiles:

#### URL Pattern Structure
- Pattern: `/turnos/enfermeras/{id}/`
- Named URL: `turnos:enfermera_detalle`
- Dynamic generation using `get_absolute_url()`

#### Template Integration
```html
<a href="{% url 'turnos:enfermera_detalle' enfermera.id %}">
    {{ enfermera.nombre }}
</a>
```

**Section sources**
- [models.py:56-57](file://turnos/models.py#L56-L57)
- [urls.py:55](file://turnos/urls.py#L55)
- [enfermera_list.html:85](file://turnos/templates/turnos/enfermera_list.html#L85)

## Dependency Analysis

### Component Relationships
The Enfermera model integrates with multiple system components:

```mermaid
graph LR
subgraph "Core Models"
Enfermera[Enfermera]
Workspace[Workspace]
AsignacionTurno[AsignacionTurno]
ConfiguracionPlanificacion[ConfiguracionPlanificacion]
end
subgraph "Management Layer"
Forms[EnfermeraForm]
Views[EnfermeraViews]
Admin[EnfermeraAdmin]
end
subgraph "Presentation Layer"
Detail[enfermera_detail.html]
Form[enfermera_form.html]
List[enfermera_list.html]
end
Enfermera --> Workspace
Enfermera --> AsignacionTurno
ConfiguracionPlanificacion --> Enfermera
Forms --> Enfermera
Views --> Enfermera
Admin --> Enfermera
Views --> Detail
Views --> Form
Views --> List
```

**Diagram sources**
- [models.py:30-58](file://turnos/models.py#L30-L58)
- [models.py:568-623](file://turnos/models.py#L568-L623)
- [models.py:332-456](file://turnos/models.py#L332-L456)

### External Dependencies
- Django ORM for database operations
- Django forms framework for validation
- PostgreSQL JSONField for flexible data storage
- Django admin interface for management

**Section sources**
- [models.py:1-8](file://turnos/models.py#L1-L8)

## Performance Considerations

### Database Optimization
- Indexes on frequently queried fields (`nombre`, `email`, `dni`)
- JSONField optimization for preference queries
- Workspace foreign key indexing for multi-tenancy filtering

### Query Optimization Strategies
- Select-related for related model joins
- Prefetch-related for reverse relationships
- Pagination for large datasets
- Filter early in query chains

### Caching Considerations
- Template-level caching for frequently accessed lists
- Database-level query result caching
- Session-based user preference caching

## Troubleshooting Guide

### Common Validation Issues
#### Email Already Exists
**Symptom**: Form validation error when creating/updating nurse
**Cause**: Email violates unique constraint
**Solution**: Use unique email addresses for each nurse profile

#### Invalid DNI Format
**Symptom**: Validation error for DNI field
**Cause**: Incorrect format (length or character type)
**Solution**: Ensure 8 digits followed by 1 letter (e.g., "12345678A")

#### Missing Required Fields
**Symptom**: Form validation errors
**Cause**: Empty required fields (nombre, email)
**Solution**: Ensure all required fields are filled

### Multi-Tenant Isolation Issues
#### Data Contamination Between Workspaces
**Symptom**: Nurses appearing in wrong workspace
**Cause**: Missing workspace filtering
**Solution**: Always filter by current workspace context

#### Cross-Workspace Access Violations
**Symptom**: Permission errors accessing other workspace data
**Cause**: Insufficient workspace permissions
**Solution**: Verify user membership in target workspace

**Section sources**
- [forms.py:52-72](file://turnos/forms.py#L52-L72)
- [admin.py:278-288](file://turnos/admin.py#L278-L288)

## Conclusion
The Enfermera model provides a robust foundation for nurse profile management in the turnos system. Its comprehensive field definitions, multi-tenancy support, and flexible preference storage enable efficient staff management while maintaining data integrity and isolation. The integrated validation, URL generation, and query patterns ensure a smooth user experience for both administrators and end users.

The model's design supports future enhancements including advanced preference management, integration with external systems, and expanded reporting capabilities. The clear separation of concerns between models, forms, views, and templates ensures maintainability and extensibility of the nurse management functionality.
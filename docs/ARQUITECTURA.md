# Documentación de Arquitectura - Planificador de Turnos de Enfermería

## Visión General del Sistema

Este sistema es un **planificador de cuadrantes regulares de enfermería** basado en rotaciones cíclicas, equilibrio horario y corrección de incidencias. NO es un generador genérico de horarios.

### Características Principales

- Generación de planillas mensuales tipo cuadrante real
- Rotaciones regulares con patrón cíclico explícito
- Equilibrio de horas semanales, mensuales y anuales
- Equilibrio de noches, fines de semana y festivos
- Planificación contextual dependiente del histórico anterior
- Motor de reparación y ajuste fino basado en OR-Tools CP-SAT

---

## Arquitectura de Componentes

```
┌─────────────────────────────────────────────────────────┐
│                    Capa de Presentación                  │
│  (Views, Templates, Forms, JavaScript)                   │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                   Capa de Dominio                        │
│  - Modelos Django (Enfermera, Turno, Planilla, etc.)    │
│  - Nuevos Modelos (Contrato, Rotación, Incidencia,      │
│    Balance)                                              │
│  - Normalización de vocabulario                          │
│  - Adaptadores de compatibilidad legacy                  │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                 Motor de Planificación                   │
│  1. Construcción determinista de rotación base           │
│  2. Aplicación de incidencias y bloqueos                 │
│  3. Cálculo de cobertura y desviaciones                  │
│  4. Reparación con CP-SAT sobre celdas conflictivas      │
│  5. Validación y persistencia de balances                │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                   Capa de Persistencia                   │
│  - Django ORM (SQLite/PostgreSQL)                        │
│  - Celery para tareas asíncronas                         │
└─────────────────────────────────────────────────────────┘
```

---

## Pipeline de Planificación

El motor de planificación sigue un pipeline de 5 pasos:

### Paso 1: Construcción Determinista de Rotación Base
- Expande el ciclo de rotación al mes completo
- Aplica desfases por enfermera
- Genera matriz base [enfermera × fecha]

### Paso 2: Aplicación de Incidencias Fijas
- Bloquea celdas por vacaciones, permisos, bajas
- Aplica asignaciones fijas
- Marca celdas como no modificables

### Paso 3: Cálculo de Cobertura y Desviaciones
- Calcula horas por enfermera
- Calcula noches, fines de semana, festivos
- Identifica desviaciones respecto a objetivos
- Detecta conflictos de cobertura

### Paso 4: Reparación con CP-SAT
- **Solo actúa sobre celdas modificables**
- Respeta incidencias fijas
- Minimiza distancia a rotación base
- Optimiza objetivos lexicográficos

### Paso 5: Validación y Persistencia
- Valida restricciones duras
- Calcula métricas finales
- Actualiza balances históricos
- Persiste planilla y asignaciones

---

## Objetivos Lexicográficos del Solver

El solver optimiza en este orden de prioridad estricta:

1. **Restricciones duras:** Cumplir TODAS (descanso 12h, cobertura mínima, máximo consecutivos)
2. **Minimizar desviación de rotación base:** Penalizar celdas que se desvíen del patrón cíclico
3. **Minimizar desviación de horas mensuales:** Cada enfermera cerca de su horas_mes_objetivo
4. **Minimizar desviación de saldo anual:** Considerar horas_acumuladas_previas del balance histórico
5. **Equilibrar noches:** Minimizar varianza de noches entre enfermeras
6. **Equilibrar fines de semana:** Minimizar varianza de fines de semana trabajados
7. **Equilibrar festivos:** Minimizar varianza de festivos trabajados

**Métrica principal:** Horas reales (NO conteo bruto de turnos)

---

## Modelos de Dominio

### Modelos Existentes (Mejorados)

- **Enfermera:** Datos básicos de la enfermera
- **TipoTurno:** Definición de turnos (MANANA, TARDE, NOCHE) con horas
- **ConfiguracionPlanificacion:** Parámetros de planificación
- **Ejecucion:** Registro de cada ejecución del planificador
- **Planilla:** Resultado de una planificación
- **AsignacionTurno:** Celda individual (enfermera + fecha + turno)
  - **Nuevo:** Campo `tipo_celda` para distinguir TURNO, LIBRE, VACACIONES, etc.

### Nuevos Modelos de Dominio

#### ContratoEnfermera
Define el régimen horario objetivo de una enfermera:
- `horas_semana_objetivo`: Horas semanales target
- `horas_anuales_objetivo`: Horas anuales target
- `porcentaje_jornada`: 100% = completa, 50% = media jornada

#### RotacionBase + CeldaRotacion
Define ciclos explícitos de turnos:
- **RotacionBase:** Ciclo completo (ej: 2M-2T-2N-2L = 8 días)
- **CeldaRotacion:** Cada día del ciclo con su turno o libre

#### AsignacionRotacionEnfermera
Asigna una rotación específica a cada enfermera con desfase:
- Permite que diferentes enfermeras estén en distintas posiciones del ciclo

#### Incidencia
Eventos que modifican la planificación normal:
- VACACIONES, PERMISO, BAJA, FORMACION
- LIBRANZA_BLOQUEADA, ASIGNACION_FIJA

#### BalanceHistoricoEnfermera
Acumulados históricos para planificación contextual:
- Horas acumuladas previas
- Noches, fines de semana, festivos acumulados
- Último turno asignado (para restricciones de transición)

---

## Normalización de Vocabulario

Se ha introducido una capa de normalización (`turnos/dominio/normalizacion.py`) que traduce nombres legacy a identificadores canónicos:

### Restricciones Duras Canónicas
- `TURNO_CONSECUTIVOS_MAX` (antes: turnos_consecutivos_max, turnosconsecutivosmax)
- `NOCHES_CONSECUTIVAS_MAX` (antes: turnos_nocturnos_consecutivos_max)
- `DESCANSO_ENTRE_TURNOS` (antes: descanso_12h)
- `COBERTURA_MINIMA`, `COBERTURA_MAXIMA`
- `TURNO_POR_DIA`
- `DIAS_LIBRES_ANUALES`
- `DESCANSO_SEMANAL`

### Restricciones Blandas Canónicas
- `EQUIDAD_TURNOS` (antes: equidad_turnos, equidadturnos)
- `MINIMIZAR_NOCHES` (antes: minimizar_noches, minimizarnoches)
- `EQUIDAD_NOCHES`, `EQUIDAD_FINDES`, `EQUIDAD_FESTIVOS`
- `MINIMIZAR_CAMBIOS`

### Patrones Canónicos
- `SECUENCIA_OBLIGATORIA` (antes: SECUENCIA_TURNOS)
- `ROTACION_CICLICA` (antes: ROTACION_TURNOS, ROTACION)
- `DESCANSO_POST_TURNO`
- `MAX_CONSECUTIVOS`
- `COBERTURA_MINIMA`
- `BLOQUEO_TRANSICION`
- `DISTRIBUCION_EQUITATIVA`

**Nota:** El sistema genera warnings de logging cuando adapta nombres legacy, permitiendo trazabilidad completa.

---

## Decisiones de Diseño

### 1. Solver como Reparador, no como Generador Libre
**Decisión:** El solver CP-SAT NO genera la planilla desde cero. Actúa como motor de reparación sobre una rotación base determinista.

**Justificación:**
- Los cuadrantes de enfermería siguen patrones regulares predecibles
- Generar desde cero produce soluciones inestables e impredecibles
- La reparación mínima preserva la regularidad del cuadrante

### 2. Métrica Principal: Horas Reales
**Decisión:** La equidad se mide por horas reales trabajadas, no por conteo bruto de turnos.

**Justificación:**
- Diferentes turnos tienen diferente duración (ej: noche puede ser 8h, mañana 7h)
- El equilibrio real es en horas, no en número de asignaciones

### 3. Planificación Contextual con Histórico
**Decisión:** Cada planificación considera el histórico acumulado de cada enfermera.

**Justificación:**
- El equilibrio es anual, no mensual
- Una enfermera con muchas noches el mes anterior debe compensar
- Sin histórico, cada mes es aislado y el equilibrio anual es imposible

### 4. Dominio Explícito sobre JSON Libre
**Decisión:** Se introducen modelos tipados para contrato, rotación, incidencia y balance.

**Justificación:**
- JSON libre como semántica interna dificulta validación y mantenimiento
- Los DTOs/objetos explícitos proporcionan type safety y documentación
- JSON puede existir como formato de entrada, pero se normaliza internamente

### 5. Un Único Motor Activo
**Decisión:** Se elimina Pyomo y se consolida en un solo pipeline CP-SAT.

**Justificación:**
- Múltiples implementaciones paralelas generan confusión y bugs
- CP-SAT es más adecuado para este tipo de problema de satisfacción de restricciones
- Mantener una sola ruta activa simplifica mantenimiento y testing

---

## Guía de Migración desde Configuraciones Legacy

### Para Usuarios del Sistema

1. **Configuraciones existentes:** Seguirán funcionando mediante adaptadores de compatibilidad
2. **Nombres de restricciones:** Se normalizan automáticamente (con warning en logs)
3. **Nuevos campos:** Se pueden añadir gradualmente (contratos, rotaciones, incidencias)

### Para Desarrolladores

1. **Nuevas restricciones:** Usar nombres canónicos (ver `turnos/dominio/normalizacion.py`)
2. **Acceso a rotaciones:** Usar `RotacionBase` y `CeldaRotacion` en lugar de patrones JSON abstractos
3. **Balances:** Consultar `BalanceHistoricoEnfermera` para planificación contextual
4. **Incidencias:** Crear objetos `Incidencia` en lugar de codificar en JSON

---

## Estructura del Código

```
turnos/
├── dominio/                    # NUEVO: Capa de dominio
│   ├── __init__.py
│   ├── normalizacion.py        # Normalización de vocabulario
│   ├── modelos.py              # (en models.py principal)
│   ├── adaptadores.py          # (pendiente)
│   └── dtos.py                 # (pendiente)
├── motor/                      # NUEVO: Motor de planificación
│   ├── __init__.py
│   ├── pipeline.py             # Orquestador (pendiente)
│   ├── rotacion_base.py        # Constructor de rotación (pendiente)
│   ├── incidencias.py          # Aplicador de incidencias (pendiente)
│   ├── cobertura.py            # Analizador de cobertura (pendiente)
│   ├── reparador.py            # Reparador CP-SAT (pendiente)
│   ├── validador_motor.py      # Validador final (pendiente)
│   └── objetivos.py            # Objetivos lexicográficos (pendiente)
├── models.py                   # Modelos Django (actualizado)
├── generador_refactorizado.py  # Generador actual (a refactorizar)
├── generador.py                # Wrapper de compatibilidad
├── restricciones_duras.py      # Restricciones hard (actualizado)
├── restricciones_blandas.py    # Restricciones soft (actualizado)
├── validador.py                # Validador (actualizado)
├── variables.py                # Variables CP-SAT
├── resolvedor.py               # Resolvedor CP-SAT
├── views.py                    # Vistas Django (actualizado)
├── forms.py                    # Formularios
├── tasks.py                    # Tareas Celery
└── utils/
    └── exportacion.py          # Exportación Excel/PDF/CSV (actualizado)
```

---

## Próximos Pasos (Pendientes)

1. **Implementar motor completo:** Pipeline, reparador CP-SAT, objetivos lexicográficos
2. **Crear adaptadores de compatibilidad:** Para configuraciones legacy
3. **Implementar capa de DTOs:** Para representación interna de matrices
4. **Tests exhaustivos:** Unitarios, integración, negocio
5. **Migraciones:** Aplicar nuevos modelos a base de datos
6. **Documentación adicional:** API, guía de usuario, ejemplos

---

## Notas Técnicas

### Encoding
- Todos los archivos Python deben estar en UTF-8 sin BOM
- Los fixtures y archivos de datos deben estar en UTF-8

### Base de Datos
- Desarrollo: SQLite (`BASE_DIR / 'db.sqlite3'`)
- Producción: PostgreSQL (configurable vía variables de entorno)

### Celery
- Broker: Redis (`redis://localhost:6379/0`)
- Configuración vía variables de entorno `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND`

### Testing
- Framework: pytest + pytest-django
- Ejecutar: `pytest` desde raíz del proyecto
- Cobertura objetivo: >80% en motor y dominio

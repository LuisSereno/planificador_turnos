# Wiki - Planificador de Turnos de Enfermería

**Versión:** 1.0 | **Actualizado:** junio 2026 | **Estado de refactorización:** COMPLETADO (100%)

---

## Índice

1. [Visión General del Proyecto](#1-visión-general-del-proyecto)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Estructura de Directorios](#3-estructura-de-directorios)
4. [Instalación y Configuración](#4-instalación-y-configuración)
   - [Desarrollo Local](#41-desarrollo-local)
   - [Producción con Docker / Podman](#42-producción-con-docker--podman)
   - [Variables de Entorno](#43-variables-de-entorno)
5. [Modelos de Django](#5-modelos-de-django)
   - [Modelos Principales](#51-modelos-principales)
   - [Modelos de Dominio Avanzado](#52-modelos-de-dominio-avanzado)
6. [Wizard de Configuración](#6-wizard-de-configuración)
   - [Paso 1: Información Básica](#61-paso-1-información-básica)
   - [Paso 2: Demanda por Turno](#62-paso-2-demanda-por-turno)
   - [Paso 3: Restricciones Duras](#63-paso-3-restricciones-duras)
   - [Paso 4: Restricciones Blandas y Parámetros](#64-paso-4-restricciones-blandas-y-parámetros)
7. [Sistema de Restricciones y Patrones](#7-sistema-de-restricciones-y-patrones)
   - [Restricciones Duras](#71-restricciones-duras)
   - [Restricciones Blandas](#72-restricciones-blandas)
   - [Patrones de Turnos](#73-patrones-de-turnos)
   - [Vocabulario Canónico](#74-vocabulario-canónico)
8. [Motor de Planificación y Solver CP-SAT](#8-motor-de-planificación-y-solver-cp-sat)
   - [Pipeline de 5 Fases](#81-pipeline-de-5-fases)
   - [Reparador CP-SAT](#82-reparador-cp-sat)
   - [Objetivos Lexicográficos](#83-objetivos-lexicográficos)
   - [Parámetros de Optimización](#84-parámetros-de-optimización)
9. [Manual de Usuario](#9-manual-de-usuario)
   - [Flujo Básico](#91-flujo-básico)
   - [Gestión de Enfermeras](#92-gestión-de-enfermeras)
   - [Gestión de Tipos de Turno](#93-gestión-de-tipos-de-turno)
   - [Ejecutar una Planificación](#94-ejecutar-una-planificación)
   - [Exportar Resultados](#95-exportar-resultados)
10. [Capa de Dominio](#10-capa-de-dominio)
11. [Tareas Asíncronas con Celery](#11-tareas-asíncronas-con-celery)
12. [Comandos de Gestión](#12-comandos-de-gestión)
13. [Troubleshooting y Logs](#13-troubleshooting-y-logs)
14. [Testing](#14-testing)
15. [Decisiones de Diseño](#15-decisiones-de-diseño)
16. [Historial de Refactorización](#16-historial-de-refactorización)

---

## 1. Visión General del Proyecto

El **Planificador de Turnos de Enfermería** es un sistema web Django para la generación automática de cuadrantes de turno. No es un generador genérico de horarios: está diseñado específicamente para la planificación de servicios de enfermería con rotaciones cíclicas regulares.

### Características Principales

- Generación de planillas mensuales tipo cuadrante real
- Rotaciones regulares con patrón cíclico explícito
- Equilibrio de horas semanales, mensuales y anuales
- Equilibrio de noches, fines de semana y festivos
- Planificación contextual dependiente del histórico anterior
- Motor de reparación y ajuste fino basado en OR-Tools CP-SAT
- Procesamiento asíncrono con Celery + Redis
- Exportación a Excel, PDF, CSV e iCalendar
- Interfaz web con wizard de configuración guiado
- Sistema multi-workspace para aislar datos entre usuarios

### Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| Backend web | Django 5.1 |
| Solver de optimización | OR-Tools CP-SAT (Google) 9.14 |
| Tareas asíncronas | Celery 5.5 + Redis 7 |
| Base de datos (desarrollo) | SQLite |
| Base de datos (producción) | PostgreSQL 16 |
| Frontend | Bootstrap 5 + Chart.js |
| Servidor web (contenedor) | Gunicorn + Nginx |
| Contenedores | Docker / Podman (rootless) |
| Exportación PDF | WeasyPrint |
| Exportación Excel | openpyxl |

---

## 2. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    Capa de Presentación                  │
│  (Views, Templates, Forms, JavaScript)                   │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                   Capa de Dominio                        │
│  - Modelos Django (Enfermera, Turno, Planilla, etc.)    │
│  - Modelos Avanzados (Contrato, Rotación, Incidencia,   │
│    Balance)                                              │
│  - DTOs tipados (dtos.py)                                │
│  - Normalización de vocabulario (normalizacion.py)       │
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
│  - Django ORM (SQLite / PostgreSQL)                      │
│  - Celery para tareas asíncronas                         │
│  - Redis como broker y caché                             │
└─────────────────────────────────────────────────────────┘
```

### Principio Clave: Solver como Reparador

El solver **no genera** la planilla desde cero. Actúa como **motor de reparación** sobre una rotación base determinista ya construida. Esto garantiza que los cuadrantes respeten patrones regulares predecibles y que las soluciones sean estables y reproducibles.

---

## 3. Estructura de Directorios

```
planificador_turnos/
├── docker/                        # Configuración Docker
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── default.conf
│   └── postgres/
│       └── init.sql
├── docs/                          # Documentación
│   ├── API.md
│   ├── ARQUITECTURA.md
│   ├── FINAL_SUMMARY.md
│   ├── REFACTOR.md
│   ├── REFACTOR_SUMMARY.md
│   ├── REFACTORIZACION_COMPLETADA.md
│   └── WIKI.md                    ← Este archivo
├── locale/                        # Traducciones i18n
├── logs/                          # Logs de aplicación
├── proyecto_turnos/               # Configuración Django
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── static/                        # Archivos estáticos fuente
├── staticfiles/                   # Archivos estáticos compilados
├── turnos/                        # Aplicación principal
│   ├── dominio/                   # Capa de dominio
│   │   ├── adaptadores.py         # Adaptadores de compatibilidad legacy
│   │   ├── dtos.py                # DTOs tipados (9 clases)
│   │   ├── normalizacion.py       # Normalización de nombres legacy → canónico
│   │   └── vocabulario.py         # Vocabulario canónico (restricciones, patrones)
│   ├── motor/                     # Motor de planificación
│   │   ├── ajuste_horas.py        # Ajuste de horas
│   │   ├── cobertura.py           # Analizador de cobertura (188 líneas)
│   │   ├── incidencias.py         # Aplicador de incidencias (122 líneas)
│   │   ├── overlay_incidencias.py # Overlay de incidencias sobre matriz
│   │   ├── pipeline.py            # Orquestador del pipeline (164 líneas)
│   │   ├── reparador.py           # Reparador CP-SAT (279 líneas)
│   │   ├── rotacion_base.py       # Constructor de rotación determinista (101 líneas)
│   │   └── validador_motor.py     # Validador final del motor
│   ├── management/
│   │   └── commands/              # Comandos manage.py personalizados
│   │       ├── cargar_restricciones_sacyl.py
│   │       ├── crear_tipos_turno.py
│   │       ├── estadisticas_sistema.py
│   │       ├── exportar_enfermeras.py
│   │       ├── generar_datos_prueba.py
│   │       ├── importar_enfermeras.py
│   │       ├── limpiar_base_datos.py
│   │       ├── load_all_fixtures.py
│   │       ├── run_planificacion.py
│   │       └── simular_planificacion.py
│   ├── migrations/                # Migraciones de base de datos (0001–0014)
│   ├── templates/                 # Plantillas HTML
│   │   ├── accounts/              # Autenticación
│   │   ├── emails/                # Plantillas de correo
│   │   └── turnos/
│   │       ├── config/            # Configuraciones (lista, detalle, wizard)
│   │       ├── partials/          # Fragmentos reutilizables
│   │       ├── pdf/               # Plantilla PDF de planilla
│   │       └── wizard/            # Wizard de 4 pasos
│   │           ├── paso1_basico.html
│   │           ├── paso2_demanda.html
│   │           ├── paso3_duras.html
│   │           └── paso4_blandas.html
│   ├── tests/                     # Tests automatizados
│   │   ├── test_dominio/
│   │   │   ├── test_dtos.py       # 17 tests de DTOs
│   │   │   └── test_normalizacion.py  # 16 tests de normalización
│   │   ├── test_motor/
│   │   │   ├── test_integracion_final.py
│   │   │   ├── test_pipeline.py   # Tests del pipeline completo
│   │   │   └── test_reparador.py  # Tests del reparador CP-SAT
│   │   ├── test_generador.py
│   │   └── test_models.py
│   ├── utils/
│   │   ├── email.py               # Utilidades de email
│   │   ├── exportacion.py         # Exportación Excel/PDF/CSV
│   │   ├── exportador_profesional.py
│   │   └── tiempo.py              # Utilidades de tiempo
│   ├── admin.py                   # Django Admin
│   ├── apps.py
│   ├── decorators.py              # Decoradores de autenticación/workspace
│   ├── forms.py                   # Formularios Django (incluye wizard)
│   ├── generador.py               # Wrapper de compatibilidad
│   ├── generador_refactorizado.py # Generador actual
│   ├── generador_patrones.py      # Generador de patrones
│   ├── logger_config.py           # Configuración de logging
│   ├── mixins.py                  # Mixins de vistas
│   ├── models.py                  # Modelos Django
│   ├── patrones.py                # Evaluador de patrones
│   ├── resolvedor.py              # Wrapper del solver CP-SAT
│   ├── restricciones_blandas.py   # Restricciones soft
│   ├── restricciones_duras.py     # Restricciones hard
│   ├── tasks.py                   # Tareas Celery
│   ├── templatetags/
│   │   └── turnos_extras.py       # Filtros de plantilla personalizados
│   ├── urls.py                    # URLs de la app
│   ├── urls_auth.py               # URLs de autenticación
│   ├── validador.py               # Validador de planificación
│   ├── variables.py               # Variables CP-SAT
│   └── views.py                   # Vistas Django
├── docker-compose.yml             # Orquestación de contenedores
├── docker-compose.dev.yml         # Configuración de desarrollo
├── docker-entrypoint.sh           # Script de entrada del contenedor
├── Dockerfile                     # Imagen Docker (Python 3.11-slim)
├── init_web.sh                    # Script de inicialización web
├── manage.py                      # CLI de Django
├── requirements.txt               # Dependencias Python
├── start.sh                       # Script de arranque (dev + prod)
├── stop.sh                        # Script de parada
├── wait-for-it.sh                 # Espera a servicios
└── pytest.ini                     # Configuración de pytest
```

---

## 4. Instalación y Configuración

### 4.1 Desarrollo Local

**Prerequisitos:** Python 3.11+, Git

```bash
# 1. Clonar el repositorio
git clone https://github.com/LuisSereno/planificador_turnos.git
cd planificador_turnos

# 2. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno (opcional para desarrollo)
cp .env.example .env
# Editar .env si es necesario

# 5. Aplicar migraciones
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Cargar datos de ejemplo (opcional)
python manage.py generar_datos_prueba
python manage.py crear_tipos_turno

# 8. Iniciar servidor de desarrollo
python manage.py runserver
```

**Acceso:** http://localhost:8000 | Admin: http://localhost:8000/admin

#### Modo Desarrollo con Celery (script automático)

El script `start.sh --dev` automatiza todos los pasos anteriores, incluyendo la gestión de Redis y Celery:

```bash
./start.sh --dev
# O en un puerto personalizado:
./start.sh --dev --port 9000
```

El script:
- Activa el entorno virtual `.venv`
- Aplica migraciones automáticamente
- Crea el superusuario `admin` / `Admin123!@#` si no existe
- Inicia Redis en un contenedor Podman (puerto 6380) como broker
- Inicia Celery worker y Celery beat en background
- Arranca `manage.py runserver`

Para detener todos los servicios:

```bash
./stop.sh --dev
```

### 4.2 Producción con Docker / Podman

**Prerequisitos:** Docker o Podman + podman-compose/docker-compose

El stack de producción levanta 6 servicios coordinados:

| Servicio | Imagen | Puerto | Función |
|----------|--------|--------|---------|
| `db` | postgres:16-alpine | 5432 | Base de datos PostgreSQL |
| `redis` | redis:7-alpine | 6379 | Broker Celery y caché |
| `web` | (build local) | 8000 | Aplicación Django + Gunicorn |
| `celery_worker` | (build local) | — | Procesamiento asíncrono |
| `celery_beat` | (build local) | — | Tareas programadas |
| `nginx` | nginx:1.25-alpine | 8080/8443 | Proxy inverso y archivos estáticos |

#### Arranque con script automático

```bash
# Modo producción (Podman por defecto)
./start.sh

# Con puerto personalizado
./start.sh --port 9090
```

#### Arranque manual con docker-compose

```bash
# Construir y levantar todos los servicios
docker-compose up -d --build

# Ver estado de los servicios
docker-compose ps

# Ver logs en tiempo real
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f web

# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes (¡borra la BD!)
docker-compose down -v
```

#### Comandos útiles en contenedor

```bash
# Ejecutar shell Django
docker-compose exec web python manage.py shell

# Aplicar migraciones manualmente
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Ejecutar tests
docker-compose exec web pytest turnos/tests/ -v

# Colectar archivos estáticos
docker-compose exec web python manage.py collectstatic --noinput
```

### 4.3 Variables de Entorno

El archivo `.env` en la raíz del proyecto controla la configuración del sistema:

```bash
# Django
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,tu-dominio.com
DJANGO_SETTINGS_MODULE=proyecto_turnos.settings

# Base de datos (PostgreSQL en producción)
POSTGRES_DB=planificador_turnos
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeme123

# Redis
REDIS_PASSWORD=redispass123

# Celery (se configuran automáticamente en docker-compose)
CELERY_BROKER_URL=redis://:redispass123@redis:6379/0
CELERY_RESULT_BACKEND=redis://:redispass123@redis:6379/0

# URL de base de datos (alternativa a variables individuales)
DATABASE_URL=postgresql://postgres:changeme123@db:5432/planificador_turnos
REDIS_URL=redis://:redispass123@redis:6379/0
```

**Notas de seguridad:**
- `SECRET_KEY` debe ser una cadena aleatoria larga (≥50 caracteres) en producción
- Cambiar todas las contraseñas por defecto antes de desplegar
- `DEBUG=False` obligatorio en producción
- Nunca subir `.env` al repositorio (está en `.gitignore`)

---

## 5. Modelos de Django

Todos los modelos se encuentran en [`turnos/models.py`](../turnos/models.py).

### 5.1 Modelos Principales

#### `Workspace`

Aísla los datos entre diferentes organizaciones o usuarios.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | CharField(200) | Nombre del workspace |
| `descripcion` | TextField | Descripción opcional |
| `creado_por` | FK → User | Usuario propietario |
| `usuarios` | M2M → User | Usuarios con acceso |
| `activo` | BooleanField | Estado del workspace |
| `fecha_creacion` | DateTimeField | Auto |

---

#### `Enfermera`

Representa a una profesional de enfermería.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `workspace` | FK → Workspace | Workspace propietario |
| `nombre` | CharField(200) | Nombre completo |
| `email` | EmailField | Email único |
| `telefono` | CharField(20) | Teléfono (opcional) |
| `dni` | CharField(20) | DNI único (opcional) |
| `activa` | BooleanField | Si está activa |
| `fecha_alta` | DateField | Auto |
| `preferencias` | JSONField | Preferencias de turno |
| `notas` | TextField | Notas adicionales |

---

#### `TipoTurno`

Define los tipos de turno (Mañana, Tarde, Noche, Libre, Descanso, etc.). Completamente dinámico y configurable por workspace.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `workspace` | FK → Workspace | Workspace propietario |
| `nombre` | CharField(100) | Nombre del turno (ej: "Mañana") |
| `codigo_corto` | CharField(5) | Acrónimo para planillas (ej: "M") |
| `hora_inicio` | TimeField | Hora de inicio (null si Libre/Descanso) |
| `hora_fin` | TimeField | Hora de fin (null si Libre/Descanso) |
| `descripcion` | TextField | Descripción opcional |
| `activo` | BooleanField | Estado |
| `es_incidencia` | BooleanField | Si es incidencia (no se asigna auto) |
| `es_sustituto_libre` | BooleanField | Si actúa como "Libre" (0 horas) |

**Propiedades calculadas:**
- `duracion_horas`: duración en horas, calculando cruce de medianoche
- `es_nocturno`: `True` si `hora_fin < hora_inicio`
- `num_configuraciones`: número de configuraciones que usan este turno

**Validaciones:**
- Turnos sustitutos de Libre no pueden tener horario ni ser incidencias
- Turnos regulares (no incidencia, no libre) deben tener `hora_inicio` y `hora_fin`
- `codigo_corto` es único por workspace

---

#### `PatronTurnos`

Patrón genérico configurable para reglas de secuencias y restricciones. Usa `TipoPatron` (TextChoices):

| Tipo | Código | Descripción |
|------|--------|-------------|
| `SECUENCIA_OBLIGATORIA` | `SEQ` | Secuencia fija A→B→C |
| `DESCANSO_POST_TURNO` | `REST` | Días libres tras N noches consecutivas |
| `MAX_CONSECUTIVOS` | `MAX_CONS` | Máximo de días seguidos del mismo tipo |
| `ROTACION_CICLICA` | `ROT` | Ciclo M→T→N→M→T→N |
| `COBERTURA_MINIMA` | `COV_MIN` | Mínimo de enfermeras por turno |
| `BLOQUEO_TRANSICION` | `BLOCK` | Prohíbe transición Noche→Mañana |
| `DISTRIBUCION_EQUITATIVA` | `EQUI` | Igualdad de cargas entre enfermeras |

Ejemplo de `configuracion` JSON para cada tipo:

```json
// DESCANSO_POST_TURNO
{"turno_tipo": "NOCHE", "cantidad_consecutiva": 2, "dias_descanso_requeridos": 3}

// MAX_CONSECUTIVOS
{"turno_tipo": "CUALQUIERA", "cantidad_maxima": 5}

// SECUENCIA_OBLIGATORIA
{"secuencia": ["MAÑANA", "TARDE", "NOCHE"], "ciclica": true}

// BLOQUEO_TRANSICION
{"turno_origen": "NOCHE", "turno_destino": "MAÑANA", "dias_minimos_entre": 1}

// COBERTURA_MINIMA
{"turno_tipo": "NOCHE", "enfermeras_minimas": 2, "aplicar_dias": [5, 6, 0]}
```

---

#### `ConfiguracionPlanificacion`

Modelo central que agrupa todos los parámetros de una planificación.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `workspace` | FK → Workspace | Workspace propietario |
| `nombre` | CharField(200) | Nombre de la configuración |
| `descripcion` | TextField | Descripción opcional |
| `activa` | BooleanField | Si está activa |
| `num_dias` | IntegerField | Número de días (7–365) |
| `fecha_inicio` | DateField | Fecha de inicio |
| `enfermeras` | M2M → Enfermera | Enfermeras incluidas |
| `turnos` | M2M → TipoTurno | Tipos de turno disponibles |
| `turnos_por_dia` | M2M → TipoTurno | Turnos que aplican la regla "uno por día" |
| `demanda_por_turno` | JSONField | Demanda mínima/óptima/máxima por turno |
| `restricciones_duras` | JSONField | Lista de restricciones obligatorias |
| `restricciones_blandas` | JSONField | Lista de restricciones preferentes |
| `patrones_turnos_json` | JSONField | Patrones dinámicos (fuente activa principal) |
| `patrones_turnos` | M2M → PatronTurnos | Patrones predefinidos (legacy) |
| `num_trabajadores` | IntegerField | Procesos paralelos del solver (1–8) |
| `tiempo_maximo_segundos` | IntegerField | Timeout del solver (10–600 seg) |
| `seed` | IntegerField | Semilla aleatoria (opcional) |
| `creado_por` | FK → User | Usuario creador |
| `fecha_creacion` | DateTimeField | Auto |
| `fecha_modificacion` | DateTimeField | Auto |

**Propiedades calculadas:**
- `fecha_fin`: `fecha_inicio + timedelta(days=num_dias - 1)`

**Método clave:**
- `get_patrones_combinados()`: unifica `patrones_turnos_json` (activo) con `patrones_turnos` ManyToMany (legacy)

---

#### `Ejecucion`

Registro de cada ejecución del planificador.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `workspace` | FK → Workspace | — |
| `configuracion` | FK → ConfiguracionPlanificacion | Configuración usada |
| `estado` | CharField | `PENDIENTE`, `PROCESANDO`, `COMPLETADA`, `INVIABLE`, `ERROR` |
| `fecha_inicio` | DateTimeField | Auto |
| `fecha_fin` | DateTimeField | Cuando terminó (null si en curso) |
| `es_optima` | BooleanField | Si el solver encontró óptimo global |
| `penalizacion_total` | FloatField | Puntuación de penalización |
| `resultado` | JSONField | Datos del resultado |
| `mensajes` | JSONField | Mensajes informativos/errores |

**Estado `INVIABLE`:** el solver no pudo satisfacer las restricciones duras. Revisar la configuración.

---

#### `Planilla`

Resultado final de una planificación con todas las asignaciones.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `workspace` | FK → Workspace | — |
| `nombre` | CharField(200) | Nombre de la planilla |
| `descripcion` | TextField | — |
| `ejecucion` | OneToOne → Ejecucion | Ejecución que la generó |
| `fecha_inicio` | DateField | — |
| `fecha_fin` | DateField | — |
| `num_dias` | IntegerField | — |

---

#### `AsignacionTurno`

Celda individual de la planilla: una enfermera en una fecha con un turno.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `planilla` | FK → Planilla | — |
| `enfermera` | FK → Enfermera | — |
| `fecha` | DateField | — |
| `turno` | FK → TipoTurno | Puede ser null si es libre |
| `es_dia_libre` | BooleanField | — |
| `observaciones` | TextField | — |
| `tipo_celda` | CharField | Ver tabla a continuación |

**Tipos de celda (`tipo_celda`):**

| Valor | Descripción |
|-------|-------------|
| `TURNO` | Turno normal de trabajo |
| `LIBRE` | Día libre (L) |
| `VACACIONES` | Vacaciones (V) |
| `PERMISO` | Permiso (P) |
| `BAJA` | Baja médica (B) |
| `FORMACION` | Formación (F) |
| `ASIGNACION_FIJA` | Asignación fija manual |

---

### 5.2 Modelos de Dominio Avanzado

Estos modelos fueron añadidos en la refactorización para soportar planificación contextual avanzada.

#### `ContratoEnfermera`

Define el régimen horario objetivo de una enfermera.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `enfermera` | OneToOne → Enfermera | — |
| `horas_semana_objetivo` | DecimalField | Horas semanales target (default: 40h) |
| `horas_anuales_objetivo` | DecimalField | Horas anuales target (default: 1800h) |
| `porcentaje_jornada` | DecimalField | 100 = completa, 50 = media jornada |
| `fecha_inicio_vigencia` | DateField | Inicio del contrato |
| `fecha_fin_vigencia` | DateField | Fin del contrato (null = indefinido) |

---

#### `RotacionBase` + `CeldaRotacion`

Define ciclos explícitos de turnos.

**`RotacionBase`:** representa el ciclo completo (ej: MM-TT-NN-LL = 8 días)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | CharField(200) | Ej: "Ciclo MMTTNDNDL" |
| `descripcion` | TextField | — |
| `ciclo_dias` | IntegerField | Duración total del ciclo |
| `workspace` | FK → Workspace | — |

**`CeldaRotacion`:** cada día del ciclo

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `rotacion` | FK → RotacionBase | — |
| `orden` | IntegerField | Posición en el ciclo (0-based) |
| `turno` | FK → TipoTurno | Turno del día (null = libre) |
| `es_libre` | BooleanField | Si es día libre |

---

#### `AsignacionRotacionEnfermera`

Asigna una rotación específica a cada enfermera con desfase de ciclo.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `enfermera` | FK → Enfermera | — |
| `rotacion` | FK → RotacionBase | — |
| `desfase` | IntegerField | Días de desplazamiento en el ciclo |
| `fecha_inicio` | DateField | — |
| `fecha_fin` | DateField | null = vigente |

El `desfase` permite que diferentes enfermeras estén en distintas posiciones del mismo ciclo, generando variedad en el cuadrante.

---

#### `Incidencia`

Eventos que modifican la planificación normal (bloquean o fijan celdas).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `enfermera` | FK → Enfermera | — |
| `tipo` | CharField | Ver tabla |
| `fecha_inicio` | DateField | — |
| `fecha_fin` | DateField | — |
| `turno_fijo` | FK → TipoTurno | Para `ASIGNACION_FIJA` |
| `observaciones` | TextField | — |

| Tipo | Descripción |
|------|-------------|
| `VACACIONES` | Días de vacaciones |
| `PERMISO` | Permiso puntual |
| `BAJA` | Baja médica |
| `FORMACION` | Período de formación |
| `LIBRANZA_BLOQUEADA` | Libranza que no se puede mover |
| `ASIGNACION_FIJA` | Turno concreto obligatorio |

---

#### `BalanceHistoricoEnfermera`

Acumulados históricos para planificación contextual mensual.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `enfermera` | FK → Enfermera | — |
| `periodo_referencia` | CharField(20) | Formato `YYYY-MM` (ej: "2026-04") |
| `horas_acumuladas_previas` | DecimalField | Horas trabajadas hasta este período |
| `noches_acumuladas` | IntegerField | Noches trabajadas acumuladas |
| `fines_semana_acumulados` | IntegerField | Fines de semana trabajados |
| `festivos_acumulados` | IntegerField | Festivos trabajados |
| `ultimo_turno_fecha` | DateField | Fecha del último turno asignado |
| `ultimo_turno_tipo` | FK → TipoTurno | Tipo del último turno |
| `fecha_actualizacion` | DateTimeField | Auto |

**Restricción:** `unique_together = ['enfermera', 'periodo_referencia']`

---

## 6. Wizard de Configuración

El wizard guiado permite crear una `ConfiguracionPlanificacion` en 4 pasos. Está implementado con `django-formtools` (`SessionWizardView`).

**URL:** `/turnos/configuraciones/nueva/wizard/`

### 6.1 Paso 1: Información Básica

Recoge los parámetros fundamentales de la planificación.

**Campos:**
- **Nombre** (obligatorio): identificador descriptivo, ej: "Planificación Octubre 2026"
- **Descripción** (opcional): notas adicionales
- **Número de días** (obligatorio): entre 7 y 365, típicamente 28–31
- **Fecha de inicio** (obligatorio): primer día de la planificación
- **Enfermeras** (obligatorio): checkboxes con todas las enfermeras activas del workspace
- **Tipos de turno** (obligatorio): checkboxes con los tipos de turno disponibles

> Selecciona al menos 2 enfermeras y los turnos de trabajo reales (Mañana, Tarde, Noche). Los turnos tipo "Libre" o "Descanso" se gestionan automáticamente.

### 6.2 Paso 2: Demanda por Turno

Define cuántas enfermeras se necesitan por turno cada día.

**Formato JSON:**
```json
{
  "MANANA": {"min": 2, "optimo": 3, "max": 5},
  "TARDE":  {"min": 2, "optimo": 3, "max": 5},
  "NOCHE":  {"min": 1, "optimo": 2, "max": 3}
}
```

- `min`: número mínimo obligatorio (restricción dura si se combina con `cobertura_minima`)
- `optimo`: número ideal que el solver intentará alcanzar
- `max`: número máximo permitido

> Las claves deben coincidir exactamente con el campo `nombre` de los `TipoTurno` seleccionados en el paso 1 (en mayúsculas, sin tildes).

### 6.3 Paso 3: Restricciones Duras

Las restricciones duras son **obligatorias**: si el solver no puede cumplirlas, la ejecución terminará en estado `INVIABLE`.

**Formato JSON (lista de objetos):**
```json
[
  {"nombre": "un_turno_por_dia",         "parametros": {"max_turnos": 2}},
  {"nombre": "cobertura_minima",         "parametros": {"min": 2}},
  {"nombre": "descanso_minimo",          "parametros": {"horas": 11}},
  {"nombre": "descanso_post_noche",      "parametros": {"min_horas": 12}},
  {"nombre": "max_noches_consecutivas",  "parametros": {"max": 3}}
]
```

**Restricciones disponibles:**

| Nombre | Descripción | Parámetros clave |
|--------|-------------|-----------------|
| `un_turno_por_dia` | Una enfermera, un turno al día | `max_turnos` |
| `cobertura_minima` | Mínimo de enfermeras por turno | `min` |
| `cobertura_maxima` | Máximo de enfermeras por turno | `max` |
| `descanso_minimo` | Horas mínimas entre turnos | `horas` |
| `descanso_post_noche` / `RD_POST_NOCHE` | Descanso tras turno nocturno | `min_horas`, `turnos` |
| `max_noches_consecutivas` / `RD_MAX_NOCHES_CONSECUTIVAS` | Máximo de noches seguidas | `max` / `max_noches`, `turnos` |
| `turnos_consecutivos_max` | Máximo de días trabajados consecutivos | `max` |
| `turnos_semanales_max` | Máximo de turnos por semana | `max` |

> Si se deja vacío, se usan los valores predeterminados mostrados en el ejemplo del formulario.

### 6.4 Paso 4: Restricciones Blandas y Parámetros

Las restricciones blandas son **preferencias**: el solver las intentará cumplir, pero no son obligatorias.

**Restricciones blandas (JSON):**
```json
[
  {"nombre": "equidad_turnos",       "peso": 10.0},
  {"nombre": "preferencias_turno",   "peso": 5.0},
  {"nombre": "minimizar_noches",     "peso": 3.0}
]
```

El campo `peso` define la importancia relativa: mayor peso = mayor prioridad en la optimización.

**Patrones de turnos:** selección de `PatronTurnos` predefinidos en la base de datos.

**Parámetros del solver:**

| Parámetro | Rango | Recomendado | Descripción |
|-----------|-------|-------------|-------------|
| `num_trabajadores` | 1–8 | 4 | Procesos paralelos del solver |
| `tiempo_maximo_segundos` | 10–600 | 60–300 | Timeout máximo de búsqueda |
| `seed` | cualquier int | null | Semilla para reproducir resultados |

> Aumentar `num_trabajadores` acelera la búsqueda pero consume más CPU. Para planillas grandes (>30 días, >10 enfermeras), usar 300 seg o más.

---

## 7. Sistema de Restricciones y Patrones

### 7.1 Restricciones Duras

Implementadas en [`turnos/restricciones_duras.py`](../turnos/restricciones_duras.py).

Restricciones canónicas del sistema:

| Nombre canónico | Descripción |
|-----------------|-------------|
| `TURNO_CONSECUTIVOS_MAX` | Máximo de turnos trabajados consecutivos |
| `NOCHES_CONSECUTIVAS_MAX` | Máximo de noches consecutivas |
| `DESCANSO_ENTRE_TURNOS` | Mínimo de horas de descanso entre turnos |
| `COBERTURA_MINIMA` | Cobertura mínima garantizada por turno |
| `COBERTURA_MAXIMA` | Cobertura máxima por turno |
| `TURNO_POR_DIA` | Solo un turno por enfermera por día |
| `DIAS_LIBRES_ANUALES` | Mínimo de días libres anuales |
| `DESCANSO_SEMANAL` | Descanso semanal obligatorio |

### 7.2 Restricciones Blandas

Implementadas en [`turnos/restricciones_blandas.py`](../turnos/restricciones_blandas.py).

| Nombre canónico | Descripción |
|-----------------|-------------|
| `EQUIDAD_TURNOS` | Equilibrio de turnos entre enfermeras |
| `MINIMIZAR_NOCHES` | Minimizar noches asignadas |
| `EQUIDAD_NOCHES` | Equilibrio de noches |
| `EQUIDAD_FINDES` | Equilibrio de fines de semana |
| `EQUIDAD_FESTIVOS` | Equilibrio de festivos |
| `MINIMIZAR_CAMBIOS` | Minimizar cambios respecto a rotación base |
| `EQUIDAD_TURNOS` (alias) | Compatible con nombres legacy |

### 7.3 Patrones de Turnos

Los patrones se almacenan en `ConfiguracionPlanificacion.patrones_turnos_json` (fuente activa) o en el modelo `PatronTurnos` (legacy).

**Tipos de patrón disponibles (`TipoPatron`):**

```
SEQ      → Secuencia Obligatoria:    A → B → C (ciclo fijo)
REST     → Descanso Post-Turno:     2 noches → 3 libres
MAX_CONS → Máximo Consecutivos:     máx. 5 días seguidos
ROT      → Rotación Cíclica:        M→T→N→M→T→N
COV_MIN  → Cobertura Mínima:        mín. 2 enfermeras/turno
BLOCK    → Transición Bloqueada:    Noche → NO Mañana
EQUI     → Distribución Equitativa: igualdad de cargas
```

### 7.4 Vocabulario Canónico

El módulo [`turnos/dominio/normalizacion.py`](../turnos/dominio/normalizacion.py) normaliza automáticamente nombres legacy a canónicos, emitiendo warnings en los logs para trazabilidad.

**Ejemplos de normalización:**
```python
"turnosconsecutivosmax"  →  "TURNO_CONSECUTIVOS_MAX"
"equidadturnos"          →  "EQUIDAD_TURNOS"
"minimizarnoches"        →  "MINIMIZAR_NOCHES"
"SECUENCIA_TURNOS"       →  "SECUENCIA_OBLIGATORIA"
"ROTACION_TURNOS"        →  "ROTACION_CICLICA"
```

El vocabulario canónico completo está en [`turnos/dominio/vocabulario.py`](../turnos/dominio/vocabulario.py).

---

## 8. Motor de Planificación y Solver CP-SAT

### 8.1 Pipeline de 5 Fases

El motor ([`turnos/motor/pipeline.py`](../turnos/motor/pipeline.py)) ejecuta estas fases en orden:

```
Fase 1: Rotación Base Determinista
  └─ Expande el ciclo de rotación al mes completo
  └─ Aplica desfases individuales de cada enfermera
  └─ Genera la matriz base [enfermera × fecha]
      ↓
Fase 2: Aplicación de Incidencias Fijas
  └─ Bloquea celdas: vacaciones, permisos, bajas
  └─ Aplica asignaciones fijas inmutables
  └─ Marca celdas como no modificables por el solver
      ↓
Fase 3: Análisis de Cobertura y Desviaciones
  └─ Calcula horas reales por enfermera
  └─ Calcula noches, fines de semana, festivos
  └─ Identifica desviaciones respecto a objetivos
  └─ Detecta conflictos de cobertura
      ↓
Fase 4: Reparación con CP-SAT  ← Motor principal
  └─ Solo actúa sobre celdas MODIFICABLES
  └─ Respeta incidencias fijas de fase 2
  └─ Minimiza distancia a rotación base
  └─ Optimiza objetivos lexicográficos
  └─ Timeout: 30 segundos por defecto
      ↓
Fase 5: Validación y Persistencia
  └─ Valida restricciones duras finales
  └─ Calcula métricas finales
  └─ Actualiza BalanceHistoricoEnfermera
  └─ Persiste Planilla y AsignacionTurno
```

### 8.2 Reparador CP-SAT

Implementado en [`turnos/motor/reparador.py`](../turnos/motor/reparador.py) (279 líneas).

Características:
- Variables booleanas solo para celdas modificables (no incidencias)
- Restricciones duras modeladas como constraintas CP-SAT
- Objetivos lexicográficos priorizados
- Timeout configurable (30 seg. por defecto en el motor interno)
- Extensible para nuevos objetivos

### 8.3 Objetivos Lexicográficos

El solver optimiza en este orden de **prioridad estricta**:

| Prioridad | Objetivo |
|-----------|---------|
| 1 (máxima) | Cumplir TODAS las restricciones duras |
| 2 | Minimizar desviación de la rotación base (preservar el patrón cíclico) |
| 3 | Minimizar desviación de horas mensuales por enfermera |
| 4 | Minimizar desviación del saldo anual acumulado |
| 5 | Equilibrar noches entre enfermeras |
| 6 | Equilibrar fines de semana trabajados |
| 7 | Equilibrar festivos trabajados |

**Métrica principal:** horas reales trabajadas (no conteo de turnos).

### 8.4 Parámetros de Optimización

Configurables en `ConfiguracionPlanificacion`:

| Parámetro | Modelo | Descripción |
|-----------|--------|-------------|
| `num_trabajadores` | `num_trabajadores` | Workers paralelos del solver (1–8) |
| `tiempo_maximo_segundos` | `tiempo_maximo_segundos` | Timeout global (10–600 seg) |
| `seed` | `seed` | Semilla para reproducibilidad |

Recomendaciones según complejidad:

| Escenario | Trabajadores | Tiempo |
|-----------|-------------|--------|
| Planilla pequeña (≤7 días, ≤6 enfermeras) | 2 | 30 seg |
| Planilla media (28–31 días, 8–12 enfermeras) | 4 | 60–120 seg |
| Planilla grande (>31 días, >12 enfermeras) | 8 | 300–600 seg |

---

## 9. Manual de Usuario

### 9.1 Flujo Básico

```
1. Crear tipos de turno  →  2. Crear enfermeras  →  3. Crear configuración
         ↓                                                    ↓
4. Ejecutar planificación  ←────────────────────────────────'
         ↓
5. Revisar resultado  →  6. Exportar (Excel/PDF/CSV/iCal)
```

### 9.2 Gestión de Enfermeras

**Desde la interfaz web:**
1. Ir a **Enfermeras** en el menú lateral
2. Clic en **Nueva Enfermera**
3. Rellenar: nombre, email y (opcional) teléfono y DNI
4. Guardar

**Importación masiva desde Excel:**
```
Menú Enfermeras → Importar → Seleccionar archivo Excel
```

Formato esperado del Excel:
| nombre | email | telefono | dni |
|--------|-------|----------|-----|
| Ana García | ana@hospital.es | 600000001 | 12345678A |

**Exportar enfermeras a Excel:**
```bash
python manage.py exportar_enfermeras --workspace 1 --output enfermeras.xlsx
```

### 9.3 Gestión de Tipos de Turno

**Crear tipos de turno desde la interfaz:**
1. Ir a **Tipos de Turno**
2. Clic en **Nuevo Tipo de Turno**
3. Configurar nombre, código corto, horario
4. Marcar `es_sustituto_libre` si es un turno "Libre" (sin horario)

**Crear tipos de turno estándar con el comando:**
```bash
python manage.py crear_tipos_turno
```
Crea automáticamente: Mañana (M), Tarde (T), Noche (N), Libre (L), Descanso (D).

**Ejemplo de tipos de turno típicos:**

| Nombre | Código | Hora inicio | Hora fin | Tipo |
|--------|--------|------------|---------|------|
| Mañana | M | 08:00 | 15:00 | Regular |
| Tarde | T | 15:00 | 22:00 | Regular |
| Noche | N | 22:00 | 08:00 | Regular (nocturno) |
| Libre | L | — | — | Sustituto Libre |
| Descanso | D | — | — | Sustituto Libre |

### 9.4 Ejecutar una Planificación

1. Ir a **Configuraciones** → seleccionar la configuración
2. Clic en **Ejecutar Planificación**
3. La planificación se procesa en segundo plano (Celery)
4. La página se actualiza automáticamente cuando finaliza
5. Revisar el estado: `COMPLETADA`, `INVIABLE` o `ERROR`

**Si el estado es `INVIABLE`:**
- Revisar que las restricciones duras son alcanzables con las enfermeras disponibles
- Reducir `cobertura_minima` o aumentar el número de enfermeras
- Verificar que los tipos de turno tienen horarios correctos

**Ejecución desde CLI:**
```bash
python manage.py run_planificacion --config-id 1
# O simulación sin guardar:
python manage.py simular_planificacion --config-id 1
```

### 9.5 Exportar Resultados

Desde la vista de planilla, están disponibles:

| Formato | Descripción |
|---------|-------------|
| **Excel (.xlsx)** | Cuadrante completo con colores por tipo de turno |
| **PDF** | Planilla imprimible con estadísticas |
| **CSV** | Datos tabulares para análisis externo |
| **iCalendar (.ics)** | Importable en Google Calendar, Outlook, etc. |

---

## 10. Capa de Dominio

Los módulos en `turnos/dominio/` proveen una capa de abstracción limpia.

### DTOs Tipados (`turnos/dominio/dtos.py`)

| Clase | Descripción |
|-------|-------------|
| `TipoCelda` (Enum) | Tipos de celda: TURNO, LIBRE, VACACIONES, etc. |
| `TipoIncidencia` (Enum) | Tipos de incidencia |
| `TurnoInfo` (dataclass) | Info de un turno: id, nombre, código, horas, nocturno |
| `CeldaPlanificacion` (dataclass) | Celda de la matriz: enfermera, fecha, turno, tipo |
| `BalanceEnfermera` (dataclass) | Balance acumulado de horas, noches, fines de semana |
| `Incidencia` (dataclass) | Incidencia en el período de planificación |
| `RotacionCiclo` (dataclass) | Ciclo de rotación con sus celdas |
| `MatrizPlanificacion` (dataclass) | Matriz completa [enfermera × fecha] |
| `ResultadoPlanificacion` (dataclass) | Resultado con métricas y mensajes |

### Normalización (`turnos/dominio/normalizacion.py`)

Funciones disponibles:
```python
from turnos.dominio.normalizacion import (
    normalizar_nombre,           # nombre_legacy → NOMBRE_CANONICO
    normalizar_restriccion,      # Dict con nombre normalizado
    normalizar_patron,           # Dict de patrón con nombre normalizado
    normalizar_lista_nombres,    # Lista de nombres normalizados
)
```

---

## 11. Tareas Asíncronas con Celery

Las planificaciones se ejecutan como tareas Celery para no bloquear la interfaz web.

**Configuración:**
- Broker: Redis (`redis://:PASSWORD@redis:6379/0`)
- Backend de resultados: Redis
- Scheduler: `django-celery-beat` con `DatabaseScheduler`

**Monitorear workers en producción:**
```bash
# Ver logs del worker
docker-compose logs -f celery_worker

# En desarrollo
tail -f /tmp/celery_worker.log
```

**Reiniciar workers:**
```bash
# Producción
docker-compose restart celery_worker

# Desarrollo (script incluido)
./restart_celery.sh
```

**Verificar que Celery está funcionando:**
```bash
# Desde el contenedor web
docker-compose exec web python manage.py shell -c "
from proyecto_turnos.celery import app
print(app.control.inspect().active())
"
```

---

## 12. Comandos de Gestión

Comandos `manage.py` personalizados incluidos en la aplicación:

```bash
# Generar datos de prueba (enfermeras, turnos, configuraciones)
python manage.py generar_datos_prueba

# Crear tipos de turno estándar (M, T, N, L, D)
python manage.py crear_tipos_turno

# Cargar restricciones SACYL (normativa enfermería Castilla y León)
python manage.py cargar_restricciones_sacyl

# Importar enfermeras desde Excel
python manage.py importar_enfermeras --file enfermeras.xlsx

# Exportar enfermeras a Excel
python manage.py exportar_enfermeras --output enfermeras.xlsx

# Ejecutar planificación desde CLI
python manage.py run_planificacion --config-id 1

# Simular planificación sin persistir
python manage.py simular_planificacion --config-id 1

# Ver estadísticas del sistema
python manage.py estadisticas_sistema

# Limpiar base de datos (¡cuidado!)
python manage.py limpiar_base_datos --confirm

# Cargar todos los fixtures
python manage.py load_all_fixtures
```

---

## 13. Troubleshooting y Logs

### Ubicación de Logs

| Log | Ruta | Descripción |
|-----|------|-------------|
| Aplicación Django | `logs/django.log` | Requests, errores de la app |
| Celery Worker | `/tmp/celery_worker.log` (dev) | Tareas ejecutadas |
| Celery Beat | `/tmp/celery_beat.log` (dev) | Tareas programadas |
| Nginx (acceso) | `docker/nginx/logs/access.log` | Peticiones HTTP |
| Nginx (errores) | `docker/nginx/logs/error.log` | Errores Nginx |
| Planificación (debug) | `planificacion_debug.log` | Debug del solver |

### Problemas Frecuentes

#### La planificación termina en estado INVIABLE

**Causas posibles:**
1. Las restricciones duras son imposibles de cumplir con las enfermeras disponibles
2. `cobertura_minima` superior al número de enfermeras
3. `max_noches_consecutivas` demasiado bajo para la demanda nocturna

**Diagnóstico:**
```bash
# Ver mensajes de la ejecución
python manage.py shell -c "
from turnos.models import Ejecucion
e = Ejecucion.objects.latest('fecha_inicio')
print(e.mensajes)
"
```

**Soluciones:**
- Reducir `cobertura_minima`
- Aumentar `tiempo_maximo_segundos` y `num_trabajadores`
- Añadir más enfermeras a la configuración
- Relajar restricciones duras

#### El worker Celery no procesa tareas

```bash
# Verificar que Redis está activo
redis-cli -p 6380 ping   # En desarrollo (puerto 6380)
# Debe responder: PONG

# Reiniciar worker
./restart_celery.sh

# Ver logs detallados
tail -100 /tmp/celery_worker.log
```

#### Error de codificación UTF-8 en archivos .ini

Si pytest falla con errores de encoding:
```bash
# Verificar encoding
file pytest.ini
# Debe ser: ASCII text  o  UTF-8 Unicode text (sin BOM)

# Reconvertir si tiene BOM
sed -i 's/\xef\xbb\xbf//' pytest.ini
```

#### Puerto 8080 ya en uso (producción)

```bash
# Usar otro puerto
./start.sh --port 8090

# O en docker-compose.yml, cambiar "8080:80" → "8090:80"
```

#### Error de permisos con Podman rootless (puerto < 1024)

Podman rootless no puede usar puertos < 1024. Solución:
```bash
# Asignar permisos de puerto (requiere sudo, solo una vez)
sudo sysctl net.ipv4.ip_unprivileged_port_start=80
```

#### Migraciones pendientes

```bash
python manage.py showmigrations turnos
python manage.py migrate turnos
```

### Verificar Estado del Sistema

```bash
# Chequeo completo Django
python manage.py check

# Ver estadísticas
python manage.py estadisticas_sistema

# Listar planificaciones recientes
python manage.py shell -c "
from turnos.models import Ejecucion
for e in Ejecucion.objects.order_by('-fecha_inicio')[:5]:
    print(f'{e.id}: {e.configuracion.nombre} - {e.estado}')
"
```

---

## 14. Testing

El proyecto usa **pytest** con `pytest-django`.

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Solo tests de dominio (no requieren BD)
pytest turnos/tests/test_dominio/ -v

# Solo tests del motor
pytest turnos/tests/test_motor/ -v

# Tests de modelos Django
pytest turnos/tests/test_models.py -v

# Con cobertura
pytest --cov=turnos --cov-report=html

# Sin caché
pytest --cache-clear
```

### Estructura de Tests

| Archivo | Tests | Qué prueba |
|---------|-------|-----------|
| `test_dominio/test_normalizacion.py` | 16 | Normalización de nombres legacy |
| `test_dominio/test_dtos.py` | 17 | DTOs tipados del dominio |
| `test_motor/test_pipeline.py` | 3+ | Pipeline completo de planificación |
| `test_motor/test_reparador.py` | — | Reparador CP-SAT |
| `test_motor/test_integracion_final.py` | — | Integración end-to-end |
| `test_models.py` | — | Modelos Django |
| `test_generador.py` | — | Generador de planificaciones |

**Total: 36 tests pasando (100%)**

### Configuración pytest (`pytest.ini`)

```ini
[pytest]
DJANGO_SETTINGS_MODULE = proyecto_turnos.settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
```

---

## 15. Decisiones de Diseño

### 1. Solver como Reparador, no como Generador Libre

El solver CP-SAT **no genera** la planilla desde cero. Actúa como motor de reparación sobre una rotación base determinista.

- **Problema con la generación libre:** produce soluciones inestables e impredecibles, difíciles de validar por los responsables de turno
- **Ventaja de la reparación:** preserva la regularidad del cuadrante y minimiza los cambios respecto al patrón esperado

### 2. Métrica Principal: Horas Reales

La equidad se mide por **horas reales trabajadas**, no por conteo bruto de turnos.

- Diferentes turnos tienen diferente duración (noche puede ser 10h, mañana 7h)
- El equilibrio real de carga es en horas, no en número de asignaciones

### 3. Planificación Contextual con Histórico

Cada planificación considera el `BalanceHistoricoEnfermera` acumulado de meses anteriores.

- El equilibrio es **anual**, no mensual
- Una enfermera con muchas noches el mes anterior recibe menos noches el mes siguiente
- Sin histórico, el equilibrio anual sería imposible

### 4. Dominio Explícito sobre JSON Libre

Se usan modelos tipados (DTOs, modelos Django) en lugar de campos JSON no estructurados.

- JSON libre como semántica interna dificulta validación y mantenimiento
- Los DTOs explícitos proporcionan type-safety y documentación
- JSON puede existir como formato de entrada/salida, pero se normaliza internamente

### 5. Un Único Motor Activo (CP-SAT)

Se eliminó la implementación en Pyomo y se consolidó todo en un único pipeline CP-SAT.

- Múltiples implementaciones paralelas generan confusión y bugs difíciles de rastrear
- CP-SAT de Google OR-Tools es más adecuado para este problema de satisfacción de restricciones
- Una sola ruta activa simplifica mantenimiento y testing

### 6. Normalización Transparente de Nombres Legacy

Las configuraciones antiguas siguen funcionando mediante normalización automática con warnings en logs.

- No rompe configuraciones existentes
- Permite migración gradual al vocabulario canónico
- Trazabilidad completa de qué configuraciones usan nombres legacy

---

## 16. Historial de Refactorización

La refactorización mayor fue completada el **23 de abril de 2026**. Estado: **100% completado**.

### Fases Completadas

| Fase | Descripción | Estado |
|------|-------------|--------|
| Fase 0 | Saneamiento del repositorio (17 archivos eliminados) | ✅ |
| Fase 1 | Normalización de vocabulario y corrección de 6 bugs | ✅ |
| Fase 2 | 6 nuevos modelos de dominio + campo `tipo_celda` | ✅ |
| Fase 3 | Motor de planificación con reparador CP-SAT | ✅ |
| Fase 4 | DTOs tipados y vocabulario canónico | ✅ |
| Fase 5 | 36 tests pasando (100%) | ✅ |
| Fase 6 | Documentación completa de arquitectura | ✅ |

### Métricas del Refactor

| Métrica | Valor |
|---------|-------|
| Archivos eliminados | 17 |
| Archivos creados | 18 |
| Archivos modificados | 12 |
| Líneas de código añadidas | ~2,900 |
| Tests totales | 36 (100% pasando) |
| Bugs corregidos | 6 |
| Nuevos modelos Django | 6 |
| DTOs tipados | 9 |

### Bugs Corregidos en la Refactorización

1. `turnosconsecutivosmax` → `TURNO_CONSECUTIVOS_MAX` en restricciones duras
2. `equidadturnos` → `EQUIDAD_TURNOS` en restricciones blandas
3. Bug crítico `patrones_turnos` → `patrones_turnos_json` en views.py
4. Estado `INVIABLE` añadido a `Ejecucion.ESTADO_CHOICES`
5. Exportación horizontal `LIBRE` corregida cuando `turno` es null
6. Normalización case-sensitive añadida

### Migraciones Aplicadas

| Migración | Descripción |
|-----------|-------------|
| `0009_add_domain_models.py` | ContratoEnfermera, RotacionBase, CeldaRotacion, AsignacionRotacionEnfermera, Incidencia, BalanceHistoricoEnfermera |
| `0013_tipoturno_dinamico.py` | Modelo TipoTurno completamente dinámico |
| `0014_tipoturno_sustituto_libre.py` | Campo `es_sustituto_libre` en TipoTurno |

---

*Documentación generada en junio 2026. Para reportar problemas o mejoras, usar el sistema de issues del repositorio.*

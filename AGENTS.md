# AGENTS.md — Planificador de Turnos de Enfermería

Reglas y convenciones para asistentes de código. Leer antes de modificar cualquier archivo.

---

## Identidad del proyecto

- **Qué es:** planificador de cuadrantes regulares de enfermería, NO un generador genérico de horarios
- **Motor:** OR-Tools CP-SAT como **reparador**, no como generador libre — nunca generar planilla desde cero
- **Equidad:** siempre en **horas reales** (no conteo de turnos); usar `duracion_horas` del `TipoTurno`
- **Alcance de la planificación:** contextual — considera `BalanceHistoricoEnfermera` de meses anteriores

---

## Comandos esenciales

```bash
# Ejecutar tests (siempre verificar antes de dar una tarea por terminada)
pytest turnos/tests/ -v

# Tests rápidos sin base de datos
pytest turnos/tests/test_dominio/ -v

# Servidor de desarrollo (incluye Celery + Redis automáticamente)
./start.sh --dev

# Migraciones
source .venv/bin/activate && python manage.py migrate

# Verificar integridad Django
python manage.py check
```

---

## Archivos clave

| Archivo | Qué contiene |
|---------|-------------|
| `turnos/models.py` | Todos los modelos Django |
| `turnos/dominio/normalizacion.py` | Mapeo nombres legacy → canónico |
| `turnos/dominio/vocabulario.py` | Listas canónicas de restricciones y patrones |
| `turnos/dominio/dtos.py` | DTOs tipados del motor (9 clases) |
| `turnos/motor/pipeline.py` | Orquestador del pipeline de 5 fases |
| `turnos/motor/reparador.py` | Reparador CP-SAT (modificar con cuidado) |
| `turnos/motor/rotacion_base.py` | Constructor determinista de la rotación base |
| `turnos/restricciones_duras.py` | Restricciones hard del solver |
| `turnos/restricciones_blandas.py` | Restricciones soft del solver |
| `turnos/validador.py` | Validador post-solver |
| `turnos/tasks.py` | Tareas Celery (punto de entrada asíncrono) |
| `turnos/views.py` | Vistas Django |
| `turnos/forms.py` | Formularios + wizard SessionWizardView |

---

## Reglas del solver CP-SAT

1. **CP-SAT solo acepta enteros** — siempre convertir con `int()` antes de usarlos en restricciones o expresiones de objetivo
2. **LIBRE_SENTINEL se excluye** de la restricción de turnos consecutivos — solo contar turnos de trabajo reales
3. **LIBRE_SENTINEL se excluye** del objetivo de equilibrio de fines de semana
4. **Las incidencias se aplican post-generación** (overlay) — todas las celdas son modificables durante la optimización CP-SAT
5. **Timeout interno del reparador:** 30 segundos; el `tiempo_maximo_segundos` de la configuración aplica al nivel de `tasks.py`

---

## Reglas de los modelos

### TipoTurno
- Turnos con `es_sustituto_libre=True`: **excluir de demanda, cobertura, ajuste de horas y CP-SAT** — solo participan en secuencias obligatorias de rotaciones base
- Turnos con `es_sustituto_libre=True`: no pueden tener `hora_inicio` / `hora_fin` ni `es_incidencia=True`
- Turnos regulares (no incidencia, no libre): **obligatorio** que tengan `hora_inicio` y `hora_fin`
- `codigo_corto` es único por workspace
- Al anotar con ORM: usar `num_configs_count` (no `num_configuraciones` — conflicto con property del modelo)

### ConfiguracionPlanificacion
- `patrones_turnos_json` es la **fuente activa principal** de patrones
- `patrones_turnos` (ManyToMany) es **legacy**, solo para compatibilidad
- Usar `get_patrones_combinados()` para obtener todos los patrones unificados
- El related_name de `turnos` (ManyToMany a TipoTurno) es `configuracionplanificacion`, no `configuraciones`

### Ejecucion
- Estados posibles: `PENDIENTE`, `PROCESANDO`, `COMPLETADA`, `INVIABLE`, `ERROR`
- `INVIABLE` = el solver no pudo satisfacer las restricciones duras (no es un error de código)
- Acceder a `ejecucion.planilla_generada` con `hasattr(ejecucion, 'planilla_generada')`, nunca con `if ejecucion.planilla_generada:` (lanza `RelatedObjectDoesNotExist` si no existe)

### ResultadoPlanificacion (DTO)
- Campo booleano de éxito: `exitosa` — **no** `exito` (causa AttributeError)

---

## Acceso a parámetros de restricciones duras

Las restricciones pueden llegar en dos formatos. **Siempre usar este patrón:**

```python
# Correcto — soporta formato legacy flat y formato moderno anidado
valor = r.get('valor', r.get('parametros', {}).get('max', DEFAULT))

# Incorrecto — solo funciona con formato legacy
valor = r.get('valor', DEFAULT)
```

---

## Vocabulario canónico (UPPER_SNAKE_CASE)

### Restricciones duras
```
TURNO_CONSECUTIVOS_MAX    # antes: turnosconsecutivosmax, turnos_consecutivos_max
NOCHES_CONSECUTIVAS_MAX   # antes: turnos_nocturnos_consecutivos_max
DESCANSO_ENTRE_TURNOS     # antes: descanso_12h
COBERTURA_MINIMA
COBERTURA_MAXIMA
TURNO_POR_DIA
DIAS_LIBRES_ANUALES
DESCANSO_SEMANAL
```

### Restricciones blandas
```
EQUIDAD_TURNOS            # antes: equidadturnos, equidad_turnos
MINIMIZAR_NOCHES          # antes: minimizarnoches, minimizar_noches
EQUIDAD_NOCHES
EQUIDAD_FINDES
EQUIDAD_FESTIVOS
MINIMIZAR_CAMBIOS
```

### Patrones
```
SECUENCIA_OBLIGATORIA     # antes: SECUENCIA_TURNOS
ROTACION_CICLICA          # antes: ROTACION_TURNOS, ROTACION
DESCANSO_POST_TURNO
MAX_CONSECUTIVOS
COBERTURA_MINIMA
BLOQUEO_TRANSICION
DISTRIBUCION_EQUITATIVA
```

La normalización es automática vía `turnos/dominio/normalizacion.py` con warning en logs.
Usar siempre nombres canónicos en código nuevo.

---

## Pitfalls frecuentes

| Error | Causa | Solución |
|-------|-------|---------|
| `AttributeError: property 'X' has no setter` | Nombre de anotación ORM = nombre de property del modelo | Usar nombre distinto (ej. `num_configs_count`) |
| `RelatedObjectDoesNotExist` al acceder a OneToOneField | Acceso directo a relación inversa opcional | `hasattr(obj, 'campo')` antes de acceder |
| `TypeError: '<' not supported between int and dict` | `demanda_por_turno` devuelve dicts, no enteros | Extraer `demanda[turno].get('min', 0)` |
| CP-SAT rechaza el modelo con error de tipo | Float en expresión de restricción | `int(valor)` antes de pasar a CP-SAT |
| Restricción no se aplica | Nombre legacy no reconocido | Usar vocabulario canónico; `normalizacion.py` genera warning |
| `AttributeError: 'ResultadoPlanificacion' has no 'exito'` | Nombre incorrecto del campo | Campo correcto: `exitosa` |
| Restricción de consecutivos cuenta libres | `LIBRE_SENTINEL` incluido en contador | Filtrar `LIBRE_SENTINEL` antes de contar |

---

## Convenciones de Django

- `manage.py` **siempre** con el Python del virtualenv `.venv`, no con el del sistema
- Modo desarrollo: Redis en puerto **6380** (no 6379, reservado para producción)
- Base de datos desarrollo: SQLite en `BASE_DIR / 'db.sqlite3'` (ruta portable)
- Base de datos producción: PostgreSQL (variable `DATABASE_URL`)
- Encoding: todos los archivos Python y `.ini` en **UTF-8 sin BOM**

---

## Pipeline de planificación (orden estricto)

```
1. rotacion_base.py   → matriz base determinista [enfermera × fecha]
2. incidencias.py     → bloquear celdas fijas (vacaciones, bajas...)
3. cobertura.py       → calcular desviaciones y métricas
4. reparador.py       → CP-SAT: reparar celdas modificables
5. validador_motor.py → validar restricciones duras + persistir balances
```

No saltarse fases ni cambiar el orden.

---

## Objetivos lexicográficos del solver (prioridad decreciente)

1. Cumplir TODAS las restricciones duras
2. Minimizar desviación de la rotación base
3. Minimizar desviación de horas mensuales
4. Minimizar desviación del saldo anual acumulado
5. Equilibrar noches
6. Equilibrar fines de semana
7. Equilibrar festivos

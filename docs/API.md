# API del Planificador

## Modelos Principales

### Enfermera

```python
class Enfermera(models.Model):
    nombre = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    dni = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    activa = models.BooleanField(default=True)
    preferencias = models.JSONField(null=True, blank=True)
```

### TipoTurno

```python
class TipoTurno(models.Model):
    nombre = models.CharField(max_length=20, choices=TIPO_TURNO_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)
```

### ConfiguracionPlanificacion

```python
class ConfiguracionPlanificacion(models.Model):
    nombre = models.CharField(max_length=200)
    num_dias = models.IntegerField()
    fecha_inicio = models.DateField()
    enfermeras = models.ManyToManyField(Enfermera)
    turnos = models.ManyToManyField(TipoTurno)
    demanda_por_turno = models.JSONField()
    restricciones_duras = models.JSONField(null=True)
    restricciones_blandas = models.JSONField(null=True)
```

## Uso del Generador

```python
from turnos.generador import GeneradorTurnos

# Crear generador
configuracion = ConfiguracionPlanificacion.objects.get(pk=1)
generador = GeneradorTurnos(configuracion)

# Resolver
resultado = generador.resolver()

# Resultado
{
    'success': True,
    'status': 'OPTIMAL',
    'es_optima': True,
    'tiempo_ejecucion': 45.3,
    'asignaciones': [...]
}
```

## Tareas Celery

### Ejecutar Planificacion

```python
from turnos.tasks import ejecutar_planificacion_async

task = ejecutar_planificacion_async.delay(ejecucion_id=123)
task.ready()  # Verificar si termino
task.result  # Obtener resultado
```

### Limpiar Ejecuciones

```python
from turnos.tasks import limpiar_ejecuciones_antiguas

limpiar_ejecuciones_antiguas.delay(dias=30)
```

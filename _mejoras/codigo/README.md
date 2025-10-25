# Codigo Celery Mejorado

## Instalacion

1. HACER BACKUP del archivo turnos/tasks.py actual
2. Revisar tasks_mejorado.py
3. Adaptar a tu proyecto si es necesario
4. Reemplazar turnos/tasks.py con el contenido mejorado

## Nuevas Tareas

- ejecutar_planificacion_async: Mejorado con reintentos y mejor manejo de errores
- crear_planilla_desde_resultado: Creacion optimizada con bulk_create
- limpiar_ejecuciones_antiguas: Mantenimiento automatico
- generar_estadisticas_mensuales: Reportes automaticos
- 
otificar_ejecucion_completada: Sistema de notificaciones

## Configuracion Celery

Agregar a proyecto_turnos/settings.py:

```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Madrid'
```

## Ejecutar Worker

```bash
celery -A proyecto_turnos worker --loglevel=info
```

Windows:
```bash
celery -A proyecto_turnos worker --loglevel=info --pool=solo
```

## Tareas Periodicas

Configurar en celery.py:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'limpiar-ejecuciones-diario': {
        'task': 'turnos.tasks.limpiar_ejecuciones_antiguas',
        'schedule': crontab(hour=2, minute=0),  # 2 AM diario
    },
    'estadisticas-mensuales': {
        'task': 'turnos.tasks.generar_estadisticas_mensuales',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),  # Primer dia del mes
    },
}
```

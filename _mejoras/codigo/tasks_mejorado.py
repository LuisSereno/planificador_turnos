'''
Tareas asÃ­ncronas de Celery - CODIGO MEJORADO
IMPORTANTE: Revisar y adaptar antes de reemplazar tasks.py existente
'''
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from turnos.models import Ejecucion, Planilla, AsignacionTurno
from turnos.generador import GeneradorTurnos

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def ejecutar_planificacion_async(self, ejecucion_id):
    '''Ejecuta planificacion de forma as

incrona'''
    try:
        ejecucion = Ejecucion.objects.get(id=ejecucion_id)
        ejecucion.estado = 'PROCESANDO'
        ejecucion.save()
        
        generador = GeneradorTurnos(ejecucion.configuracion)
        resultado = generador.resolver()
        
        ejecucion.resultado = resultado
        ejecucion.es_optima = resultado.get('es_optima', False)
        
        if resultado.get('success'):
            planilla = crear_planilla_desde_resultado(ejecucion, resultado)
            ejecucion.planilla = planilla
            ejecucion.estado = 'COMPLETADA'
        else:
            ejecucion.estado = 'ERROR'
            ejecucion.mensaje_error = resultado.get('mensaje', 'Error desconocido')
        
        ejecucion.fecha_fin = timezone.now()
        ejecucion.save()
        
        return {'success': True, 'ejecucion_id': ejecucion_id}
        
    except Exception as e:
        logger.error(f\"Error en ejecucion {ejecucion_id}: {e}\")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        raise


def crear_planilla_desde_resultado(ejecucion, resultado):
    '''Crea planilla con asignaciones desde resultado del solver'''
    config = ejecucion.configuracion
    
    planilla = Planilla.objects.create(
        nombre=f\"Planilla {config.nombre} - {timezone.now().strftime('%d/%m/%Y')}\",
        ejecucion=ejecucion,
        fecha_inicio=config.fecha_inicio,
        fecha_fin=config.fecha_inicio + timedelta(days=config.num_dias-1),
        num_dias=config.num_dias
    )
    
    asignaciones = []
    for asig_data in resultado.get('asignaciones', []):
        from datetime import datetime
        fecha = datetime.fromisoformat(asig_data['fecha']).date()
        
        asignaciones.append(AsignacionTurno(
            planilla=planilla,
            enfermera_id=asig_data['enfermera_id'],
            fecha=fecha,
            turno_id=asig_data.get('turno_id'),
            es_dia_libre=asig_data.get('es_dia_libre', False)
        ))
    
    AsignacionTurno.objects.bulk_create(asignaciones, batch_size=100)
    logger.info(f\"Planilla {planilla.id} creada con {len(asignaciones)} asignaciones\")
    
    return planilla


@shared_task
def limpiar_ejecuciones_antiguas(dias=30):
    '''Limpia ejecuciones antiguas para liberar espacio'''
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    ejecuciones_antiguas = Ejecucion.objects.filter(
        fecha_inicio__lt=fecha_limite,
        estado__in=['COMPLETADA', 'ERROR']
    )
    
    count = ejecuciones_antiguas.count()
    ejecuciones_antiguas.delete()
    
    logger.info(f\"Limpiadas {count} ejecuciones antiguas\")
    return {'eliminadas': count}


@shared_task
def generar_estadisticas_mensuales():
    '''Genera estadisticas mensuales del sistema'''
    from django.db.models import Count, Avg
    from datetime import date
    
    hoy = timezone.now().date()
    primer_dia_mes = date(hoy.year, hoy.month, 1)
    
    stats = {
        'ejecuciones_totales': Ejecucion.objects.filter(
            fecha_inicio__gte=primer_dia_mes
        ).count(),
        'ejecuciones_exitosas': Ejecucion.objects.filter(
            fecha_inicio__gte=primer_dia_mes,
            estado='COMPLETADA'
        ).count(),
        'tiempo_promedio': Ejecucion.objects.filter(
            fecha_inicio__gte=primer_dia_mes,
            estado='COMPLETADA'
        ).aggregate(Avg('tiempo_ejecucion'))['tiempo_ejecucion__avg']
    }
    
    logger.info(f\"Estadisticas mensuales generadas: {stats}\")
    return stats


@shared_task
def notificar_ejecucion_completada(ejecucion_id):
    '''Envia notificacion cuando una ejecucion termina'''
    try:
        ejecucion = Ejecucion.objects.get(id=ejecucion_id)
        
        # Aqui puedes agregar logica de notificacion
        # Por ejemplo, enviar email, webhook, etc.
        
        logger.info(f\"Notificacion enviada para ejecucion {ejecucion_id}\")
        return {'notificado': True}
        
    except Exception as e:
        logger.error(f\"Error al notificar ejecucion {ejecucion_id}: {e}\")
        return {'notificado': False, 'error': str(e)}

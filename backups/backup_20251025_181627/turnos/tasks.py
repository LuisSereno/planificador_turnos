"""
Celery tasks for turnos app
"""
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.utils import timezone
import logging
from datetime import datetime, timedelta
from celery import shared_task
from .models import Ejecucion, ConfiguracionPlanificacion, Planilla, AsignacionTurno

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, name='turnos.tasks.ejecutar_planificacion_async')
def ejecutar_planificacion_async(self, ejecucion_id):
    """
    Tarea Celery para ejecutar planificación de turnos

    Args:
        ejecucion_id: ID de la ejecución a procesar
    """
    try:
        logger.info(f"🚀 Iniciando tarea Celery para ejecución #{ejecucion_id}")

        # Importar aquí para evitar circular imports
        from .generador import GeneradorTurnos

        ejecucion = Ejecucion.objects.get(id=ejecucion_id)
        configuracion = ejecucion.configuracion

        ejecucion.estado = 'PROCESANDO'
        ejecucion.fecha_inicio = timezone.now()
        ejecucion.save()

        logger.info(f"📊 Procesando configuración: {configuracion.nombre}")

        generador = GeneradorTurnos(configuracion)

        logger.info(f"👥 {generador.num_enfermeras} enfermeras, {generador.num_turnos} turnos, {generador.num_dias} días")

        logger.info("⚙️ Ejecutando solver OR-Tools...")
        resultado = generador.resolver()

        if not resultado or not resultado.get('status') in ['OPTIMAL', 'FEASIBLE']:
            raise ValueError("El solver no encontró una solución válida")

        logger.info("✅ Solver completado exitosamente")

        # Crear planilla
        planilla = crear_planilla_desde_resultado(ejecucion, resultado, generador)

        # Actualizar ejecución
        ejecucion.estado = 'COMPLETADA'
        ejecucion.fecha_fin = timezone.now()
        ejecucion.es_optima = resultado.get('es_optima', False)
        ejecucion.penalizacion_total = resultado.get('penalizacion', 0.0)
        ejecucion.resultado = resultado
        ejecucion.planilla = planilla
        ejecucion.mensajes = {
            'asignaciones_creadas': planilla.asignaciones.count(),
            'tiempo_ejecucion': (ejecucion.fecha_fin - ejecucion.fecha_inicio).total_seconds(),
            'mensaje': f'✅ Planificación completada exitosamente'
        }
        ejecucion.save()

        logger.info(f"✅ Ejecución #{ejecucion_id} completada exitosamente")

        # Enviar notificación
        enviar_notificacion_ejecucion.delay(ejecucion_id, 'completada')

        return {'success': True, 'ejecucion_id': ejecucion_id, 'planilla_id': planilla.id}

    except Ejecucion.DoesNotExist:
        logger.error(f"❌ Ejecución #{ejecucion_id} no encontrada")
        return {'success': False, 'error': 'Ejecución no encontrada'}

    except Exception as e:
        logger.error(f"❌ Error en ejecución #{ejecucion_id}: {e}", exc_info=True)

        try:
            ejecucion = Ejecucion.objects.get(id=ejecucion_id)
            ejecucion.estado = 'ERROR'
            ejecucion.fecha_fin = timezone.now()
            ejecucion.mensajes = {
                'error': str(e),
                'tipo': type(e).__name__,
                'mensaje': 'La ejecución falló. Revisa los logs para más detalles.'
            }
            ejecucion.save()

            # Enviar notificación de error
            enviar_notificacion_ejecucion.delay(ejecucion_id, 'error')
        except:
            pass

        # Reintentar hasta 3 veces
        raise self.retry(exc=e, countdown=60)


def crear_planilla_desde_resultado(ejecucion, resultado, generador):
    """
    Crea una planilla y sus asignaciones desde el resultado del solver

    Args:
        ejecucion: Instancia de Ejecucion
        resultado: Diccionario con el resultado de la optimización
        generador: Instancia de GeneradorTurnos

    Returns:
        Instancia de Planilla creada
    """
    config = ejecucion.configuracion

    # Crear planilla
    fecha_inicio = config.fecha_inicio
    fecha_fin = fecha_inicio + timedelta(days=config.num_dias - 1)

    planilla = Planilla.objects.create(
        nombre=f"Planilla {config.nombre} - {fecha_inicio.strftime('%d/%m/%Y')}",
        descripcion=f"Generada automáticamente el {timezone.now().strftime('%d/%m/%Y %H:%M')}",
        ejecucion=ejecucion,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        num_dias=config.num_dias
    )

    # Preparar datos para bulk_create
    asignaciones_bulk = []
    turnos_trabajados = 0
    dias_libres = 0

    for asig_data in resultado['asignaciones']:
        enfermera_id = asig_data['enfermera_id']
        dia = asig_data['dia']
        es_dia_libre = asig_data.get('es_dia_libre', False)
        fecha_str = asig_data.get('fecha')

        # Parsear fecha
        if fecha_str:
            fecha = datetime.fromisoformat(fecha_str).date()
        else:
            fecha = fecha_inicio + timedelta(days=dia)

        # Buscar enfermera
        enfermera = next((e for e in generador.enfermeras if e.id == enfermera_id), None)
        if not enfermera:
            logger.warning(f"⚠️ Enfermera {enfermera_id} no encontrada")
            continue

        if es_dia_libre:
            # Día libre
            asignacion = AsignacionTurno(
                planilla=planilla,
                enfermera=enfermera,
                fecha=fecha,
                es_dia_libre=True
            )
            asignaciones_bulk.append(asignacion)
            dias_libres += 1
        else:
            # Turno trabajado
            turno_id = asig_data.get('turno_id')
            turno_nombre = asig_data.get('turno')  # Clave: 'turno', no 'turno_nombre'

            # Buscar turno por ID o por nombre
            turno = None
            if turno_id:
                turno = next((t for t in generador.turnos if t.id == turno_id), None)

            if not turno and turno_nombre and turno_nombre != 'LIBRE':
                turno = next((t for t in generador.turnos if t.nombre == turno_nombre), None)

            if turno:
                asignacion = AsignacionTurno(
                    planilla=planilla,
                    enfermera=enfermera,
                    fecha=fecha,
                    turno=turno,
                    es_dia_libre=False
                )
                asignaciones_bulk.append(asignacion)
                turnos_trabajados += 1
            else:
                logger.warning(
                    f"⚠️ Turno no encontrado: {turno_nombre or turno_id} para enfermera {enfermera.nombre} el día {dia}")

    # Crear todas las asignaciones en una sola operación
    if asignaciones_bulk:
        AsignacionTurno.objects.bulk_create(asignaciones_bulk)
        logger.info(f'📋 Planilla {planilla.id} creada con {len(asignaciones_bulk)} asignaciones')
        logger.info(f'   💼 Turnos trabajados: {turnos_trabajados}')
        logger.info(f'   🏖️ Días libres: {dias_libres}')
    else:
        logger.error("❌ No se crearon asignaciones")

    return planilla


@shared_task(name='turnos.tasks.enviar_notificacion_ejecucion')
def enviar_notificacion_ejecucion(ejecucion_id, tipo='completada'):
    """
    Envía notificación por email sobre el estado de una ejecución

    Args:
        ejecucion_id: ID de la ejecución
        tipo: Tipo de notificación ('completada', 'error')
    """
    try:
        ejecucion = Ejecucion.objects.get(id=ejecucion_id)
        config = ejecucion.configuracion

        if tipo == 'completada':
            subject = f'✅ Planificación completada: {config.nombre}'
            message = f'''
La planificación "{config.nombre}" ha sido completada con éxito.

Estado: {'Óptima' if ejecucion.es_optima else 'Factible'}
Penalización: {ejecucion.penalizacion_total:.2f}
Duración: {ejecucion.duracion:.2f} segundos

Accede a los resultados desde la aplicación.
            '''
        else:
            subject = f'❌ Error en planificación: {config.nombre}'
            message = f'''
Ha ocurrido un error al generar la planificación "{config.nombre}".

Error: {ejecucion.mensajes.get('error', 'Error desconocido') if ejecucion.mensajes else 'Error desconocido'}

Por favor, revisa la configuración e intenta nuevamente.
            '''

        # Enviar email al creador
        if config.creado_por and config.creado_por.email:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[config.creado_por.email],
                fail_silently=True
            )
            logger.info(f'📧 Notificación enviada a {config.creado_por.email}')

    except Exception as e:
        logger.error(f'❌ Error al enviar notificación: {e}')


@shared_task(name='turnos.tasks.limpiar_ejecuciones_antiguas')
def limpiar_ejecuciones_antiguas(dias=90):
    """
    Limpia ejecuciones antiguas (más de X días)

    Args:
        dias: Número de días de antigüedad (default: 90)
    """
    try:
        fecha_limite = timezone.now() - timedelta(days=dias)

        # Eliminar ejecuciones antiguas en estado ERROR o COMPLETADA
        eliminadas = Ejecucion.objects.filter(
            fecha_inicio__lt=fecha_limite,
            estado__in=['ERROR', 'COMPLETADA']
        ).delete()

        logger.info(f'🧹 Limpiadas {eliminadas[0]} ejecuciones antiguas')

        return {'success': True, 'eliminadas': eliminadas[0]}

    except Exception as e:
        logger.error(f'❌ Error al limpiar ejecuciones: {e}')
        return {'success': False, 'error': str(e)}


@shared_task(name='turnos.tasks.enviar_recordatorios_turnos')
def enviar_recordatorios_turnos():
    """
    Envía recordatorios de turnos del día siguiente
    (Placeholder - implementar según necesidades)
    """
    try:
        # TODO: Implementar lógica de recordatorios
        logger.info('📧 Tarea de recordatorios ejecutada')
        return {'success': True, 'message': 'Recordatorios procesados'}

    except Exception as e:
        logger.error(f'❌ Error al enviar recordatorios: {e}')
        return {'success': False, 'error': str(e)}


@shared_task(name='turnos.tasks.calcular_estadisticas_dashboard')
def calcular_estadisticas_dashboard():
    """
    Calcula y cachea las estadísticas del dashboard
    """
    from django.core.cache import cache
    from django.db.models import Avg

    try:
        stats = {
            'total_configuraciones': ConfiguracionPlanificacion.objects.filter(activa=True).count(),
            'total_ejecuciones': Ejecucion.objects.count(),
            'ejecuciones_completadas': Ejecucion.objects.filter(estado='COMPLETADA').count(),
        }

        # Penalización promedio
        penalizacion_avg = Ejecucion.objects.filter(
            estado='COMPLETADA',
            penalizacion_total__isnull=False
        ).aggregate(Avg('penalizacion_total'))

        stats['penalizacion_promedio'] = penalizacion_avg['penalizacion_total__avg'] or 0

        # Cachear por 1 hora
        cache.set('dashboard_stats', stats, 3600)

        logger.info('📊 Estadísticas del dashboard actualizadas')

        return stats

    except Exception as e:
        logger.error(f'❌ Error al calcular estadísticas: {e}')
        raise

# -*- coding: utf-8 -*-
"""
Tareas asíncronas de Celery para planificación de turnos
"""

from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging
import json

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def ejecutar_planificacion_async(self, configuracion_id):
    """
    Ejecuta la planificación de turnos de forma asíncrona

    Args:
        configuracion_id: ID (int o dict) de ConfiguracionPlanificacion

    Returns:
        dict: Resultado con success, ejecucion_id y datos
    """
    from turnos.models import ConfiguracionPlanificacion, Ejecucion, Planilla, AsignacionTurno
    from turnos.generador import GeneradorTurnos
    from datetime import timedelta

    ejecucion = None

    try:
        # ══════════════════════════════════════════════════════════════
        # 1. VALIDAR Y CONVERTIR ID
        # ══════════════════════════════════════════════════════════════
        if isinstance(configuracion_id, dict):
            # Si viene como dict (error común), extraer ID
            configuracion_id = configuracion_id.get('id') or configuracion_id.get('pk')
            logger.warning(f"configuracion_id vino como dict, extrayendo: {configuracion_id}")

        try:
            configuracion_id = int(configuracion_id)
        except (TypeError, ValueError) as e:
            logger.error(f"No se puede convertir configuracion_id a int: {configuracion_id}")
            return {
                'success': False,
                'error': f'ID inválido: {configuracion_id}'
            }

        logger.info(f"═══ Iniciando planificación async para config ID: {configuracion_id} ═══")

        # ══════════════════════════════════════════════════════════════
        # 2. OBTENER CONFIGURACIÓN
        # ══════════════════════════════════════════════════════════════
        try:
            config = ConfiguracionPlanificacion.objects.select_related('creado_por').get(pk=configuracion_id)
            logger.info(f"Config: {config.nombre} | Días: {config.num_dias} | Inicio: {config.fecha_inicio}")
        except ConfiguracionPlanificacion.DoesNotExist:
            logger.error(f"Configuración {configuracion_id} no existe")
            return {
                'success': False,
                'error': f'Configuración {configuracion_id} no encontrada'
            }

        # ══════════════════════════════════════════════════════════════
        # 3. CREAR O ACTUALIZAR EJECUCIÓN
        # ══════════════════════════════════════════════════════════════
        with transaction.atomic():
            ejecucion = Ejecucion.objects.filter(
                configuracion=config,
                estado='PENDIENTE'
            ).order_by('-fecha_inicio').first()

            if not ejecucion:
                ejecucion = Ejecucion.objects.create(
                    configuracion=config,
                    estado='PROCESANDO'
                )
                logger.info(f"✓ Ejecución {ejecucion.id} creada (PROCESANDO)")
            else:
                ejecucion.estado = 'PROCESANDO'
                ejecucion.save()
                logger.info(f"✓ Ejecución {ejecucion.id} actualizada a PROCESANDO")

        # ══════════════════════════════════════════════════════════════
        # 4. EJECUTAR GENERADOR
        # ══════════════════════════════════════════════════════════════
        logger.info("Inicializando GeneradorTurnos...")
        generador = GeneradorTurnos(config)

        logger.info("Resolviendo planificación...")
        resultado = generador.resolver()

        logger.info(f"Resolución completada: {resultado.get('status')}")

        # ══════════════════════════════════════════════════════════════
        # 5. PROCESAR RESULTADO Y GUARDAR
        # ══════════════════════════════════════════════════════════════
        with transaction.atomic():
            ejecucion.estado = 'COMPLETADA' if resultado.get('success') else 'ERROR'
            ejecucion.fecha_fin = timezone.now()
            ejecucion.es_optima = resultado.get('es_optima', False)
            ejecucion.resultado = resultado

            # Guardar estadísticas de validación
            if 'validacion' in resultado:
                ejecucion.mensajes = resultado['validacion']
                logger.info(f"Validaciones: {len(resultado['validacion'].get('validaciones', []))} OK, "
                           f"{len(resultado['validacion'].get('violaciones', []))} violaciones")

            # Si hay penalización, guardarla
            if 'penalizacion_total' in resultado:
                ejecucion.penalizacion_total = resultado['penalizacion_total']

            ejecucion.save()

            # ══════════════════════════════════════════════════════════════
            # 6. CREAR PLANILLA Y ASIGNACIONES
            # ══════════════════════════════════════════════════════════════
            if resultado.get('success') and resultado.get('asignaciones'):
                logger.info("Creando planilla y asignaciones...")

                # Crear planilla
                fecha_inicio = config.fecha_inicio
                fecha_fin = fecha_inicio + timedelta(days=config.num_dias - 1)

                planilla = Planilla.objects.create(
                    nombre=f"Planificación {config.nombre} - {fecha_inicio.strftime('%d/%m/%Y')}",
                    descripcion=f"Generada automáticamente el {timezone.now().strftime('%d/%m/%Y %H:%M')}",
                    ejecucion=ejecucion,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    num_dias=config.num_dias
                )

                logger.info(f"✓ Planilla {planilla.id} creada")

                # Crear asignaciones en bulk
                asignaciones_bulk = []
                for asig in resultado['asignaciones']:
                    from turnos.models import Enfermera, TipoTurno
                    from datetime import datetime

                    enfermera = Enfermera.objects.get(pk=asig['enfermera_id'])
                    turno = TipoTurno.objects.get(pk=asig['turno_id']) if asig.get('turno_id') else None
                    fecha = datetime.fromisoformat(asig['fecha']).date()

                    asignaciones_bulk.append(
                        AsignacionTurno(
                            planilla=planilla,
                            enfermera=enfermera,
                            fecha=fecha,
                            turno=turno,
                            es_dia_libre=asig.get('es_dia_libre', False)
                        )
                    )

                AsignacionTurno.objects.bulk_create(asignaciones_bulk)
                logger.info(f"✓ {len(asignaciones_bulk)} asignaciones creadas")

                # Vincular planilla a ejecución
                ejecucion.planilla = planilla
                ejecucion.save()

        # ══════════════════════════════════════════════════════════════
        # 7. RESULTADO FINAL
        # ══════════════════════════════════════════════════════════════
        duracion = ejecucion.duracion if ejecucion.duracion else 0

        logger.info(f"═══ Ejecución {ejecucion.id} completada en {duracion:.2f}s ═══")

        return {
            'success': resultado.get('success', False),
            'ejecucion_id': ejecucion.id,
            'planilla_id': ejecucion.planilla.id if ejecucion.planilla else None,
            'estado': ejecucion.estado,
            'es_optima': ejecucion.es_optima,
            'num_asignaciones': resultado.get('num_asignaciones', 0),
            'tiempo_ejecucion': duracion,
            'validacion': resultado.get('validacion', {})
        }

    except Exception as exc:
        # ══════════════════════════════════════════════════════════════
        # 8. MANEJO DE ERRORES
        # ══════════════════════════════════════════════════════════════
        logger.exception(f"ERROR en ejecución {configuracion_id}: {exc}")

        # Actualizar ejecución a ERROR si existe
        if ejecucion:
            try:
                with transaction.atomic():
                    ejecucion.estado = 'ERROR'
                    ejecucion.fecha_fin = timezone.now()
                    ejecucion.mensajes = {
                        'error': str(exc),
                        'tipo': type(exc).__name__,
                        'retry_count': self.request.retries
                    }
                    ejecucion.save()
                    logger.info(f"Ejecución {ejecucion.id} marcada como ERROR")
            except Exception as e:
                logger.error(f"No se pudo actualizar ejecución a ERROR: {e}")

        # Reintentar la tarea (máximo 3 veces)
        if self.request.retries < self.max_retries:
            logger.info(f"Reintentando tarea (intento {self.request.retries + 1}/{self.max_retries})...")
            raise self.retry(exc=exc)
        else:
            logger.error("Máximo de reintentos alcanzado")
            return {
                'success': False,
                'error': str(exc),
                'ejecucion_id': ejecucion.id if ejecucion else None
            }


@shared_task
def limpiar_ejecuciones_antiguas(dias=30):
    """
    Limpia ejecuciones antiguas (completadas o con error)

    Args:
        dias: Eliminar ejecuciones más antiguas que N días

    Returns:
        dict: Número de registros eliminados
    """
    from turnos.models import Ejecucion
    from datetime import timedelta

    fecha_limite = timezone.now() - timedelta(days=dias)

    eliminadas, detalles = Ejecucion.objects.filter(
        fecha_inicio__lt=fecha_limite,
        estado__in=['ERROR', 'COMPLETADA']
    ).delete()

    logger.info(f"Limpieza: {eliminadas} ejecuciones eliminadas (>{dias} días)")

    return {
        'eliminadas': eliminadas,
        'detalles': detalles
    }


@shared_task
def generar_reporte_estadisticas(mes, anio):
    """
    Genera reporte de estadísticas mensuales

    Args:
        mes: Mes (1-12)
        anio: Año (ej: 2025)

    Returns:
        dict: Estadísticas del mes
    """
    from turnos.models import Ejecucion, Planilla
    from datetime import datetime

    inicio = datetime(anio, mes, 1)
    if mes == 12:
        fin = datetime(anio + 1, 1, 1)
    else:
        fin = datetime(anio, mes + 1, 1)

    ejecuciones = Ejecucion.objects.filter(
        fecha_inicio__gte=inicio,
        fecha_inicio__lt=fin
    )

    stats = {
        'mes': mes,
        'anio': anio,
        'total_ejecuciones': ejecuciones.count(),
        'completadas': ejecuciones.filter(estado='COMPLETADA').count(),
        'errores': ejecuciones.filter(estado='ERROR').count(),
        'optimas': ejecuciones.filter(es_optima=True).count(),
        'planillas_generadas': Planilla.objects.filter(
            fecha_inicio__gte=inicio,
            fecha_inicio__lt=fin
        ).count()
    }

    logger.info(f"Reporte {mes}/{anio}: {json.dumps(stats, indent=2)}")

    return stats

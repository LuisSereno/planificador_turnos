"""
Tareas asíncronas de Celery — Código mejorado
IMPORTANTE: Revisa y ajusta nombres de campos según tus modelos antes de reemplazar.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone

from turnos.generador import GeneradorTurnos
from turnos.models import Ejecucion, Planilla, AsignacionTurno

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def ejecutar_planificacion_async(self, ejecucion_id: int) -> dict:
    """
    Ejecuta la planificación de forma asíncrona con reintentos controlados.
    """
    try:
        ejecucion = Ejecucion.objects.get(id=ejecucion_id)
        ejecucion.estado = "PROCESANDO"
        ejecucion.fecha_inicio = ejecucion.fecha_inicio or timezone.now()
        ejecucion.save(update_fields=["estado", "fecha_inicio"])

        generador = GeneradorTurnos(ejecucion.configuracion)
        resultado = generador.resolver()

        # Persistir resultado del solver
        ejecucion.resultado = resultado
        ejecucion.es_optima = bool(resultado.get("es_optima", False))

        if resultado.get("success"):
            planilla = crear_planilla_desde_resultado(ejecucion, resultado)
            ejecucion.planilla = planilla
            ejecucion.estado = "COMPLETADA"
        else:
            ejecucion.estado = "ERROR"
            # Si tu modelo tiene un campo para error, descomenta y ajusta:
            # ejecucion.mensaje_error = resultado.get("mensaje", "Error desconocido")

        ejecucion.fecha_fin = timezone.now()
        ejecucion.save()
        return {"success": True, "ejecucion_id": ejecucion_id}
    except Exception as e:
        logger.error(f"Error en ejecución {ejecucion_id}: {e}")
        # Reintenta con backoff fijo si aún quedan reintentos
        if getattr(self.request, "retries", 0) < getattr(self, "max_retries", 0):
            raise self.retry(exc=e, countdown=60)
        raise


def crear_planilla_desde_resultado(ejecucion: Ejecucion, resultado: dict) -> Planilla:
    """
    Crea una planilla y sus asignaciones a partir del resultado del solver.
    """
    config = ejecucion.configuracion

    planilla = Planilla.objects.create(
        nombre=f"Planilla {config.nombre} - {timezone.now().strftime('%d/%m/%Y')}",
        ejecucion=ejecucion,
        fecha_inicio=config.fecha_inicio,
        fecha_fin=config.fecha_inicio + timedelta(days=config.num_dias - 1),
        num_dias=config.num_dias,
    )

    asignaciones_bulk: list[AsignacionTurno] = []
    for asig in resultado.get("asignaciones", []):
        # Acepta 'YYYY-MM-DD' o ISO 8601 con hora
        fecha_val = asig.get("fecha")
        if isinstance(fecha_val, str):
            # fromisoformat soporta 'YYYY-MM-DD' y 'YYYY-MM-DDTHH:MM:SS'
            fecha_dt = datetime.fromisoformat(fecha_val)
            fecha = fecha_dt.date()
        elif isinstance(fecha_val, datetime):
            fecha = fecha_val.date()
        else:
            # Si no hay fecha válida, omite la asignación
            logger.warning(f"Asig sin fecha válida: {asig}")
            continue

        asignaciones_bulk.append(
            AsignacionTurno(
                planilla=planilla,
                enfermera_id=asig["enfermera_id"],
                fecha=fecha,
                turno_id=asig.get("turno_id"),
                es_dia_libre=asig.get("es_dia_libre", False),
            )
        )

    # Inserción eficiente por lotes
    if asignaciones_bulk:
        AsignacionTurno.objects.bulk_create(asignaciones_bulk, batch_size=100)
        logger.info(
            f"Planilla {planilla.id} creada con {len(asignaciones_bulk)} asignaciones"
        )
    else:
        logger.warning(f"Planilla {planilla.id} creada sin asignaciones")

    return planilla


@shared_task
def limpiar_ejecuciones_antiguas(dias: int = 30) -> dict:
    """
    Elimina ejecuciones antiguas para liberar espacio.
    """
    fecha_limite = timezone.now() - timedelta(days=dias)
    qs = Ejecucion.objects.filter(
        fecha_inicio__lt=fecha_limite, estado__in=["COMPLETADA", "ERROR"]
    )
    count = qs.count()
    qs.delete()
    logger.info(f"Limpiadas {count} ejecuciones antiguas")
    return {"eliminadas": count}


@shared_task
def generar_estadisticas_mensuales() -> dict:
    """
    Calcula estadísticas agregadas del mes en curso.
    """
    from django.db.models import Avg  # import local para evitar cargas innecesarias

    hoy = timezone.now().date()
    primer_dia = hoy.replace(day=1)

    total = Ejecucion.objects.filter(fecha_inicio__gte=primer_dia).count()
    exitosas = Ejecucion.objects.filter(
        fecha_inicio__gte=primer_dia, estado="COMPLETADA"
    ).count()
    tiempo_prom = (
        Ejecucion.objects.filter(fecha_inicio__gte=primer_dia, estado="COMPLETADA")
        .aggregate(Avg("tiempo_ejecucion"))
        .get("tiempo_ejecucion__avg")
    )

    stats = {
        "ejecuciones_totales": total,
        "ejecuciones_exitosas": exitosas,
        "tiempo_promedio": tiempo_prom,
    }
    logger.info(f"Estadísticas mensuales: {stats}")
    return stats


@shared_task
def notificar_ejecucion_completada(ejecucion_id: int) -> dict:
    """
    Envía una notificación al finalizar una ejecución (placeholder).
    """
    try:
        ejecucion = Ejecucion.objects.get(id=ejecucion_id)
        # Implementa aquí email/webhook/etc.
        logger.info(f"Notificación enviada para ejecución {ejecucion.pk}")
        return {"notificado": True}
    except Exception as e:
        logger.error(f"Error al notificar ejecución {ejecucion_id}: {e}")
        return {"notificado": False, "error": str(e)}

# -*- coding: utf-8 -*-
"""
Tareas asíncronas de Celery para planificación de turnos
"""

from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging
import json
from datetime import date, timedelta
from typing import Dict, List

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
        resultado = generador.generar()

        logger.info(f"Resolución completada: {resultado.get('status')}")
        
        if not resultado.get('success'):
            # Comprimir JSON para logs
            error_json = json.dumps(resultado, separators=(',', ':'), ensure_ascii=False)
            logger.error(f"Error en la resolución: {error_json}")

        # ══════════════════════════════════════════════════════════════
        # 5. PROCESAR RESULTADO Y GUARDAR
        # ══════════════════════════════════════════════════════════════
        with transaction.atomic():
            if resultado.get('status') == 'INFEASIBLE':
                ejecucion.estado = 'INVIABLE'
            else:
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

                # Note: Planilla.ejecucion is the canonical relationship
                # No need to set ejecucion.planilla (deprecated)

        # ══════════════════════════════════════════════════════════════
        # 7. RESULTADO FINAL
        # ══════════════════════════════════════════════════════════════
        duracion = ejecucion.duracion if ejecucion.duracion else 0

        logger.info(f"═══ Ejecución {ejecucion.id} completada en {duracion:.2f}s ═══")

        # Log compressed result for AI analysis
        result_log = {
            'success': resultado.get('success', False),
            'ejecucion_id': ejecucion.id,
            'estado': ejecucion.estado,
            'es_optima': ejecucion.es_optima,
            'num_asignaciones': resultado.get('num_asignaciones', 0),
            'validacion': resultado.get('validacion', {}),
        }
        logger.info(f"Resultado ejecución {ejecucion.id}: {json.dumps(result_log, separators=(',', ':'), ensure_ascii=False)}")

        return {
            'success': resultado.get('success', False),
            'ejecucion_id': ejecucion.id,
            'planilla_id': ejecucion.planilla_generada.id if ejecucion.planilla_generada else None,
            'estado': ejecucion.estado,
            'es_optima': ejecucion.es_optima,
            'num_asignaciones': resultado.get('num_asignaciones', 0),
            'tiempo_ejecucion': duracion,
            'validacion': resultado.get('validacion', {}),
            'mensaje': resultado.get('mensaje', '') if resultado.get('status') == 'INFEASIBLE' else None
        }

    except Exception as exc:
        # ══════════════════════════════════════════════════════════════
        # 8. MANEJO DE ERRORES
        # ══════════════════════════════════════════════════════════════
        logger.error(f"ERROR CRÍTICO en ejecución {configuracion_id}")
        if 'config' in locals():
            logger.error(f"Configuración fallida: ID={config.id} Nombre='{config.nombre}'")
        logger.exception("Detalles del error:", exc_info=exc)

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

    # Comprimir JSON para logs
    stats_json = json.dumps(stats, separators=(',', ':'), ensure_ascii=False)
    logger.info(f"Reporte {mes}/{anio}: {stats_json}")

    return stats

@shared_task
def test_db_connection():
  from turnos.models import ConfiguracionPlanificacion
  from django.conf import settings
  import logging
  logger = logging.getLogger(__name__)

  logger.info(f"DB Path: {settings.DATABASES['default']['NAME']}")
  total = ConfiguracionPlanificacion.objects.count()
  logger.info(f"Total configs: {total}")

  if total > 0:
      ids = list(ConfiguracionPlanificacion.objects.values_list('id', 'nombre'))
      for id, nombre in ids:
          logger.info(f"  - ID {id}: {nombre}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def ejecutar_planificacion_motor_async(self, configuracion_id):
    """
    Ejecuta la planificación usando el NUEVO MOTOR de planificación.
    
    Este es el reemplazo del generador antiguo, usando el pipeline de 5 fases:
    1. Rotación base determinista
    2. Aplicación de incidencias
    3. Análisis de cobertura
    4. Reparación CP-SAT
    5. Validación final
    
    Args:
        configuracion_id: ID de ConfiguracionPlanificacion
        
    Returns:
        dict: Resultado con success, ejecucion_id y datos
    """
    from turnos.models import (
        ConfiguracionPlanificacion, 
        Ejecucion, 
        Planilla, 
        AsignacionTurno,
        Enfermera,
        TipoTurno,
        RotacionBase,
        AsignacionRotacionEnfermera,
        Incidencia,
    )
    from turnos.dominio.dtos import (
        RotacionCiclo,
        TurnoInfo,
        Incidencia as DTOIncidencia,
        TipoIncidencia,
    )
    from turnos.motor.pipeline import PipelinePlanificacion
    
    ejecucion = None
    
    try:
        logger.info(f"═══ [NUEVO MOTOR] Iniciando planificación para config ID: {configuracion_id} ═══")
        
        # 1. Obtener configuración
        try:
            config = ConfiguracionPlanificacion.objects.select_related('creado_por').get(pk=configuracion_id)
        except ConfiguracionPlanificacion.DoesNotExist:
            logger.error(f"Configuración {configuracion_id} no existe")
            return {
                'success': False,
                'error': f'Configuración {configuracion_id} no encontrada'
            }
        
        # 2. Crear ejecución
        with transaction.atomic():
            ejecucion = Ejecucion.objects.create(
                configuracion=config,
                estado='PROCESANDO'
            )
            logger.info(f"✓ Ejecución {ejecucion.id} creada")
        
        # 3. Preparar datos para el motor
        # Fechas del período
        fechas = [
            config.fecha_inicio + timedelta(days=i) 
            for i in range(config.num_dias)
        ]
        
        # Enfermeras del workspace
        enfermeras = {
            e.id: e.nombre 
            for e in Enfermera.objects.filter(workspace=config.workspace, activa=True)
        }
        
        # Turnos
        turnos_info = {
            t.id: TurnoInfo(
                id=t.id,
                nombre=t.nombre,
                hora_inicio=t.hora_inicio,
                hora_fin=t.hora_fin,
                duracion_horas=t.duracion_horas,
                es_nocturno=t.es_nocturno,
            )
            for t in TipoTurno.objects.filter(workspace=config.workspace)
        }
        
        # Rotaciones (usar rotaciones configuradas o crear una por defecto)
        asignaciones_rotacion = {}
        desfases = {}
        
        rotaciones_db = AsignacionRotacionEnfermera.objects.filter(
            enfermera_id__in=enfermeras.keys()
        ).select_related('rotacion')
        
        for asignacion in rotaciones_db:
            # Convertir rotación DB a DTO
            celdas = [
                celda.turno if not celda.es_libre else None
                for celda in asignacion.rotacion.celdas.order_by('orden')
            ]
            
            rotacion_dto = RotacionCiclo(
                nombre=asignacion.rotacion.nombre,
                ciclo_dias=asignacion.rotacion.ciclo_dias,
                celdas=[
                    TurnoInfo(
                        id=t.id,
                        nombre=t.nombre,
                        hora_inicio=t.hora_inicio,
                        hora_fin=t.hora_fin,
                        duracion_horas=t.duracion_horas,
                        es_nocturno=t.es_nocturno,
                    ) if t else None
                    for t in celdas if t is not None or True  # Incluir None para libres
                ],
            )
            
            asignaciones_rotacion[asignacion.enfermera_id] = rotacion_dto
            desfases[asignacion.enfermera_id] = asignacion.desfase
        
        # Si no hay rotaciones configuradas, crear una por defecto
        if not asignaciones_rotacion:
            logger.warning("No hay rotaciones configuradas, usando rotación por defecto 2M-2T-2N-2L")
            
            # Crear rotación default con primeros 4 turnos
            turnos_lista = list(turnos_info.values())[:4]
            ciclo_default = []
            for t in turnos_lista:
                ciclo_default.extend([t, t])  # 2 días de cada turno
            ciclo_default.extend([None, None])  # 2 días libres
            
            rotacion_default = RotacionCiclo(
                nombre='Rotación Default 2M-2T-2N-2L',
                ciclo_dias=8,
                celdas=ciclo_default,
            )
            
            for enf_id in enfermeras:
                asignaciones_rotacion[enf_id] = rotacion_default
                desfases[enf_id] = 0
        
        # Incidencias
        incidencias_db = Incidencia.objects.filter(
            enfermera_id__in=enfermeras.keys()
        ).select_related('turno_fijo', 'enfermera')
        
        incidencias_list = []
        for inc_db in incidencias_db:
            tipo_map = {
                'VACACIONES': TipoIncidencia.VACACIONES,
                'PERMISO': TipoIncidencia.PERMISO,
                'BAJA': TipoIncidencia.BAJA,
                'FORMACION': TipoIncidencia.FORMACION,
                'LIBRANZA_BLOQUEADA': TipoIncidencia.LIBRANZA_BLOQUEADA,
                'ASIGNACION_FIJA': TipoIncidencia.ASIGNACION_FIJA,
            }
            
            # Build turno_fijo object if exists
            turno_fijo_obj = None
            if inc_db.turno_fijo:
                turno_fijo_obj = TurnoInfo(
                    id=inc_db.turno_fijo.id,
                    nombre=inc_db.turno_fijo.nombre,
                    hora_inicio=inc_db.turno_fijo.hora_inicio,
                    hora_fin=inc_db.turno_fijo.hora_fin,
                    duracion_horas=inc_db.turno_fijo.duracion_horas,
                    es_nocturno=inc_db.turno_fijo.es_nocturno,
                )
            
            incidencias_list.append(DTOIncidencia(
                enfermera_id=inc_db.enfermera_id,
                enfermera_nombre=inc_db.enfermera.nombre,
                tipo=tipo_map.get(inc_db.tipo, TipoIncidencia.PERMISO),
                fecha_inicio=inc_db.fecha_inicio,
                fecha_fin=inc_db.fecha_fin,
                turno_fijo=turno_fijo_obj,
                observaciones=inc_db.observaciones,
            ))
        
        # Configuración de restricciones
        configuracion_restricciones = {}
        if config.restricciones_duras:
            for r in config.restricciones_duras:
                if isinstance(r, dict):
                    configuracion_restricciones[r.get('nombre', '')] = r.get('valor', {})
        
        # Build horas_objetivo from contracts and get historical balances
        from turnos.models import ContratoEnfermera, BalanceHistoricoEnfermera
        
        horas_objetivo = {}
        balances_historicos = {}
        
        for enf_id in enfermeras.keys():
            try:
                contrato = ContratoEnfermera.objects.get(enfermera_id=enf_id)
                # Calculate hours for the period from weekly hours
                semanas_en_periodo = config.num_dias / 7.0
                horas_objetivo[enf_id] = float(contrato.horas_semana_objetivo * semanas_en_periodo)
            except ContratoEnfermera.DoesNotExist:
                # Default to 40 hours/week
                horas_objetivo[enf_id] = 40.0 * (config.num_dias / 7.0)
            
            # Get historical balance if exists
            try:
                balance_hist = BalanceHistoricoEnfermera.objects.get(
                    enfermera_id=enf_id,
                    periodo_referencia=str(config.fecha_inicio.year)
                )
                balances_historicos[enf_id] = {
                    'horas_acumuladas_previas': float(balance_hist.horas_acumuladas_previas),
                    'noches_acumuladas': balance_hist.noches_acumuladas,
                    'fines_semana_acumulados': balance_hist.fines_semana_acumulados,
                    'festivos_acumulados': balance_hist.festivos_acumulados,
                    'ultimo_turno_fecha': balance_hist.ultimo_turno_fecha.isoformat() if balance_hist.ultimo_turno_fecha else None,
                    'ultimo_turno_tipo_id': balance_hist.ultimo_turno_tipo_id if balance_hist.ultimo_turno_tipo else None,
                }
            except BalanceHistoricoEnfermera.DoesNotExist:
                balances_historicos[enf_id] = {}
        
        # Coverage minimum from demand
        cobertura_minima = {}
        if config.demanda_por_turno:
            # Map turno nombre to turno id
            for turno in TipoTurno.objects.filter(workspace=config.workspace):
                if turno.nombre in config.demanda_por_turno:
                    cobertura_minima[turno.id] = config.demanda_por_turno[turno.nombre]
        
        # 4. Ejecutar pipeline
        logger.info("Ejecutando pipeline de planificación...")
        
        pipeline = PipelinePlanificacion(
            fechas=fechas,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
            incidencias=incidencias_list,
            horas_objetivo=horas_objetivo,
            cobertura_minima=cobertura_minima,
            turnos_info=turnos_info,
            restricciones_duras=config.restricciones_duras or [],
            restricciones_blandas=config.restricciones_blandas or [],
            balances_historicos=balances_historicos,
        )
        
        resultado = pipeline.ejecutar()
        
        # 5. Procesar resultado
        with transaction.atomic():
            ejecucion.estado = 'COMPLETADA' if resultado.exitosa else 'INVIABLE'
            ejecucion.fecha_fin = timezone.now()
            ejecucion.es_optima = not resultado.violaciones
            ejecucion.resultado = {
                'violaciones': resultado.violaciones,
                'warnings': resultado.warnings,
                'balances': {
                    str(k): {
                        'horas_asignadas': v.horas_asignadas,
                        'noches_asignadas': v.noches_asignadas,
                        'fines_semana_asignados': v.fines_semana_asignados,
                    }
                    for k, v in resultado.balances.items()
                },
            }
            ejecucion.save()
            
            # Crear planilla si fue exitoso
            if resultado.exitosa:
                fecha_inicio = config.fecha_inicio
                fecha_fin = fecha_inicio + timedelta(days=config.num_dias - 1)
                
                planilla = Planilla.objects.create(
                    nombre=f"Planificación {config.nombre} - {fecha_inicio.strftime('%d/%m/%Y')}",
                    descripcion=f"Generada con NUEVO MOTOR el {timezone.now().strftime('%d/%m/%Y %H:%M')}",
                    ejecucion=ejecucion,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    num_dias=config.num_dias,
                )
                
                # Crear asignaciones desde la matriz
                asignaciones_bulk = []
                for enf_id, celdas_enfermera in resultado.matriz.celdas.items():
                    enfermera = Enfermera.objects.get(pk=enf_id)
                    
                    for fecha, celda in celdas_enfermera.items():
                        turno = None
                        es_libre = celda.es_libre or celda.tipo_celda == 'LIBRE'
                        
                        if celda.turno_id:
                            turno = TipoTurno.objects.get(pk=celda.turno_id)
                        
                        asignaciones_bulk.append(
                            AsignacionTurno(
                                planilla=planilla,
                                enfermera=enfermera,
                                fecha=fecha,
                                turno=turno,
                                es_dia_libre=es_libre,
                                tipo_celda=celda.tipo_celda.value if hasattr(celda.tipo_celda, 'value') else celda.tipo_celda,
                            )
                        )
                
                AsignacionTurno.objects.bulk_create(asignaciones_bulk)
                logger.info(f"✓ Planilla {planilla.id} creada con {len(asignaciones_bulk)} asignaciones")
                
                # Persistir balances históricos actualizados
                for enf_id, balance in resultado.balances.items():
                    balance_hist, created = BalanceHistoricoEnfermera.objects.update_or_create(
                        enfermera_id=enf_id,
                        periodo_referencia=str(config.fecha_inicio.year),
                        defaults={
                            'horas_acumuladas_previas': balance.horas_totales_con_historico,
                            'noches_acumuladas': balance.noches_asignadas + balance.noches_acumuladas,
                            'fines_semana_acumulados': balance.fines_semana_asignados + balance.fines_semana_acumulados,
                            'festivos_acumulados': balance.festivos_asignados + balance.festivos_acumulados,
                            'ultimo_turno_fecha': config.fecha_inicio + timedelta(days=config.num_dias - 1),
                        }
                    )
                    action = "Creado" if created else "Actualizado"
                    logger.info(f"✓ {action} balance histórico para enfermera {enf_id}")
        
        logger.info(f"═══ [NUEVO MOTOR] Ejecución {ejecucion.id} completada ═══")
        
        return {
            'success': resultado.exitosa,
            'ejecucion_id': ejecucion.id,
            'planilla_id': planilla.id if resultado.exitosa else None,
            'estado': ejecucion.estado,
            'violaciones': len(resultado.violaciones),
            'warnings': len(resultado.warnings),
        }
        
    except Exception as e:
        logger.error(f"[NUEVO MOTOR] Error en planificación: {e}", exc_info=True)
        
        if ejecucion:
            ejecucion.estado = 'ERROR'
            ejecucion.fecha_fin = timezone.now()
            ejecucion.resultado = {'error': str(e)}
            ejecucion.save()
        
        self.retry(exc=e)


def debug_database_task():
    """Task para debug de base de datos"""
    from turnos.models import ConfiguracionPlanificacion
    from django.conf import settings
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"DB Path: {settings.DATABASES['default']['NAME']}")
    total = ConfiguracionPlanificacion.objects.count()
    logger.info(f"Total configs: {total}")

    if total > 0:
        ids = list(ConfiguracionPlanificacion.objects.values_list('id', 'nombre'))
        for id, nombre in ids:
            logger.info(f"  - ID {id}: {nombre}")

    return {'total': total, 'db_path': settings.DATABASES['default']['NAME']}

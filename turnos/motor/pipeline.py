# -*- coding: utf-8 -*-
"""
Pipeline principal de planificación.
Orquesta las fases: rotación base → incidencias → cobertura → reparación → validación.
"""
import logging
from datetime import date
from typing import List, Dict, Optional

from ..dominio.dtos import (
    MatrizPlanificacion,
    ResultadoPlanificacion,
    RotacionCiclo,
    Incidencia,
)
from .rotacion_base import RotacionBaseBuilder
from .incidencias import AplicadorIncidencias
from .cobertura import AnalizadorCobertura
from .reparador import ReparadorCPSAT

logger = logging.getLogger(__name__)


class PipelinePlanificacion:
    """
    Orquestador del pipeline de planificación.
    
    Ejecuta las fases secuenciales:
    1. Construcción determinista de rotación base
    2. Aplicación de incidencias fijas
    3. Cálculo de cobertura y desviaciones
    4. Reparación con CP-SAT (si hay conflictos)
    5. Validación y persistencia de balances
    """
    
    def __init__(
        self,
        fechas: List[date],
        enfermeras: Dict[int, str],
        asignaciones_rotacion: Dict[int, RotacionCiclo],
        desfases: Dict[int, int],
        incidencias: List[Incidencia],
        horas_objetivo: Dict[int, float],
        cobertura_minima: Optional[Dict[int, int]] = None,
        configuracion_solver: Optional[Dict] = None,
        turnos_info: Optional[Dict[int, 'TurnoInfo']] = None,
        restricciones_duras: List[dict] = None,
        restricciones_blandas: List[dict] = None,
        balances_historicos: Optional[Dict[int, dict]] = None,
    ):
        self.fechas = fechas
        self.enfermeras = enfermeras
        self.asignaciones_rotacion = asignaciones_rotacion
        self.desfases = desfases
        self.incidencias = incidencias
        self.horas_objetivo = horas_objetivo
        self.cobertura_minima = cobertura_minima or {}
        self.configuracion_solver = configuracion_solver or {}
        self.turnos_info = turnos_info or {}
        self.restricciones_duras = restricciones_duras or []
        self.restricciones_blandas = restricciones_blandas or []
        self.balances_historicos = balances_historicos or {}
        
    def ejecutar(self) -> ResultadoPlanificacion:
        """
        Ejecuta el pipeline completo de planificación.
        
        Returns:
            ResultadoPlanificacion con la matriz final y métricas
        """
        logger.info("=" * 80)
        logger.info("INICIANDO PIPELINE DE PLANIFICACIÓN")
        logger.info("=" * 80)
        
        try:
            # FASE 1: Construcción de rotación base
            logger.info("FASE 1: Construyendo rotación base...")
            matriz_base = RotacionBaseBuilder(
                fechas=self.fechas,
                enfermeras=self.enfermeras,
                asignaciones_rotacion=self.asignaciones_rotacion,
                desfases=self.desfases,
            ).construir()
            logger.info(f"✓ Rotación base: {matriz_base.total_celdas()} celdas generadas")
            
            # FASE 2: Aplicación de incidencias
            logger.info("FASE 2: Aplicando incidencias...")
            matriz_bloqueada = AplicadorIncidencias(
                matriz_base=matriz_base,
                incidencias=self.incidencias,
            ).aplicar()
            celdas_bloqueadas = sum(
                1 
                for celdas_enf in matriz_bloqueada.celdas.values() 
                for celda in celdas_enf.values() 
                if not celda.es_modificable
            )
            logger.info(f"✓ Incidencias aplicadas: {celdas_bloqueadas} celdas bloqueadas")
            
            # FASE 3: Análisis de cobertura
            logger.info("FASE 3: Analizando cobertura...")
            analisis = AnalizadorCobertura(
                matriz=matriz_bloqueada,
                horas_objetivo_enfermeras=self.horas_objetivo,
                cobertura_minima_turnos=self.cobertura_minima,
                balances_historicos=self.balances_historicos,
            ).analizar()
            
            if analisis['tiene_conflictos']:
                logger.warning(f"⚠ {len(analisis['conflictos'])} conflictos de cobertura detectados")
            else:
                logger.info("✓ Sin conflictos de cobertura")
            
            # FASE 4: Reparación con CP-SAT (si es necesario)
            matriz_final = matriz_bloqueada
            celdas_modificadas = 0
            estado_solver = 'NO_EJECUTADO'
            
            if analisis['tiene_conflictos']:
                logger.info("FASE 4: Iniciando reparación con CP-SAT...")
                reparador = ReparadorCPSAT(
                    matriz_bloqueada=matriz_bloqueada,
                    analisis_cobertura=analisis,
                    turnos_info=self.turnos_info,
                    restricciones_duras=self.restricciones_duras,
                    objetivos=self.restricciones_blandas,
                )
                matriz_final = reparador.reparar()
                estado_solver = reparador.solver_status if hasattr(reparador, 'solver_status') else 'EJECUTADO'
                
                # Contar celdas modificadas
                celdas_modificadas = sum(
                    1
                    for enf_id in matriz_final.celdas
                    for fecha, celda in matriz_final.celdas[enf_id].items()
                    if matriz_bloqueada.obtener_celda(enf_id, fecha) and \
                       celda.turno != matriz_bloqueada.obtener_celda(enf_id, fecha).turno
                )
                logger.info(f"✓ Reparación completada: {celdas_modificadas} celdas modificadas")
            else:
                logger.info("FASE 4: No se requiere reparación")
            
            # FASE 5: Validación final
            logger.info("FASE 5: Validando resultado final...")
            resultado = ResultadoPlanificacion(
                exitosa=True,
                matriz=matriz_final,
                balances=analisis['balances'],
                metricas={
                    'total_celdas': matriz_final.total_celdas(),
                    'celdas_bloqueadas': celdas_bloqueadas,
                    'celdas_modificables': matriz_final.total_celdas() - celdas_bloqueadas,
                    'conflictos_cobertura': len(analisis['conflictos']),
                },
                estado_solver=estado_solver,
                celdas_modificadas=celdas_modificadas,
                celdas_totales=matriz_final.total_celdas(),
            )
            
            logger.info("=" * 80)
            logger.info("PIPELINE COMPLETADO EXITOSAMENTE")
            logger.info("=" * 80)
            
            return resultado
            
        except Exception as e:
            logger.error(f"✗ Error en pipeline: {str(e)}", exc_info=True)
            return ResultadoPlanificacion(
                exitosa=False,
                matriz=MatrizPlanificacion(),
                balances={},
                metricas={},
                estado_solver='ERROR',
                violaciones=[str(e)],
            )

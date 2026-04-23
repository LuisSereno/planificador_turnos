# -*- coding: utf-8 -*-
"""
Aplicador de incidencias y bloqueos.
Modifica la matriz base para reflejar vacaciones, bajas, permisos y asignaciones fijas.
"""
import logging
from datetime import date, timedelta
from typing import List, Dict

from ..dominio.dtos import (
    MatrizPlanificacion,
    CeldaPlanificacion,
    TipoCelda,
    Incidencia,
    TipoIncidencia,
)

logger = logging.getLogger(__name__)


class AplicadorIncidencias:
    """
    Aplica incidencias a la matriz de planificación base.
    
    Esta es la fase 2 del pipeline: las celdas afectadas por incidencias se 
    marcan como no modificables y se les asigna el tipo correspondiente.
    """
    
    def __init__(
        self,
        matriz_base: MatrizPlanificacion,
        incidencias: List[Incidencia],
    ):
        self.matriz_base = matriz_base
        self.incidencias = incidencias
        
    def aplicar(self) -> MatrizPlanificacion:
        """
        Aplica todas las incidencias a la matriz.
        
        Returns:
            Matriz modificada con incidencias aplicadas
        """
        logger.info(f"Aplicando {len(self.incidencias)} incidencias a la matriz")
        
        celdas_bloqueadas = 0
        
        for incidencia in self.incidencias:
            # Determinar el rango de fechas afectadas
            fecha_actual = incidencia.fecha_inicio
            while fecha_actual <= incidencia.fecha_fin:
                # Verificar si la enfermera tiene celda en esta fecha
                celda = self.matriz_base.obtener_celda(incidencia.enfermera_id, fecha_actual)
                
                if celda:
                    # Aplicar incidencia según tipo
                    if incidencia.tipo == TipoIncidencia.VACACIONES:
                        celda.tipo_celda = TipoCelda.VACACIONES
                        celda.turno = None
                        celda.es_modificable = False
                        celda.observaciones = 'Vacaciones'
                        
                    elif incidencia.tipo == TipoIncidencia.PERMISO:
                        celda.tipo_celda = TipoCelda.PERMISO
                        celda.turno = None
                        celda.es_modificable = False
                        celda.observaciones = 'Permiso'
                        
                    elif incidencia.tipo == TipoIncidencia.BAJA:
                        celda.tipo_celda = TipoCelda.BAJA
                        celda.turno = None
                        celda.es_modificable = False
                        celda.observaciones = 'Baja médica'
                        
                    elif incidencia.tipo == TipoIncidencia.FORMACION:
                        celda.tipo_celda = TipoCelda.FORMACION
                        celda.es_modificable = False
                        celda.observaciones = 'Formación'
                        
                    elif incidencia.tipo == TipoIncidencia.LIBRANZA_BLOQUEADA:
                        celda.tipo_celda = TipoCelda.LIBRE
                        celda.turno = None
                        celda.es_modificable = False
                        
                    elif incidencia.tipo == TipoIncidencia.ASIGNACION_FIJA:
                        if incidencia.turno_fijo:
                            celda.turno = incidencia.turno_fijo
                            celda.tipo_celda = TipoCelda.ASIGNACION_FIJA
                            celda.es_modificable = False
                            celda.observaciones = 'Asignación fija'
                    
                    celdas_bloqueadas += 1
                
                fecha_actual += timedelta(days=1)
        
        logger.info(f"Incidencias aplicadas: {celdas_bloqueadas} celdas bloqueadas")
        return self.matriz_base

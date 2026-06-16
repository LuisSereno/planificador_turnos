# -*- coding: utf-8 -*-
"""
Overlay de incidencias post-generación.
Aplica vacaciones, permisos, bajas y otras incidencias sobre la planificación
ya generada, sin afectar al proceso de generación del solver.
"""
import logging
from datetime import date, timedelta
from typing import Dict, List

from ..dominio.dtos import (
    MatrizPlanificacion,
    CeldaPlanificacion,
    TipoCelda,
    TipoIncidencia,
    Incidencia,
    TurnoInfo,
    ResultadoOverlay,
)

logger = logging.getLogger(__name__)


class OverlayIncidencias:
    """
    Aplica incidencias como overlay sobre la matriz de planificación completada.
    
    Esta es la Phase 6 del pipeline: las incidencias se aplican DESPUÉS de que
    el solver haya generado la planificación óptima, como un paso de
    post-procesamiento determinista.
    """
    
    def __init__(
        self,
        matriz: MatrizPlanificacion,
        incidencias: List[Incidencia],
        turnos_info: Dict[int, TurnoInfo],
        cobertura_minima: Dict[int, int] = None,
    ):
        self.matriz = matriz
        self.incidencias = incidencias or []
        self.turnos_info = turnos_info
        self.cobertura_minima = cobertura_minima or {}
    
    def aplicar(self) -> ResultadoOverlay:
        """
        Aplica todas las incidencias sobre una copia de la matriz.
        
        Returns:
            ResultadoOverlay con la matriz final, celdas sobreescritas y huecos
        """
        logger.info(f"Aplicando overlay de {len(self.incidencias)} incidencias...")
        
        # Clonar la matriz para no modificar la original
        matriz_final = self.matriz.clone()
        
        celdas_sobreescritas = []
        
        for incidencia in self.incidencias:
            sobreescritas = self._aplicar_incidencia(matriz_final, incidencia)
            celdas_sobreescritas.extend(sobreescritas)
        
        # Detectar huecos de cobertura creados por el overlay
        huecos_cobertura = self._detectar_huecos_cobertura(matriz_final)
        
        logger.info(
            f"Overlay completado: {len(celdas_sobreescritas)} celdas sobreescritas, "
            f"{len(huecos_cobertura)} huecos de cobertura"
        )
        
        return ResultadoOverlay(
            matriz_final=matriz_final,
            celdas_sobreescritas=celdas_sobreescritas,
            huecos_cobertura=huecos_cobertura,
        )
    
    def _aplicar_incidencia(
        self, matriz: MatrizPlanificacion, incidencia: Incidencia
    ) -> list:
        """Aplica una sola incidencia y devuelve la lista de celdas sobreescritas."""
        sobreescritas = []
        
        fecha_actual = incidencia.fecha_inicio
        while fecha_actual <= incidencia.fecha_fin:
            celda = matriz.obtener_celda(incidencia.enfermera_id, fecha_actual)
            
            if celda:
                registro = self._sobrescribir_celda(celda, incidencia)
                if registro:
                    sobreescritas.append(registro)
            
            fecha_actual += timedelta(days=1)
        
        return sobreescritas
    
    def _sobrescribir_celda(
        self, celda: CeldaPlanificacion, incidencia: Incidencia
    ) -> dict:
        """
        Sobrescribe una celda según el tipo de incidencia.
        Devuelve un dict con la información de la sobreescritura.
        """
        # Registrar estado original
        turno_original_id = celda.turno.id if celda.turno else None
        horas_originales = celda.turno.duracion_horas if celda.turno else 0.0
        tipo_original = celda.tipo_celda
        
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
            # Formación mantiene el turno si existe (la enfermera podría estar trabajando)
            celda.tipo_celda = TipoCelda.FORMACION
            celda.es_modificable = False
            celda.observaciones = 'Formación'
            
        elif incidencia.tipo == TipoIncidencia.LIBRANZA_BLOQUEADA:
            celda.tipo_celda = TipoCelda.LIBRE
            celda.turno = None
            celda.es_modificable = False
            celda.observaciones = 'Libranza bloqueada'
            
        elif incidencia.tipo == TipoIncidencia.ASIGNACION_FIJA:
            if incidencia.turno_fijo:
                celda.turno = incidencia.turno_fijo
                celda.tipo_celda = TipoCelda.ASIGNACION_FIJA
                celda.es_modificable = False
                celda.observaciones = 'Asignación fija'
            else:
                # Sin turno fijo, tratar como día libre bloqueado
                celda.tipo_celda = TipoCelda.LIBRE
                celda.turno = None
                celda.es_modificable = False
                celda.observaciones = 'Asignación fija (sin turno)'
        
        # Calcular horas perdidas
        horas_nuevas = celda.turno.duracion_horas if celda.turno else 0.0
        horas_perdidas = horas_originales - horas_nuevas
        
        return {
            'enfermera_id': celda.enfermera_id,
            'enfermera_nombre': celda.enfermera_nombre,
            'fecha': celda.fecha.isoformat(),
            'turno_original_id': turno_original_id,
            'tipo_celda_original': tipo_original.value if hasattr(tipo_original, 'value') else tipo_original,
            'tipo_incidencia': incidencia.tipo.value if hasattr(incidencia.tipo, 'value') else incidencia.tipo,
            'horas_perdidas': horas_perdidas,
        }
    
    def _detectar_huecos_cobertura(self, matriz: MatrizPlanificacion) -> list:
        """
        Detecta fechas/turnos donde el overlay creó un déficit de cobertura
        respecto a la cobertura mínima configurada.
        """
        if not self.cobertura_minima:
            return []
        
        huecos = []
        
        for fecha in matriz.fechas:
            # Contar personal asignado por turno en esta fecha
            celdas_fecha = matriz.obtener_celdas_fecha(fecha)
            conteo_por_turno = {}
            
            for enf_id, celda in celdas_fecha.items():
                if celda.turno and celda.tipo_celda == TipoCelda.TURNO:
                    turno_id = celda.turno.id
                    conteo_por_turno[turno_id] = conteo_por_turno.get(turno_id, 0) + 1
                elif celda.turno and celda.tipo_celda == TipoCelda.ASIGNACION_FIJA:
                    # Las asignaciones fijas también cuentan para cobertura
                    turno_id = celda.turno.id
                    conteo_por_turno[turno_id] = conteo_por_turno.get(turno_id, 0) + 1
            
            # Comparar con cobertura mínima
            for turno_id, minimo_requerido in self.cobertura_minima.items():
                asignados = conteo_por_turno.get(turno_id, 0)
                deficit = minimo_requerido - asignados
                
                if deficit > 0:
                    huecos.append({
                        'fecha': fecha.isoformat(),
                        'turno_id': turno_id,
                        'deficit': deficit,
                        'asignados': asignados,
                        'requeridos': minimo_requerido,
                    })
        
        return huecos

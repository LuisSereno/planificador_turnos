# -*- coding: utf-8 -*-
"""
Ajustador de horas basado en contrato.
Valida y ajusta la rotación base para que las horas generadas se aproximen
a las horas objetivo contractuales (anuales/mensuales/semanales).
"""
import logging
from collections import Counter
from typing import Dict, List, Tuple

from ..dominio.dtos import (
    MatrizPlanificacion,
    CeldaPlanificacion,
    TipoCelda,
    TurnoInfo,
)

logger = logging.getLogger(__name__)


class AjustadorHoras:
    """
    Ajusta la matriz de rotación base para aproximar las horas contractuales.
    
    Después de la rotación base determinista (Phase 1), este módulo compara
    las horas generadas por enfermera con su objetivo (ContratoEnfermera).
    Si la desviación supera la tolerancia, realiza ajustes mínimos:
    - Exceso de horas: convierte turnos a LIBRE
    - Déficit de horas: convierte LIBRE a turnos
    """
    
    def __init__(
        self,
        matriz: MatrizPlanificacion,
        horas_objetivo: Dict[int, float],
        turnos_info: Dict[int, TurnoInfo],
        tolerancia_horas: float = 16.0,
        max_celdas_por_enfermera: int = 1,
    ):
        self.matriz = matriz
        self.horas_objetivo = horas_objetivo
        self.turnos_info = turnos_info
        self.tolerancia_horas = tolerancia_horas
        self.max_celdas = max_celdas_por_enfermera
    
    def ajustar(self) -> MatrizPlanificacion:
        """
        Ajusta las horas de cada enfermera modificando celdas de la matriz.
        
        Returns:
            Matriz ajustada (misma referencia, mutada in-place)
        """
        logger.info("Ajustando horas por contrato...")
        
        total_ajustes = 0
        
        for enfermera_id, enfermera_nombre in self.matriz.enfermeras.items():
            objetivo = self.horas_objetivo.get(enfermera_id)
            if objetivo is None or objetivo <= 0:
                continue
            
            celdas = self.matriz.obtener_celdas_enfermera(enfermera_id)
            if not celdas:
                continue
            
            # Calcular horas actuales
            horas_actuales = self._sumar_horas(celdas)
            delta = horas_actuales - objetivo
            
            if abs(delta) <= self.tolerancia_horas:
                continue
            
            logger.info(
                f"Enfermera {enfermera_nombre}: horas={horas_actuales:.1f}, "
                f"objetivo={objetivo:.1f}, delta={delta:+.1f}"
            )
            
            if delta > 0:
                # Exceso: quitar turnos (convertir a LIBRE)
                celdas_ajustadas = self._quitar_turnos(celdas, delta)
            else:
                # Déficit: añadir turnos (convertir LIBRE a turno)
                celdas_ajustadas = self._anadir_turnos(celdas, abs(delta), enfermera_id)
            
            total_ajustes += celdas_ajustadas
        
        logger.info(f"Ajuste de horas: {total_ajustes} celdas modificadas")
        return self.matriz
    
    def _sumar_horas(self, celdas: dict) -> float:
        """Suma las horas asignadas de un conjunto de celdas."""
        total = 0.0
        for celda in celdas.values():
            if celda.tipo_celda == TipoCelda.TURNO and celda.turno:
                total += celda.turno.duracion_horas
        return total
    
    def _quitar_turnos(self, celdas: dict, horas_a_quitar: float) -> int:
        """
        Convierte turnos a LIBRE hasta reducir el exceso de horas.
        Prioriza celdas adyacentes a días libres para minimizar ruptura del patrón.
        """
        # Ordenar celdas por fecha
        celdas_ordenadas = sorted(celdas.values(), key=lambda c: c.fecha)
        
        # Candidatos: celdas de turno que son modificables
        candidatos = [
            c for c in celdas_ordenadas
            if c.tipo_celda == TipoCelda.TURNO and c.turno and c.es_modificable
        ]
        
        if not candidatos:
            return 0
        
        # Puntuar cada candidato: preferir los adyacentes a LIBRE
        candidatos_puntuados = []
        fechas_turno = {c.fecha for c in candidatos}
        fechas_libre = {
            c.fecha for c in celdas_ordenadas
            if c.tipo_celda == TipoCelda.LIBRE or (c.turno is None and c.tipo_celda == TipoCelda.TURNO)
        }
        
        from datetime import timedelta
        for c in candidatos:
            # Puntuación: número de vecinos que son LIBRE (más = mejor candidato para quitar)
            vecinos_libre = 0
            for delta_dias in [-1, 1]:
                fecha_vecina = c.fecha + timedelta(days=delta_dias)
                if fecha_vecina in fechas_libre:
                    vecinos_libre += 1
            candidatos_puntuados.append((vecinos_libre, c))
        
        # Ordenar: más vecinos libres primero
        candidatos_puntuados.sort(key=lambda x: -x[0])
        
        horas_quitadas = 0.0
        celdas_ajustadas = 0
        
        for _, celda in candidatos_puntuados:
            if horas_quitadas >= horas_a_quitar:
                break
            if celdas_ajustadas >= self.max_celdas:
                break
            
            horas_quitadas += celda.turno.duracion_horas
            celda.turno = None
            celda.tipo_celda = TipoCelda.LIBRE
            celdas_ajustadas += 1
        
        return celdas_ajustadas
    
    def _anadir_turnos(self, celdas: dict, horas_a_anadir: float, enfermera_id: int) -> int:
        """
        Convierte LIBRE a turnos hasta cubrir el déficit de horas.
        Usa el tipo de turno más común en la rotación de la enfermera.
        """
        # Encontrar el turno más común de esta enfermera
        turno_mas_comun = self._turno_mas_comun(celdas)
        if not turno_mas_comun:
            # Fallback: usar el primer turno disponible
            if self.turnos_info:
                turno_mas_comun = next(iter(self.turnos_info.values()))
            else:
                return 0
        
        # Ordenar celdas por fecha
        celdas_ordenadas = sorted(celdas.values(), key=lambda c: c.fecha)
        
        # Candidatos: celdas LIBRE que son modificables
        candidatos = [
            c for c in celdas_ordenadas
            if (c.tipo_celda == TipoCelda.LIBRE or 
                (c.turno is None and c.tipo_celda == TipoCelda.TURNO))
            and c.es_modificable
        ]
        
        if not candidatos:
            return 0
        
        # Puntuar: preferir celdas adyacentes a turnos (para mantener bloques de trabajo)
        from datetime import timedelta
        fechas_turno = {
            c.fecha for c in celdas_ordenadas
            if c.tipo_celda == TipoCelda.TURNO and c.turno
        }
        
        candidatos_puntuados = []
        for c in candidatos:
            vecinos_turno = 0
            for delta_dias in [-1, 1]:
                fecha_vecina = c.fecha + timedelta(days=delta_dias)
                if fecha_vecina in fechas_turno:
                    vecinos_turno += 1
            candidatos_puntuados.append((vecinos_turno, c))
        
        # Ordenar: más vecinos turno primero
        candidatos_puntuados.sort(key=lambda x: -x[0])
        
        horas_anadidas = 0.0
        celdas_ajustadas = 0
        
        for _, celda in candidatos_puntuados:
            if horas_anadidas >= horas_a_anadir:
                break
            if celdas_ajustadas >= self.max_celdas:
                break
            
            celda.turno = turno_mas_comun
            celda.tipo_celda = TipoCelda.TURNO
            horas_anadidas += turno_mas_comun.duracion_horas
            celdas_ajustadas += 1
        
        return celdas_ajustadas
    
    def _turno_mas_comun(self, celdas: dict) -> TurnoInfo:
        """Encuentra el tipo de turno más frecuente en las celdas de una enfermera."""
        contador = Counter()
        for celda in celdas.values():
            if celda.tipo_celda == TipoCelda.TURNO and celda.turno:
                contador[celda.turno.id] = contador.get(celda.turno.id, 0) + 1
        
        if not contador:
            return None
        
        turno_id_mas_comun = max(contador, key=contador.get)
        
        # Buscar el TurnoInfo completo
        for celda in celdas.values():
            if celda.turno and celda.turno.id == turno_id_mas_comun:
                return celda.turno
        
        return None

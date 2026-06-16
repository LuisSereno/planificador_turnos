# -*- coding: utf-8 -*-
"""
Analizador de cobertura y desviaciones.
Calcula métricas de la matriz: horas por enfermera, cobertura por turno, desviaciones.
"""
import logging
from datetime import date
from typing import Dict, List
from collections import defaultdict

from ..dominio.dtos import (
    MatrizPlanificacion,
    BalanceEnfermera,
    TipoCelda,
    TurnoInfo,
)

logger = logging.getLogger(__name__)


class AnalizadorCobertura:
    """
    Analiza la matriz de planificación para identificar:
    - Horas asignadas por enfermera
    - Cobertura por turno y fecha
    - Desviaciones respecto a objetivos
    - Conflictos de cobertura
    """
    
    def __init__(
        self,
        matriz: MatrizPlanificacion,
        horas_objetivo_enfermeras: Dict[int, float],  # enfermera_id -> horas_mes_objetivo
        cobertura_minima_turnos: Dict[int, int] = None,  # turno_id -> mínimo enfermeras
        balances_historicos: Dict[int, dict] = None,  # enfermera_id -> historical data
        max_consecutivos: int = 6,
        max_noches_consecutivas: int = 3,
    ):
        self.matriz = matriz
        self.horas_objetivo = horas_objetivo_enfermeras
        self.cobertura_minima = cobertura_minima_turnos or {}
        self.balances_historicos = balances_historicos or {}
        self.max_consecutivos = max_consecutivos
        self.max_noches_consecutivas = max_noches_consecutivas
        
    def analizar(self) -> Dict:
        """
        Realiza el análisis completo de la matriz.
        
        Returns:
            Dict con:
            - 'balances': Dict[enfermera_id, BalanceEnfermera]
            - 'cobertura_turnos': Dict[fecha, Dict[turno_id, count]]
            - 'conflictos': List[str]
            - 'tiene_conflictos': bool
        """
        logger.info("Analizando cobertura y desviaciones")
        
        balances = self._calcular_balances()
        cobertura = self._calcular_cobertura()
        conflictos = self._detectar_conflictos(cobertura)
        conflictos.extend(self._detectar_violaciones_consecutivos())
        conflictos.extend(self._detectar_violaciones_noches_consecutivas())
        
        resultado = {
            'balances': balances,
            'cobertura_turnos': cobertura,
            'conflictos': conflictos,
            'tiene_conflictos': len(conflictos) > 0,
        }
        
        logger.info(f"Análisis completado: {len(conflictos)} conflictos detectados")
        return resultado
    
    def _calcular_balances(self) -> Dict[int, BalanceEnfermera]:
        """Calcula el balance de horas y carga para cada enfermera"""
        balances = {}
        
        for enfermera_id, enfermera_nombre in self.matriz.enfermeras.items():
            celdas = self.matriz.obtener_celdas_enfermera(enfermera_id)
            
            horas_asignadas = 0.0
            turnos_asignados = 0
            noches_asignadas = 0
            fines_semana_asignados = 0
            
            for celda in celdas.values():
                # Solo contar celdas que son turnos reales (no incidencias)
                if celda.tipo_celda == TipoCelda.TURNO and celda.turno:
                    horas_asignadas += celda.turno.duracion_horas
                    turnos_asignados += 1
                    
                    if celda.es_noche:
                        noches_asignadas += 1
                    
                    if celda.es_fin_de_semana:
                        fines_semana_asignados += 1
            
            horas_objetivo = self.horas_objetivo.get(enfermera_id, 0.0)
            desviacion = horas_asignadas - horas_objetivo
            
            # Incorporar acumulados históricos
            hist = self.balances_historicos.get(enfermera_id, {})
            horas_acumuladas_previas = hist.get('horas_acumuladas_previas', 0.0)
            noches_acumuladas = hist.get('noches_acumuladas', 0)
            fines_semana_acumulados = hist.get('fines_semana_acumulados', 0)
            festivos_acumulados = hist.get('festivos_acumulados', 0)
            
            balances[enfermera_id] = BalanceEnfermera(
                enfermera_id=enfermera_id,
                enfermera_nombre=enfermera_nombre,
                horas_asignadas=horas_asignadas,
                horas_objetivo=horas_objetivo,
                desviacion_horas=desviacion,
                turnos_asignados=turnos_asignados,
                noches_asignadas=noches_asignadas,
                fines_semana_asignados=fines_semana_asignados,
                horas_acumuladas_previas=horas_acumuladas_previas,
                noches_acumuladas=noches_acumuladas,
                fines_semana_acumulados=fines_semana_acumulados,
                festivos_acumulados=festivos_acumulados,
            )
        
        return balances
    
    def _calcular_cobertura(self) -> Dict[date, Dict[int, int]]:
        """Calcula cuántas enfermeras hay asignadas a cada turno por fecha"""
        cobertura = defaultdict(lambda: defaultdict(int))
        
        for fecha in self.matriz.fechas:
            celdas_fecha = self.matriz.obtener_celdas_fecha(fecha)
            
            for celda in celdas_fecha.values():
                if celda.tipo_celda == TipoCelda.TURNO and celda.turno:
                    cobertura[fecha][celda.turno.id] += 1
        
        return dict(cobertura)
    
    def _detectar_conflictos(self, cobertura: Dict) -> List[str]:
        """Detecta conflictos de cobertura mínima.
        
        Itera sobre TODAS las fechas en la matriz, no solo las que tienen
        asignaciones. Si una fecha no está en cobertura, significa que
        tiene 0 enfermeras en todos los turnos.
        """
        conflictos = []
        
        # Iterar sobre todas las fechas en la matriz
        for fecha in self.matriz.fechas:
            turnos_count = cobertura.get(fecha, {})
            
            for turno_id, minimo in self.cobertura_minima.items():
                enfermeras_asignadas = turnos_count.get(turno_id, 0)
                
                if enfermeras_asignadas < minimo:
                    conflictos.append(
                        f"Fecha {fecha}, turno {turno_id}: "
                        f"{enfermeras_asignadas} enfermeras (mínimo {minimo})"
                    )
        
        return conflictos

    def _detectar_violaciones_consecutivos(self) -> List[str]:
        """Detecta enfermeras que exceden el maximo de turnos consecutivos."""
        conflictos = []

        for enf_id, celdas_enfermera in self.matriz.celdas.items():
            fechas_ordenadas = sorted(celdas_enfermera.keys())
            contador = 0

            for fecha in fechas_ordenadas:
                celda = celdas_enfermera[fecha]
                if celda.tipo_celda == TipoCelda.TURNO and celda.turno and not celda.es_libre:
                    contador += 1
                    if contador > self.max_consecutivos:
                        conflictos.append(
                            f"Enfermera {enf_id}, fecha {fecha}: "
                            f"{contador} turnos consecutivos "
                            f"(maximo {self.max_consecutivos})"
                        )
                else:
                    contador = 0

        return conflictos

    def _detectar_violaciones_noches_consecutivas(self) -> List[str]:
        """Detecta enfermeras que exceden el maximo de noches consecutivas."""
        conflictos = []

        for enf_id, celdas_enfermera in self.matriz.celdas.items():
            fechas_ordenadas = sorted(celdas_enfermera.keys())
            contador_noches = 0

            for fecha in fechas_ordenadas:
                celda = celdas_enfermera[fecha]
                if celda.es_noche:
                    contador_noches += 1
                    if contador_noches > self.max_noches_consecutivas:
                        conflictos.append(
                            f"Enfermera {enf_id}, fecha {fecha}: "
                            f"{contador_noches} noches consecutivas "
                            f"(maximo {self.max_noches_consecutivas})"
                        )
                else:
                    contador_noches = 0

        return conflictos

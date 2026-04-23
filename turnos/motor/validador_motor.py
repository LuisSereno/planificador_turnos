# -*- coding: utf-8 -*-
"""
Validador final del motor de planificación.
Verifica que la matriz reparada cumple todas las restricciones y persiste balances.
"""
import logging
from datetime import date
from typing import Dict, List, Tuple
from collections import defaultdict

from ..dominio.dtos import (
    MatrizPlanificacion,
    CeldaPlanificacion,
    TipoCelda,
    BalanceEnfermera,
    ResultadoPlanificacion,
    TurnoInfo,
)

logger = logging.getLogger(__name__)


class ValidadorMotor:
    """
    Valida la matriz de planificación final después de la reparación CP-SAT.
    
    Verifica:
    1. Restricciones duras (no deben haber violaciones)
    2. Calidad de la solución (métricas de equidad)
    3. Integridad de datos (celdas completas, tipos correctos)
    4. Persiste balances históricos para planificación futura
    """
    
    def __init__(
        self,
        matriz: MatrizPlanificacion,
        turnos_info: Dict[int, TurnoInfo],
        configuracion: dict,
    ):
        self.matriz = matriz
        self.turnos_info = turnos_info
        self.configuracion = configuracion
        self.violaciones = []
        self.warnings = []
        
    def validar(self) -> ResultadoPlanificacion:
        """
        Ejecuta todas las validaciones y genera el resultado final.
        
        Returns:
            ResultadoPlanificacion con métricas y validaciones
        """
        logger.info("Iniciando validación final de la planilla...")
        
        # 1. Validar restricciones duras
        self._validar_restricciones_duras()
        
        # 2. Validar calidad de la solución
        self._validar_calidad_solucion()
        
        # 3. Validar integridad de datos
        self._validar_integridad_datos()
        
        # 4. Calcular balances finales
        balances = self._calcular_balances_finales()
        
        # 5. Generar resultado
        resultado = ResultadoPlanificacion(
            matriz=self.matriz,
            exito=len(self.violaciones) == 0,
            violaciones=self.violaciones,
            warnings=self.warnings,
            balances=balances,
        )
        
        if resultado.exito:
            logger.info("✅ Validación exitosa: planilla cumple todas las restricciones")
        else:
            logger.warning(
                f"⚠️ Validación con {len(self.violaciones)} violaciones"
            )
        
        return resultado
    
    def _validar_restricciones_duras(self):
        """Verifica que no haya violaciones de restricciones duras"""
        
        # Validar un turno por día
        self._validar_un_turno_por_dia()
        
        # Validar turnos consecutivos máximos
        self._validar_turnos_consecutivos()
        
        # Validar noches consecutivas máximas
        self._validar_noches_consecutivas()
        
        # Validar cobertura mínima
        self._validar_cobertura_minima()
    
    def _validar_un_turno_por_dia(self):
        """Cada enfermera debe tener exactamente un turno o día libre por día"""
        for enf_id, celdas_enfermera in self.matriz.celdas.items():
            for fecha, celda in celdas_enfermera.items():
                if celda.turno_id is None and not celda.es_libre and celda.tipo_celda == TipoCelda.TURNO:
                    self.violaciones.append({
                        'tipo': 'TURNO_POR_DIA',
                        'enfermera_id': enf_id,
                        'fecha': fecha.isoformat(),
                        'descripcion': f'Enfermera {enf_id} no tiene asignación para {fecha}',
                    })
    
    def _validar_turnos_consecutivos(self):
        """Valida máximo de turnos consecutivos sin descanso"""
        max_consecutivos = self.configuracion.get('TURNO_CONSECUTIVOS_MAX', 6)
        
        for enf_id, celdas_enfermera in self.matriz.celdas.items():
            fechas_ordenadas = sorted(celdas_enfermera.keys())
            contador = 0
            
            for fecha in fechas_ordenadas:
                celda = celdas_enfermera[fecha]
                
                if celda.tipo_celda == TipoCelda.TURNO or (celda.turno_id and not celda.es_libre):
                    contador += 1
                    if contador > max_consecutivos:
                        self.violaciones.append({
                            'tipo': 'TURNO_CONSECUTIVOS_MAX',
                            'enfermera_id': enf_id,
                            'fecha': fecha.isoformat(),
                            'descripcion': f'Enfermera {enf_id} excede {max_consecutivos} turnos consecutivos ({contador})',
                        })
                else:
                    contador = 0  # Reiniciar contador en día libre
    
    def _validar_noches_consecutivas(self):
        """Valida máximo de noches consecutivas"""
        max_noches = self.configuracion.get('NOCHES_CONSECUTIVAS_MAX', 3)
        
        for enf_id, celdas_enfermera in self.matriz.celdas.items():
            fechas_ordenadas = sorted(celdas_enfermera.keys())
            contador_noches = 0
            
            for fecha in fechas_ordenadas:
                celda = celdas_enfermera[fecha]
                
                if celda.turno_id and self._es_turno_nocturno(celda.turno_id):
                    contador_noches += 1
                    if contador_noches > max_noches:
                        self.violaciones.append({
                            'tipo': 'NOCHES_CONSECUTIVAS_MAX',
                            'enfermera_id': enf_id,
                            'fecha': fecha.isoformat(),
                            'descripcion': f'Enfermera {enf_id} excede {max_noches} noches consecutivas ({contador_noches})',
                        })
                else:
                    contador_noches = 0
    
    def _validar_cobertura_minima(self):
        """Valida cobertura mínima por turno"""
        cobertura_minima = self.configuracion.get('COBERTURA_MINIMA', {})
        
        # Agrupar por fecha y turno
        cobertura = defaultdict(lambda: defaultdict(int))
        for enf_id, celdas_enfermera in self.matriz.celdas.items():
            for fecha, celda in celdas_enfermera.items():
                if celda.turno_id and not celda.es_libre:
                    cobertura[fecha][celda.turno_id] += 1
        
        # Verificar mínimos
        for fecha, turnos_count in cobertura.items():
            for turno_id, minimo in cobertura_minima.items():
                if turno_id in turnos_count and turnos_count[turno_id] < minimo:
                    self.violaciones.append({
                        'tipo': 'COBERTURA_MINIMA',
                        'turno_id': turno_id,
                        'fecha': fecha.isoformat(),
                        'descripcion': f'Turno {turno_id} en {fecha} tiene {turnos_count[turno_id]} enfermeras (mínimo: {minimo})',
                    })
    
    def _validar_calidad_solucion(self):
        """Verifica métricas de calidad (equidad)"""
        
        # Calcular estadísticas de horas
        horas_por_enfermera = []
        noches_por_enfermera = []
        findes_por_enfermera = []
        
        for enf_id, celdas_enfermera in self.matriz.celdas.items():
            horas = sum(
                self._obtener_duracion_turno(celda.turno_id)
                for celda in celdas_enfermera.values()
                if celda.turno_id
            )
            horas_por_enfermera.append(horas)
            
            noches = sum(
                1 for celda in celdas_enfermera.values()
                if celda.turno_id and self._es_turno_nocturno(celda.turno_id)
            )
            noches_por_enfermera.append(noches)
            
            findes = sum(
                1 for celda in celdas_enfermera.values()
                if celda.es_fin_de_semana and celda.turno_id and not celda.es_libre
            )
            findes_por_enfermera.append(findes)
        
        # Verificar desviación de horas
        if horas_por_enfermera:
            media_horas = sum(horas_por_enfermera) / len(horas_por_enfermera)
            max_desviacion = max(abs(h - media_horas) for h in horas_por_enfermera)
            
            if max_desviacion > 10:  # Más de 10 horas de diferencia
                self.warnings.append(
                    f"Desviación alta en horas: {max_desviacion:.1f}h (media: {media_horas:.1f}h)"
                )
        
        # Verificar equidad de noches
        if noches_por_enfermera:
            diff_noches = max(noches_por_enfermera) - min(noches_por_enfermera)
            if diff_noches > 3:
                self.warnings.append(
                    f"Desbalance de noches: diferencia de {diff_noches} entre enfermeras"
                )
        
        # Verificar equidad de fines de semana
        if findes_por_enfermera:
            diff_findes = max(findes_por_enfermera) - min(findes_por_enfermera)
            if diff_findes > 2:
                self.warnings.append(
                    f"Desbalance de fines de semana: diferencia de {diff_findes}"
                )
    
    def _validar_integridad_datos(self):
        """Verifica que todas las celdas estén correctamente definidas"""
        
        for enf_id, celdas_enfermera in self.matriz.celdas.items():
            for fecha, celda in celdas_enfermera.items():
                # Verificar que tipo_celda es válido
                if celda.tipo_celda not in [tc.value for tc in TipoCelda]:
                    self.violaciones.append({
                        'tipo': 'TIPO_CELDA_INVALIDO',
                        'enfermera_id': enf_id,
                        'fecha': fecha.isoformat(),
                        'descripcion': f'Tipo de celda inválido: {celda.tipo_celda}',
                    })
                
                # Verificar que TURNOS tienen turno_id
                if celda.tipo_celda == TipoCelda.TURNO.value and not celda.turno_id:
                    self.violaciones.append({
                        'tipo': 'TURNO_SIN_ID',
                        'enfermera_id': enf_id,
                        'fecha': fecha.isoformat(),
                        'descripcion': f'Celda de turno sin turno_id',
                    })
    
    def _calcular_balances_finales(self) -> Dict[int, BalanceEnfermera]:
        """Calcula los balances finales de cada enfermera"""
        balances = {}
        
        for enf_id, celdas_enfermera in self.matriz.celdas.items():
            horas = 0.0
            noches = 0
            findes = 0
            festivos = 0
            
            for celda in celdas_enfermera.values():
                if celda.turno_id and not celda.es_libre:
                    horas += self._obtener_duracion_turno(celda.turno_id)
                    
                    if self._es_turno_nocturno(celda.turno_id):
                        noches += 1
                    
                    if celda.es_fin_de_semana:
                        findes += 1
                    
                    if celda.es_festivo:
                        festivos += 1
            
            balances[enf_id] = BalanceEnfermera(
                enfermera_id=enf_id,
                horas_asignadas=horas,
                turnos_asignados=sum(1 for c in celdas_enfermera.values() if c.turno_id),
                noches_asignadas=noches,
                fines_semana_asignados=findes,
                festivos_asignados=festivos,
            )
        
        logger.info(f"Balances calculados para {len(balances)} enfermeras")
        
        return balances
    
    def _es_turno_nocturno(self, turno_id: int) -> bool:
        """Determina si un turno es nocturno"""
        if turno_id in self.turnos_info:
            return self.turnos_info[turno_id].es_nocturno
        return False
    
    def _obtener_duracion_turno(self, turno_id: int) -> float:
        """Obtiene la duración de un turno"""
        if turno_id in self.turnos_info:
            return self.turnos_info[turno_id].duracion_horas
        return 0.0

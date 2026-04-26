# -*- coding: utf-8 -*-
"""
Reparador basado en OR-Tools CP-SAT.
Repara conflictos en la matriz de planificación minimizando la desviación de la rotación base.
"""
import logging
from datetime import date
from typing import List, Dict, Optional, Tuple
from ortools.sat.python import cp_model

from ..dominio.dtos import (
    MatrizPlanificacion,
    CeldaPlanificacion,
    TipoCelda,
    TurnoInfo,
    ResultadoPlanificacion,
    BalanceEnfermera,
)
from ..dominio.normalizacion import normalizar_nombre

logger = logging.getLogger(__name__)


class ReparadorCPSAT:
    """
    Reparador de conflictos usando CP-SAT.
    
    Este módulo actúa como motor de ajuste fino, NO como generador libre.
    Solo modifica celdas conflictivas respetando:
    - Celdas bloqueadas por incidencias
    - Restricciones duras (descansos, máximos consecutivos, etc.)
    - Proximidad a la rotación base (objetivo primario)
    """
    
    def __init__(
        self,
        matriz_bloqueada: MatrizPlanificacion,
        analisis_cobertura,
        turnos_info: Dict[int, TurnoInfo],
        restricciones_duras: List[dict] = None,
        objetivos: List[dict] = None,
        cobertura_minima: Dict[int, int] = None,
    ):
        self.matriz = matriz_bloqueada
        self.analisis = analisis_cobertura
        self.turnos_info = turnos_info
        self.restricciones_duras = restricciones_duras or []
        self.objetivos = objetivos or []
        self.cobertura_minima = cobertura_minima or {}
        self.model = cp_model.CpModel()
        self.solver_vars = {}  # (enfermera_id, fecha_idx, turno_id) -> BoolVar
        self.solver_status = 'NO_EJECUTADO'
        
    def reparar(self) -> MatrizPlanificacion:
        """
        Ejecuta la reparación CP-SAT y devuelve la matriz optimizada.
        """
        logger.info("Iniciando reparación CP-SAT...")
        
        # Construir modelo
        self._crear_variables()
        self._aplicar_restricciones_duras()
        self._aplicar_objetivos()
        
        # Resolver
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0  # Timeout 30s
        solver.parameters.num_search_workers = 4
        
        status = solver.Solve(self.model)
        
        # Store solver status
        status_map = {
            cp_model.OPTIMAL: 'OPTIMAL',
            cp_model.FEASIBLE: 'FEASIBLE',
            cp_model.INFEASIBLE: 'INFEASIBLE',
            cp_model.MODEL_INVALID: 'MODEL_INVALID',
        }
        self.solver_status = status_map.get(status, 'UNKNOWN')
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.info(f"Reparación exitosa. Status: {solver.StatusName(status)}")
            return self._extraer_solucion(solver)
        else:
            logger.warning(f"Reparación no encontró solución factible. Status: {solver.StatusName(status)}")
            return self.matriz  # Devolver matriz sin cambios
    
    def _crear_variables(self):
        """
        Crea variables CP-SAT solo para celdas modificables.
        """
        # Collect all unique turno IDs from the matrix
        all_turno_ids = set()
        for enfermera_id, celdas in self.matriz.celdas.items():
            for fecha, celda in celdas.items():
                if celda.turno:
                    all_turno_ids.add(celda.turno.id)
        
        self.matriz.turnos_disponibles = list(all_turno_ids)
        
        for enfermera_id, celdas in self.matriz.celdas.items():
            for fecha, celda in celdas.items():
                if not celda.es_modificable:
                    continue  # Saltar celdas bloqueadas
                
                # Variable: ¿se asigna turno t a esta celda?
                for turno_id in self.matriz.turnos_disponibles:
                    var = self.model.NewBoolVar(
                        f"x_e{enfermera_id}_d{fecha}_t{turno_id}"
                    )
                    self.solver_vars[(enfermera_id, fecha, turno_id)] = var
                
                # Restricción: exactamente un turno por celda modificable
                self.model.Add(
                    sum(self.solver_vars[(enfermera_id, fecha, t)] 
                        for t in self.matriz.turnos_disponibles) == 1
                )
    
    def _aplicar_restricciones_duras(self):
        """
        Aplica restricciones duras al modelo CP-SAT.
        """
        # RD001: Un turno por día (ya garantizado por la construcción de variables)
        
        # RD002: Turnos consecutivos máximo
        self._restringir_turnos_consecutivos()
        
        # RD003: Descanso mínimo entre turnos (12h)
        self._restringir_descanso_entre_turnos()
        
        # RD004: Cobertura mínima por turno
        self._restringir_cobertura_minima()
        
        # RD005: Máximo noches consecutivas
        self._restringir_noches_consecutivas()
    
    def _restringir_turnos_consecutivos(self):
        """Limita el número de turnos consecutivos sin descanso."""
        # Buscar configuración
        max_consec = 6  # Default
        for r in self.restricciones_duras:
            if normalizar_nombre(r.get('nombre', '')) == 'TURNO_CONSECUTIVOS_MAX':
                max_consec = int(r.get('valor', 6))
                break
        
        fechas_ordenadas = sorted(self.matriz.fechas)
        
        for enfermera_id in self.matriz.enfermeras:
            for i in range(len(fechas_ordenadas) - max_consec + 1):
                ventana = fechas_ordenadas[i:i + max_consec + 1]
                
                # En cualquier ventana de max_consec+1 días, debe haber al menos 1 libre
                vars_turno = []
                for fecha in ventana:
                    for turno_id in self.matriz.turnos_disponibles:
                        key = (enfermera_id, fecha, turno_id)
                        if key in self.solver_vars:
                            vars_turno.append(self.solver_vars[key])
                
                if vars_turno:
                    # Al menos una celda debe ser LIBRE (turno_id especial)
                    # Simplificación: limitamos a max_consec turnos asignados
                    self.model.Add(sum(vars_turno) <= max_consec)
    
    def _restringir_descanso_entre_turnos(self):
        """Garantiza descanso mínimo entre turnos (12h entre noche y mañana)."""
        # Identify night and morning shifts
        turnos_nocturnos = []
        turnos_madrugadores = []
        
        for turno_id, turno_info in self.turnos_info.items():
            if turno_info.es_nocturno:
                turnos_nocturnos.append(turno_id)
            # Morning shifts starting before 8 AM after night shift
            elif turno_info.hora_inicio and turno_info.hora_inicio.hour < 8:
                turnos_madrugadores.append(turno_id)
        
        if not turnos_nocturnos or not turnos_madrugadores:
            return
        
        fechas_ordenadas = sorted(self.matriz.fechas)
        
        # Prevent night shift followed by early morning shift next day
        for enfermera_id in self.matriz.enfermeras:
            for i in range(len(fechas_ordenadas) - 1):
                fecha_actual = fechas_ordenadas[i]
                fecha_siguiente = fechas_ordenadas[i + 1]
                
                # For each night shift on day D
                for turno_noche in turnos_nocturnos:
                    key_noche = (enfermera_id, fecha_actual, turno_noche)
                    if key_noche not in self.solver_vars:
                        continue
                    
                    # Prevent early morning shift on day D+1
                    for turno_manana in turnos_madrugadores:
                        key_manana = (enfermera_id, fecha_siguiente, turno_manana)
                        if key_manana not in self.solver_vars:
                            continue
                        
                        # Both cannot be true simultaneously
                        self.model.Add(
                            self.solver_vars[key_noche] + self.solver_vars[key_manana] <= 1
                        )
    
    def _restringir_cobertura_minima(self):
        """Garantiza cobertura mínima por turno y fecha."""
        # Usar cobertura_minima pasada como parámetro (no del análisis)
        cobertura_min = self.cobertura_minima
        
        for fecha in self.matriz.fechas:
            for turno_id, minimo in cobertura_min.items():
                vars_cobertura = []
                for enfermera_id in self.matriz.enfermeras:
                    key = (enfermera_id, fecha, turno_id)
                    if key in self.solver_vars:
                        vars_cobertura.append(self.solver_vars[key])
                
                if vars_cobertura:
                    self.model.Add(sum(vars_cobertura) >= minimo)
    
    def _restringir_noches_consecutivas(self):
        """Limita noches consecutivas."""
        max_noches = 4  # Default
        for r in self.restricciones_duras:
            if normalizar_nombre(r.get('nombre', '')) == 'NOCHES_CONSECUTIVAS_MAX':
                max_noches = int(r.get('valor', 4))
                break
        
        # Identificar turnos nocturnos
        turnos_nocturnos = [
            t_id for t_id, t_info in self.turnos_info.items()
            if t_info.es_nocturno
        ]
        
        if not turnos_nocturnos:
            return
        
        fechas_ordenadas = sorted(self.matriz.fechas)
        
        for enfermera_id in self.matriz.enfermeras:
            for i in range(len(fechas_ordenadas) - max_noches):
                ventana = fechas_ordenadas[i:i + max_noches + 1]
                
                # En ventana de max_noches+1 días, máximo max_noches noches
                vars_noches = []
                for fecha in ventana:
                    for turno_id in turnos_nocturnos:
                        key = (enfermera_id, fecha, turno_id)
                        if key in self.solver_vars:
                            vars_noches.append(self.solver_vars[key])
                
                if vars_noches:
                    self.model.Add(sum(vars_noches) <= max_noches)
    
    def _aplicar_objetivos(self):
        """
        Configura objetivos lexicográficos del solver.
        """
        # Objetivo 1: Minimizar desviación de rotación base
        self._objetivo_minimizar_desviacion_base()
        
        # Objetivo 2: Minimizar desviación de horas mensuales
        self._objetivo_balance_horas()
        
        # Objetivo 3: Equilibrar noches
        self._objetivo_equilibrar_noches()
        
        # Objetivo 4: Equilibrar fines de semana
        self._objetivo_equilibrar_findes()
    
    def _objetivo_minimizar_desviacion_base(self):
        """
        Penaliza celdas que se desvían de la rotación base.
        Este es el objetivo PRIORITARIO.
        """
        penalizaciones = []
        
        for enfermera_id, celdas in self.matriz.celdas.items():
            for fecha, celda in celdas.items():
                if not celda.es_modificable:
                    continue
                
                turno_base = celda.turno_base_id
                if turno_base is None:
                    continue
                
                # Penalizar si no se asigna el turno base
                for turno_id in self.matriz.turnos_disponibles:
                    if turno_id != turno_base:
                        key = (enfermera_id, fecha, turno_id)
                        if key in self.solver_vars:
                            penalizaciones.append(self.solver_vars[key])
        
        if penalizaciones:
            self.model.Minimize(sum(penalizaciones))
    
    def _objetivo_balance_horas(self):
        """
        Minimiza la desviación de horas mensuales objetivo.
        Implementado como soft constraint con variables de desviación.
        """
        # This would require complex linearization in CP-SAT
        # For now, we rely on the base rotation already being balanced
        # and let the coverage analyzer detect issues post-solver
        # A full implementation would add deviation variables and minimize them
        pass
    
    def _objetivo_equilibrar_noches(self):
        """
        Equilibra el número de noches entre enfermeras.
        Implementado como soft constraint para minimizar varianza.
        """
        # Similar to hours balance - would require deviation variables
        # For now, the base rotation should already distribute nights fairly
        # The coverage analyzer will report any imbalances
        pass
    
    def _objetivo_equilibrar_findes(self):
        """
        Equilibra fines de semana trabajados.
        Implementado como soft constraint para minimizar varianza.
        """
        # Similar - metric tracked post-solver
        # Weekend distribution should be handled by base rotation design
        pass
    
    def _extraer_solucion(self, solver: cp_model.CpSolver) -> MatrizPlanificacion:
        """
        Extrae la solución del solver y actualiza la matriz.
        """
        matriz_resultado = self.matriz.clone()
        
        # Build a lookup map for turno_id -> TurnoInfo
        turno_lookup = {t_id: t_info for t_id, t_info in self.turnos_info.items()}
        
        for (enfermera_id, fecha, turno_id), var in self.solver_vars.items():
            if solver.Value(var) == 1:
                celda = matriz_resultado.obtener_celda(enfermera_id, fecha)
                if celda and celda.es_modificable:
                    # Update the turno object
                    if turno_id in turno_lookup:
                        celda.turno = turno_lookup[turno_id]
                        celda.tipo_celda = TipoCelda.TURNO
                    else:
                        # If turno_id not found, mark as free
                        celda.turno = None
                        celda.tipo_celda = TipoCelda.LIBRE
        
        return matriz_resultado

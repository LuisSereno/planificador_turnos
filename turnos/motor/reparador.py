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
        horas_objetivo: Dict[int, float] = None,
    ):
        self.matriz = matriz_bloqueada
        self.analisis = analisis_cobertura
        self.turnos_info = turnos_info
        self.restricciones_duras = restricciones_duras or []
        self.objetivos = objetivos or []
        self.cobertura_minima = cobertura_minima or {}
        self.horas_objetivo = horas_objetivo or {}  # enfermera_id -> horas_mes_objetivo
        self.model = cp_model.CpModel()
        self.solver_vars = {}  # (enfermera_id, fecha_idx, turno_id) -> BoolVar
        self.solver_status = 'NO_EJECUTADO'
        
        # Sentinel para celdas LIBRE en el solver
        self.LIBRE_SENTINEL = '__LIBRE__'
        
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
        Incluye opción explícita de LIBRE para que una celda libre
        pueda seguir siendo libre o convertirse en un turno.
        
        turnos_disponibles se construye a partir de TODOS los turnos
        en turnos_info (configuración completa), no solo los presentes
        en la matriz base. Esto permite al solver usar cualquier turno
        válido para corregir cobertura.
        """
        # Usar TODOS los turnos de la configuración (turnos_info)
        all_turno_ids = set(self.turnos_info.keys())
        
        # Incluir LIBRE como opción válida en el solver
        self.matriz.turnos_disponibles = list(all_turno_ids) + [self.LIBRE_SENTINEL]
        
        for enfermera_id, celdas in self.matriz.celdas.items():
            for fecha, celda in celdas.items():
                if not celda.es_modificable:
                    continue  # Saltar celdas bloqueadas
                
                # Variable: ¿se asigna turno t (o LIBRE) a esta celda?
                for turno_id in self.matriz.turnos_disponibles:
                    var = self.model.NewBoolVar(
                        f"x_e{enfermera_id}_d{fecha}_t{turno_id}"
                    )
                    self.solver_vars[(enfermera_id, fecha, turno_id)] = var
                
                # Restricción: exactamente una opción por celda modificable
                # (puede ser un turno real o LIBRE)
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
        """Limita el número de turnos consecutivos sin descanso.
        
        Solo cuenta turnos REALES (no LIBRE). En cualquier ventana de
        max_consec+1 días, debe haber al menos 1 día LIBRE.
        
        Cuenta tanto celdas bloqueadas (ya asignadas) como variables del solver.
        """
        # Buscar configuración - soportar ambos campos: 'nombre' y 'tipo'
        max_consec = 6  # Default
        for r in self.restricciones_duras:
            nombre_raw = r.get('nombre', '') or r.get('tipo', '')
            if normalizar_nombre(nombre_raw) == 'TURNO_CONSECUTIVOS_MAX':
                max_consec = int(r.get('valor', 6))
                break
        
        # Identificar turnos reales (excluir LIBRE_SENTINEL)
        turnos_reales = [
            t_id for t_id in self.matriz.turnos_disponibles
            if t_id != self.LIBRE_SENTINEL
        ]
        
        if not turnos_reales:
            return
        
        fechas_ordenadas = sorted(self.matriz.fechas)
        
        for enfermera_id in self.matriz.enfermeras:
            for i in range(len(fechas_ordenadas) - max_consec + 1):
                ventana = fechas_ordenadas[i:i + max_consec + 1]
                
                # 1. Contar días BLOQUEADOS que ya son trabajo real
                bloqueados_trabajo = 0
                for fecha in ventana:
                    celda = self.matriz.obtener_celda(enfermera_id, fecha)
                    if celda and not celda.es_modificable:
                        if celda.turno and celda.turno.id in turnos_reales:
                            bloqueados_trabajo += 1
                
                # 2. Contar días MODIFICABLES que el solver puede asignar como trabajo
                vars_trabajo = []
                for fecha in ventana:
                    celda = self.matriz.obtener_celda(enfermera_id, fecha)
                    if celda and celda.es_modificable:
                        for turno_id in turnos_reales:
                            key = (enfermera_id, fecha, turno_id)
                            if key in self.solver_vars:
                                vars_trabajo.append(self.solver_vars[key])
                
                # 3. Restricción: bloqueados + solver <= max_consec
                # Equivalente: solver <= max_consec - bloqueados_trabajo
                limite_solver = max_consec - bloqueados_trabajo
                if limite_solver < 0:
                    # Ya se violó la restricción con celdas bloqueadas
                    logger.warning(
                        f"Enfermera {enfermera_id}: ventana {ventana[0]}-{ventana[-1]} "
                        f"ya tiene {bloqueados_trabajo} días de trabajo bloqueados "
                        f"(máximo permitido: {max_consec})"
                    )
                elif vars_trabajo:
                    self.model.Add(sum(vars_trabajo) <= limite_solver)
    
    def _restringir_descanso_entre_turnos(self):
        """Garantiza descanso mínimo entre turnos (12h entre noche y mañana).
        
        Considera tanto celdas bloqueadas como variables del solver para
        detectar transiciones prohibidas noche->manana en días consecutivos.
        """
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
                    # For each early morning shift on day D+1
                    for turno_manana in turnos_madrugadores:
                        key_noche = (enfermera_id, fecha_actual, turno_noche)
                        key_manana = (enfermera_id, fecha_siguiente, turno_manana)
                        
                        noche_en_solver = key_noche in self.solver_vars
                        manana_en_solver = key_manana in self.solver_vars
                        
                        if noche_en_solver and manana_en_solver:
                            # Ambos son modificables: el solver no puede activar los dos
                            self.model.Add(
                                self.solver_vars[key_noche] + self.solver_vars[key_manana] <= 1
                            )
                        elif noche_en_solver and not manana_en_solver:
                            # Noche es modificable, mañana está bloqueada
                            celda_manana = self.matriz.obtener_celda(enfermera_id, fecha_siguiente)
                            if celda_manana and not celda_manana.es_modificable:
                                if celda_manana.turno and celda_manana.turno.id == turno_manana:
                                    # Mañana está bloqueada como turno madrugador: prohibir noche
                                    self.model.Add(self.solver_vars[key_noche] == 0)
                        elif not noche_en_solver and manana_en_solver:
                            # Noche está bloqueada, mañana es modificable
                            celda_noche = self.matriz.obtener_celda(enfermera_id, fecha_actual)
                            if celda_noche and not celda_noche.es_modificable:
                                if celda_noche.turno and celda_noche.turno.id == turno_noche:
                                    # Noche está bloqueada como turno nocturno: prohibir mañana
                                    self.model.Add(self.solver_vars[key_manana] == 0)
                        # Si ambos están bloqueados, no hay variables que restringir
    
    def _restringir_cobertura_minima(self):
        """Garantiza cobertura mínima por turno y fecha.
        
        Cuenta tanto celdas bloqueadas (ya asignadas por rotación/incidencias)
        como celdas modificables (variables del solver). Solo exige al solver
        la diferencia que falta para alcanzar el mínimo.
        """
        cobertura_min = self.cobertura_minima
        
        for fecha in self.matriz.fechas:
            for turno_id, minimo in cobertura_min.items():
                # 1. Contar celdas BLOQUEADAS ya asignadas a este turno
                bloqueadas_count = 0
                for enfermera_id in self.matriz.enfermeras:
                    celda = self.matriz.obtener_celda(enfermera_id, fecha)
                    if celda and not celda.es_modificable:
                        if celda.turno and celda.turno.id == turno_id:
                            bloqueadas_count += 1
                
                # 2. Contar celdas MODIFICABLES que el solver puede asignar
                vars_modificables = []
                for enfermera_id in self.matriz.enfermeras:
                    key = (enfermera_id, fecha, turno_id)
                    if key in self.solver_vars:
                        vars_modificables.append(self.solver_vars[key])
                
                # 3. El solver debe cubrir lo que falta (mínimo 0)
                restante = max(0, minimo - bloqueadas_count)
                if restante > 0 and vars_modificables:
                    self.model.Add(sum(vars_modificables) >= restante)
                elif restante > 0 and not vars_modificables:
                    logger.warning(
                        f"Cobertura imposible: fecha {fecha}, turno {turno_id}, "
                        f"necesita {minimo}, bloqueadas={bloqueadas_count}, "
                        f"sin celdas modificables disponibles"
                    )
    
    def _restringir_noches_consecutivas(self):
        """Limita noches consecutivas.
        
        Cuenta tanto celdas bloqueadas (ya asignadas) como variables del solver.
        """
        # Soportar ambos campos: 'nombre' y 'tipo'
        max_noches = 4  # Default
        for r in self.restricciones_duras:
            nombre_raw = r.get('nombre', '') or r.get('tipo', '')
            if normalizar_nombre(nombre_raw) == 'NOCHES_CONSECUTIVAS_MAX':
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
                
                # 1. Contar noches BLOQUEADAS ya asignadas
                bloqueadas_noches = 0
                for fecha in ventana:
                    celda = self.matriz.obtener_celda(enfermera_id, fecha)
                    if celda and not celda.es_modificable:
                        if celda.turno and celda.turno.id in turnos_nocturnos:
                            bloqueadas_noches += 1
                
                # 2. Contar noches MODIFICABLES que el solver puede asignar
                vars_noches = []
                for fecha in ventana:
                    celda = self.matriz.obtener_celda(enfermera_id, fecha)
                    if celda and celda.es_modificable:
                        for turno_id in turnos_nocturnos:
                            key = (enfermera_id, fecha, turno_id)
                            if key in self.solver_vars:
                                vars_noches.append(self.solver_vars[key])
                
                # 3. Restricción: bloqueadas + solver <= max_noches
                limite_solver = max_noches - bloqueadas_noches
                if limite_solver < 0:
                    logger.warning(
                        f"Enfermera {enfermera_id}: ventana {ventana[0]}-{ventana[-1]} "
                        f"ya tiene {bloqueadas_noches} noches bloqueadas "
                        f"(máximo permitido: {max_noches})"
                    )
                elif vars_noches:
                    self.model.Add(sum(vars_noches) <= limite_solver)
    
    def _aplicar_objetivos(self):
        """
        Configura objetivo lexicográfico combinado para el solver.
        Construye una única función objetivo ponderada con:
        1. Minimizar desviación de rotación base (prioridad alta)
        2. Balance horario mensual
        3. Equilibrio de noches
        4. Equilibrio de fines de semana
        """
        penalizaciones = []
        
        # Objetivo 1: Minimizar desviación de rotación base (peso 100)
        penalizaciones_base = self._penalizar_desviacion_base()
        penalizaciones.extend([100 * p for p in penalizaciones_base])
        
        # Objetivo 2: Balance de horas mensuales (peso 10)
        penalizaciones_horas = self._penalizar_balance_horas()
        penalizaciones.extend([10 * p for p in penalizaciones_horas])
        
        # Objetivo 3: Equilibrar noches (peso 5)
        penalizaciones_noches = self._penalizar_equilibrio_noches()
        penalizaciones.extend([5 * p for p in penalizaciones_noches])
        
        # Objetivo 4: Equilibrar fines de semana (peso 3)
        penalizaciones_findes = self._penalizar_equilibrio_findes()
        penalizaciones.extend([3 * p for p in penalizaciones_findes])
        
        if penalizaciones:
            self.model.Minimize(sum(penalizaciones))
    
    def _penalizar_desviacion_base(self) -> list:
        """
        Penaliza celdas que se desvían de la rotación base.
        Objetivo PRIORITARIO.
        
        - Si turno_base es un turno real: penaliza asignar otro turno
        - Si turno_base es None (libre): penaliza asignar cualquier turno real
        """
        penalizaciones = []
        
        for enfermera_id, celdas in self.matriz.celdas.items():
            for fecha, celda in celdas.items():
                if not celda.es_modificable:
                    continue
                
                turno_base = celda.turno_base_id
                
                if turno_base is not None:
                    # Era un turno real: penalizar si se asigna otro turno
                    for turno_id in self.matriz.turnos_disponibles:
                        if turno_id != turno_base:
                            key = (enfermera_id, fecha, turno_id)
                            if key in self.solver_vars:
                                penalizaciones.append(self.solver_vars[key])
                else:
                    # Era LIBRE en la rotación base: penalizar si se asigna
                    # cualquier turno real (no LIBRE_SENTINEL)
                    for turno_id in self.matriz.turnos_disponibles:
                        if turno_id != self.LIBRE_SENTINEL:
                            key = (enfermera_id, fecha, turno_id)
                            if key in self.solver_vars:
                                penalizaciones.append(self.solver_vars[key])
        
        return penalizaciones
    
    def _penalizar_balance_horas(self) -> list:
        """
        Penaliza la desviación de horas mensuales objetivo.
        Usa horas_objetivo reales desde contratos (pasadas desde pipeline).
        """
        penalizaciones = []
        
        # Usar horas_objetivo reales si están disponibles
        horas_objetivo_por_enfermera = dict(self.horas_objetivo)
        
        # Fallback: intentar deducir desde objetivos/config si no hay horas_objetivo
        if not horas_objetivo_por_enfermera:
            for r in self.objetivos:
                # Soportar ambos campos: 'nombre' y 'tipo'
                nombre_raw = r.get('nombre', '') or r.get('tipo', '')
                if 'HORA' in nombre_raw.upper() or 'EQUIDAD' in nombre_raw.upper():
                    for enf_id in self.matriz.enfermeras:
                        horas_objetivo_por_enfermera[enf_id] = int(r.get('horas_objetivo', r.get('valor', 160)))
        
        # Fallback final: 160h/mes para todos si no hay configuración
        if not horas_objetivo_por_enfermera:
            logger.warning("No hay horas_objetivo disponibles, usando 160h por defecto")
            for enf_id in self.matriz.enfermeras:
                horas_objetivo_por_enfermera[enf_id] = 160
        
        # Para cada enfermera, calcular horas totales y minimizar desviación
        for enfermera_id in self.matriz.enfermeras:
            if enfermera_id not in horas_objetivo_por_enfermera:
                continue
            
            objetivo = horas_objetivo_por_enfermera[enfermera_id]
            vars_horas = []
            
            for fecha in self.matriz.fechas:
                for turno_id in self.matriz.turnos_disponibles:
                    # Saltar LIBRE sentinel (no suma horas)
                    if turno_id == self.LIBRE_SENTINEL:
                        continue
                    key = (enfermera_id, fecha, turno_id)
                    if key in self.solver_vars:
                        duracion = self.turnos_info.get(turno_id, None)
                        if duracion:
                            factor = int(duracion.duracion_horas * 10)  # Entero para CP-SAT
                            vars_horas.append(factor * self.solver_vars[key])
            
            if vars_horas:
                # Variable de desviación (entera positiva)
                desviacion = self.model.NewIntVar(0, 10000, f'desv_h_{enfermera_id}')
                self.model.Add(
                    sum(vars_horas) - objetivo * 10 <= desviacion
                )
                self.model.Add(
                    objetivo * 10 - sum(vars_horas) <= desviacion
                )
                penalizaciones.append(desviacion)
        
        return penalizaciones
    
    def _penalizar_equilibrio_noches(self) -> list:
        """
        Penaliza el desequilibrio en noches asignadas entre enfermeras.
        Minimiza la diferencia máxima de noches.
        """
        penalizaciones = []
        
        # Identificar turnos nocturnos
        turnos_nocturnos = [
            t_id for t_id, t_info in self.turnos_info.items()
            if t_info.es_nocturno
        ]
        
        if not turnos_nocturnos:
            return penalizaciones
        
        # Para cada enfermera, contar noches
        vars_noches_por_enf = {}
        for enfermera_id in self.matriz.enfermeras:
            vars_noche = []
            for fecha in self.matriz.fechas:
                for turno_id in turnos_nocturnos:
                    key = (enfermera_id, fecha, turno_id)
                    if key in self.solver_vars:
                        vars_noche.append(self.solver_vars[key])
            
            if vars_noche:
                noche_var = self.model.NewIntVar(0, len(self.matriz.fechas), f'noches_{enfermera_id}')
                self.model.Add(sum(vars_noche) == noche_var)
                vars_noches_por_enf[enfermera_id] = noche_var
        
        if vars_noches_por_enf:
            # Minimizar diferencia máxima
            max_noches = self.model.NewIntVar(0, len(self.matriz.fechas), 'max_noches')
            min_noches = self.model.NewIntVar(0, len(self.matriz.fechas), 'min_noches')
            
            for v in vars_noches_por_enf.values():
                self.model.Add(max_noches >= v)
                self.model.Add(min_noches <= v)
            
            diff_noches = self.model.NewIntVar(0, len(self.matriz.fechas), 'diff_noches')
            self.model.Add(diff_noches == max_noches - min_noches)
            penalizaciones.append(diff_noches)
        
        return penalizaciones
    
    def _penalizar_equilibrio_findes(self) -> list:
        """
        Penaliza el desequilibrio en fines de semana trabajados.
        Minimiza la diferencia máxima de fines de semana entre enfermeras.
        
        Solo cuenta turnos REALES (excluye LIBRE_SENTINEL).
        """
        penalizaciones = []
        
        # Identificar fines de semana en el período
        findes = []
        for i, fecha in enumerate(sorted(self.matriz.fechas)):
            if fecha.weekday() >= 5:  # Sábado=5, Domingo=6
                findes.append(i)
        
        if not findes:
            return penalizaciones
        
        # Solo turnos REALES (excluir LIBRE_SENTINEL)
        turno_ids = [
            t_id for t_id in self.matriz.turnos_disponibles
            if t_id != self.LIBRE_SENTINEL
        ]
        
        if not turno_ids:
            return penalizaciones
        
        # Para cada enfermera, contar findes trabajados
        vars_finde_por_enf = {}
        for enfermera_id in self.matriz.enfermeras:
            vars_finde = []
            for fecha_idx, fecha in enumerate(sorted(self.matriz.fechas)):
                if fecha.weekday() >= 5:
                    for turno_id in turno_ids:
                        key = (enfermera_id, fecha, turno_id)
                        if key in self.solver_vars:
                            vars_finde.append(self.solver_vars[key])
            
            if vars_finde:
                finde_var = self.model.NewIntVar(0, len(findes), f'findes_{enfermera_id}')
                self.model.Add(sum(vars_finde) == finde_var)
                vars_finde_por_enf[enfermera_id] = finde_var
        
        if vars_finde_por_enf:
            # Minimizar diferencia máxima
            max_finde = self.model.NewIntVar(0, len(findes), 'max_finde')
            min_finde = self.model.NewIntVar(0, len(findes), 'min_finde')
            
            for v in vars_finde_por_enf.values():
                self.model.Add(max_finde >= v)
                self.model.Add(min_finde <= v)
            
            diff_finde = self.model.NewIntVar(0, len(findes), 'diff_finde')
            self.model.Add(diff_finde == max_finde - min_finde)
            penalizaciones.append(diff_finde)
        
        return penalizaciones
    
    def _extraer_solucion(self, solver: cp_model.CpSolver) -> MatrizPlanificacion:
        """
        Extrae la solución del solver y actualiza la matriz.
        Maneja explícitamente el LIBRE_SENTINEL para celdas que permanecen libres.
        """
        matriz_resultado = self.matriz.clone()
        
        # Build a lookup map for turno_id -> TurnoInfo
        turno_lookup = {t_id: t_info for t_id, t_info in self.turnos_info.items()}
        
        for (enfermera_id, fecha, turno_id), var in self.solver_vars.items():
            if solver.Value(var) == 1:
                celda = matriz_resultado.obtener_celda(enfermera_id, fecha)
                if celda and celda.es_modificable:
                    if turno_id == self.LIBRE_SENTINEL:
                        # Celda permanece libre
                        celda.turno = None
                        celda.tipo_celda = TipoCelda.LIBRE
                    elif turno_id in turno_lookup:
                        # Asignar turno real
                        celda.turno = turno_lookup[turno_id]
                        celda.tipo_celda = TipoCelda.TURNO
                    else:
                        # Fallback: turno no encontrado, marcar como libre
                        celda.turno = None
                        celda.tipo_celda = TipoCelda.LIBRE
        
        return matriz_resultado

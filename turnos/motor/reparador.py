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
    - Restricciones duras (descansos, máximos consecutivos, etc.)
    - Proximidad a la rotación base (objetivo primario)
    
    Nota: No maneja celdas bloqueadas por incidencias porque estas se aplican
    como overlay post-generación (Phase 6), después del solver.
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
        balances_historicos: Dict[int, dict] = None,
    ):
        self.matriz = matriz_bloqueada
        self.analisis = analisis_cobertura
        self.turnos_info = turnos_info
        self.restricciones_duras = restricciones_duras or []
        self.objetivos = objetivos or []
        self.cobertura_minima = cobertura_minima or {}
        self.horas_objetivo = horas_objetivo or {}  # enfermera_id -> horas_mes_objetivo
        self.balances_historicos = balances_historicos or {}
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
        Crea variables CP-SAT para TODAS las celdas.
        Incluye opción explícita de LIBRE para que una celda libre
        pueda seguir siendo libre o convertirse en un turno.
        
        Nota: No hay celdas bloqueadas porque las incidencias se aplican
        como overlay post-generación, no antes del solver.
        
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
                # Variable: ¿se asigna turno t (o LIBRE) a esta celda?
                for turno_id in self.matriz.turnos_disponibles:
                    var = self.model.NewBoolVar(
                        f"x_e{enfermera_id}_d{fecha}_t{turno_id}"
                    )
                    self.solver_vars[(enfermera_id, fecha, turno_id)] = var
                
                # Restricción: exactamente una opción por celda
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
        
        Todas las celdas son variables del solver (no hay celdas bloqueadas).
        """
        # Buscar configuración - soportar ambos campos: 'nombre' y 'tipo'
        max_consec = 6  # Default
        for r in self.restricciones_duras:
            nombre_raw = r.get('nombre', '') or r.get('tipo', '')
            if normalizar_nombre(nombre_raw) == 'TURNO_CONSECUTIVOS_MAX':
                max_consec = int(r.get('valor', r.get('parametros', {}).get('max', 6)))
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
                
                # Todas las celdas son variables del solver
                vars_trabajo = []
                for fecha in ventana:
                    for turno_id in turnos_reales:
                        key = (enfermera_id, fecha, turno_id)
                        if key in self.solver_vars:
                            vars_trabajo.append(self.solver_vars[key])
                
                if vars_trabajo:
                    self.model.Add(sum(vars_trabajo) <= max_consec)
    
    def _restringir_descanso_entre_turnos(self):
        """Garantiza descanso mínimo de 12 horas reales entre turnos consecutivos.

        Utiliza cálculo de datetime real (fin turno A → inicio turno B) en lugar
        de heurísticas semánticas (noche → madrugador). Considera tanto celdas
        bloqueadas como variables del solver.
        """
        from ..utils.tiempo import calcular_descanso_entre_turnos
        from datetime import date, timedelta

        # Precomputar pares de turnos incompatibles en días consecutivos
        transiciones_prohibidas = set()
        ref_date = date(2026, 1, 1)
        next_date = ref_date + timedelta(days=1)

        for t_id_a, t_info_a in self.turnos_info.items():
            for t_id_b, t_info_b in self.turnos_info.items():
                descanso = calcular_descanso_entre_turnos(
                    ref_date, t_info_a, next_date, t_info_b
                )
                if descanso < 12.0:
                    transiciones_prohibidas.add((t_id_a, t_id_b))

        if not transiciones_prohibidas:
            return

        fechas_ordenadas = sorted(self.matriz.fechas)

        for enfermera_id in self.matriz.enfermeras:
            for i in range(len(fechas_ordenadas) - 1):
                fecha_actual = fechas_ordenadas[i]
                fecha_siguiente = fechas_ordenadas[i + 1]

                for t_id_a, t_id_b in transiciones_prohibidas:
                    key_a = (enfermera_id, fecha_actual, t_id_a)
                    key_b = (enfermera_id, fecha_siguiente, t_id_b)

                    a_en_solver = key_a in self.solver_vars
                    b_en_solver = key_b in self.solver_vars

                    if a_en_solver and b_en_solver:
                        # Ambos en solver: no pueden activarse juntos
                        self.model.Add(
                            self.solver_vars[key_a] + self.solver_vars[key_b] <= 1
                        )
    
    def _restringir_cobertura_minima(self):
        """Garantiza cobertura mínima por turno y fecha.
        
        Todas las celdas son variables del solver (no hay celdas bloqueadas).
        """
        cobertura_min = self.cobertura_minima
        
        for fecha in self.matriz.fechas:
            for turno_id, minimo in cobertura_min.items():
                # Todas las celdas son variables del solver
                vars_solver = []
                for enfermera_id in self.matriz.enfermeras:
                    key = (enfermera_id, fecha, turno_id)
                    if key in self.solver_vars:
                        vars_solver.append(self.solver_vars[key])
                
                if minimo > 0 and vars_solver:
                    self.model.Add(sum(vars_solver) >= minimo)
    
    def _restringir_noches_consecutivas(self):
        """Limita noches consecutivas.
        
        Todas las celdas son variables del solver (no hay celdas bloqueadas).
        """
        # Soportar ambos campos: 'nombre' y 'tipo'
        max_noches = 3  # Default: igual que validador_motor
        for r in self.restricciones_duras:
            nombre_raw = r.get('nombre', '') or r.get('tipo', '')
            if normalizar_nombre(nombre_raw) == 'NOCHES_CONSECUTIVAS_MAX':
                max_noches = int(r.get('valor', r.get('parametros', {}).get('max', 3)))
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
                
                # Todas las celdas son variables del solver
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
        Configura función objetivo ponderada (weighted-sum) para el solver.

        NO es optimización lexicográfica estricta. Se usa una suma ponderada
        donde los pesos relativos establecen la prioridad entre objetivos:
          - Rotación base: peso 500 (máxima prioridad: preservar patrón)
          - Balance horario: peso 5
          - Equilibrio noches: peso 5
          - Equilibrio fines de semana: peso 3

        Con estos pesos, romper una celda de rotación cuesta 500 puntos,
        mientras que una desviación horaria de ±24h genera ~120 puntos por
        enfermera. El solver prefiere mantener el patrón antes que romperlo.

        TODO: Implementar optimización lexicográfica real mediante llamadas
        secuenciales a solver.Solve() si se requiere prioridad estricta.
        """
        penalizaciones = []
        
        # Objetivo 1: Minimizar desviación de rotación base (peso 500)
        penalizaciones_base = self._penalizar_desviacion_base()
        penalizaciones.extend([500 * p for p in penalizaciones_base])
        
        # Objetivo 2: Balance de horas mensuales (peso 5)
        penalizaciones_horas = self._penalizar_balance_horas()
        penalizaciones.extend([5 * p for p in penalizaciones_horas])
        
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
        
        Usa `_turno_base_original_id` (snapshot inmutable de Phase 1) cuando
        está disponible, para que AjustadorHoras no corrompa la referencia.
        
        - Si turno_base es un turno real: penaliza asignar otro turno
        - Si turno_base es None (libre): penaliza asignar cualquier turno real
        """
        penalizaciones = []
        
        for enfermera_id, celdas in self.matriz.celdas.items():
            for fecha, celda in celdas.items():
                # Usar snapshot inmutable si existe; fallback a propiedad computada
                turno_base = (
                    celda._turno_base_original_id
                    if celda._turno_base_original_id is not None
                    else celda.turno_base_id
                )
                
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
        Incluye horas del solver del período actual y un offset por horas
        acumuladas históricamente para favorecer el balance inter-mensual.
        
        No hay horas bloqueadas porque las incidencias se aplican post-generación.
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

        # Para cada enfermera, calcular horas del período actual y minimizar desviación
        for enfermera_id in self.matriz.enfermeras:
            if enfermera_id not in horas_objetivo_por_enfermera:
                continue

            # Asegurar que objetivo sea entero (CP-SAT no acepta flotantes)
            objetivo = int(horas_objetivo_por_enfermera[enfermera_id])

            # Horas asignables por el SOLVER (período actual)
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

            # Construir expresión: histórico + variables solver
            # El histórico actúa como offset constante: enfermeras con más
            # horas acumuladas verán mayor desviación, favoreciendo que el
            # solver les asigne menos turnos este mes.
            horas_historico = int(
                self.balances_historicos.get(enfermera_id, {}).get(
                    'horas_acumuladas_previas', 0
                ) * 10
            )
            total_expr = horas_historico
            if vars_horas:
                total_expr += sum(vars_horas)

            if vars_horas:
                desviacion = self.model.NewIntVar(0, 50000, f'desv_h_{enfermera_id}')
                self.model.Add(total_expr - objetivo * 10 <= desviacion)
                self.model.Add(objetivo * 10 - total_expr <= desviacion)
                penalizaciones.append(desviacion)

        return penalizaciones
    
    def _penalizar_equilibrio_noches(self) -> list:
        """
        Penaliza el desequilibrio en noches asignadas entre enfermeras.
        Minimiza la diferencia máxima de noches.
        Incluye acumulado histórico para medir la carga total real.
        
        No hay noches bloqueadas porque las incidencias se aplican post-generación.
        """
        penalizaciones = []

        # Identificar turnos nocturnos
        turnos_nocturnos = [
            t_id for t_id, t_info in self.turnos_info.items()
            if t_info.es_nocturno
        ]

        if not turnos_nocturnos:
            return penalizaciones

        # Para cada enfermera, contar noches (solver + histórico)
        vars_noches_por_enf = {}
        for enfermera_id in self.matriz.enfermeras:
            # Noches asignables por el SOLVER
            vars_noche = []
            for fecha in self.matriz.fechas:
                for turno_id in turnos_nocturnos:
                    key = (enfermera_id, fecha, turno_id)
                    if key in self.solver_vars:
                        vars_noche.append(self.solver_vars[key])

            # Noches HISTÓRICAS acumuladas (constante)
            noches_historico = 0
            hist = self.balances_historicos.get(enfermera_id, {})
            noches_historico = hist.get('noches_acumuladas', 0)

            if vars_noche:
                noche_var = self.model.NewIntVar(
                    0, len(self.matriz.fechas) + noches_historico,
                    f'noches_{enfermera_id}'
                )
                self.model.Add(noches_historico + sum(vars_noche) == noche_var)
                vars_noches_por_enf[enfermera_id] = noche_var
            elif noches_historico > 0:
                # Solo tiene noches históricas: variable constante
                noche_var = self.model.NewIntVar(noches_historico, noches_historico, f'noches_{enfermera_id}')
                vars_noches_por_enf[enfermera_id] = noche_var

        if vars_noches_por_enf:
            # Minimizar diferencia máxima
            max_noches = self.model.NewIntVar(0, len(self.matriz.fechas) * 2, 'max_noches')
            min_noches = self.model.NewIntVar(0, len(self.matriz.fechas) * 2, 'min_noches')

            for v in vars_noches_por_enf.values():
                self.model.Add(max_noches >= v)
                self.model.Add(min_noches <= v)

            diff_noches = self.model.NewIntVar(0, len(self.matriz.fechas) * 2, 'diff_noches')
            self.model.Add(diff_noches == max_noches - min_noches)
            penalizaciones.append(diff_noches)

        return penalizaciones
    
    def _penalizar_equilibrio_findes(self) -> list:
        """
        Penaliza el desequilibrio en fines de semana trabajados.
        Minimiza la diferencia máxima de fines de semana entre enfermeras.
        Incluye acumulado histórico para medir la carga total real.
        
        No hay fines de semana bloqueados porque las incidencias se aplican post-generación.
        """
        penalizaciones = []

        # Identificar fines de semana en el período
        findes = []
        for fecha in sorted(self.matriz.fechas):
            if fecha.weekday() >= 5:  # Sábado=5, Domingo=6
                findes.append(fecha)

        if not findes:
            return penalizaciones

        # Solo turnos REALES (excluir LIBRE_SENTINEL)
        turno_ids = [
            t_id for t_id in self.matriz.turnos_disponibles
            if t_id != self.LIBRE_SENTINEL
        ]

        if not turno_ids:
            return penalizaciones

        # Para cada enfermera, contar findes trabajados (solver + histórico)
        vars_finde_por_enf = {}
        for enfermera_id in self.matriz.enfermeras:
            # Fines de semana asignables por el SOLVER
            vars_finde = []
            for fecha in findes:
                for turno_id in turno_ids:
                    key = (enfermera_id, fecha, turno_id)
                    if key in self.solver_vars:
                        vars_finde.append(self.solver_vars[key])

            # Fines de semana HISTÓRICOS acumulados (constante)
            findes_historico = 0
            hist = self.balances_historicos.get(enfermera_id, {})
            findes_historico = hist.get('fines_semana_acumulados', 0)

            if vars_finde:
                finde_var = self.model.NewIntVar(
                    0, len(findes) + findes_historico,
                    f'findes_{enfermera_id}'
                )
                self.model.Add(findes_historico + sum(vars_finde) == finde_var)
                vars_finde_por_enf[enfermera_id] = finde_var
            elif findes_historico > 0:
                # Solo tiene findes históricos: variable constante
                finde_var = self.model.NewIntVar(findes_historico, findes_historico, f'findes_{enfermera_id}')
                vars_finde_por_enf[enfermera_id] = finde_var

        if vars_finde_por_enf:
            # Minimizar diferencia máxima
            max_finde = self.model.NewIntVar(0, len(findes) * 2, 'max_finde')
            min_finde = self.model.NewIntVar(0, len(findes) * 2, 'min_finde')

            for v in vars_finde_por_enf.values():
                self.model.Add(max_finde >= v)
                self.model.Add(min_finde <= v)

            diff_finde = self.model.NewIntVar(0, len(findes) * 2, 'diff_finde')
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
                if celda:
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

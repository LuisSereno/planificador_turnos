"""
Generador de planificaciones usando OR-Tools
"""
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class GeneradorTurnos:
    """Clase para generar planificaciones de turnos usando CP-SAT"""

    def __init__(self, configuracion):
        """
        Inicializa el generador con una configuración

        Args:
            configuracion: Instancia de ConfiguracionPlanificacion
        """
        self.configuracion = configuracion
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Parámetros
        self.num_dias = configuracion.num_dias
        self.enfermeras = list(configuracion.enfermeras.filter(activa=True))
        self.num_enfermeras = len(self.enfermeras)
        self.turnos = list(configuracion.turnos.filter(activo=True))
        self.num_turnos = len(self.turnos)

        if not self.enfermeras:
            raise ValueError("No hay enfermeras activas disponibles")
        if not self.turnos:
            raise ValueError("No hay turnos activos disponibles")

        # Variables de decisión
        self.shifts = {}
        self.resultado = None

        # Configurar solver
        if configuracion.tiempo_maximo_segundos:
            self.solver.parameters.max_time_in_seconds = configuracion.tiempo_maximo_segundos

        if configuracion.num_trabajadores:
            self.solver.parameters.num_search_workers = configuracion.num_trabajadores

        if configuracion.seed:
            self.solver.parameters.random_seed = configuracion.seed

        logger.info(f"📊 Generador inicializado: {self.num_enfermeras} enfermeras, {self.num_turnos} turnos, {self.num_dias} días")

    def crear_variables(self):
        """Crea las variables de decisión del modelo"""
        # shifts[e, d, t] = 1 si enfermera e trabaja turno t en día d
        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                for t in range(self.num_turnos):
                    self.shifts[(e, d, t)] = self.model.NewBoolVar(
                        f'shift_e{e}_d{d}_t{t}'
                    )
        logger.info(f"✅ Variables creadas: {len(self.shifts)}")

    def aplicar_restricciones_duras(self):
        """Aplica las restricciones duras (obligatorias)"""
        restricciones = self.configuracion.restricciones_duras or []

        # Restricción básica: un turno por día (SIEMPRE APLICADA)
        self._restriccion_un_turno_por_dia()

        # Restricción de cobertura mínima (SIEMPRE APLICADA si hay demanda)
        self._restriccion_cobertura_minima_default()

        for restriccion in restricciones:
            nombre = restriccion.get('nombre')
            params = restriccion.get('parametros', {})

            if nombre == 'cobertura_minima':
                # Ya aplicada arriba, pero podemos sobrescribir
                self._restriccion_cobertura_minima(params)

            elif nombre == 'cobertura_maxima':
                self._restriccion_cobertura_maxima(params)

            elif nombre == 'descanso_minimo':
                self._restriccion_descanso_minimo(params)

            elif nombre == 'turnos_consecutivos_max':
                self._restriccion_turnos_consecutivos_max(params)

            elif nombre == 'turnos_semanales_max':
                self._restriccion_turnos_semanales_max(params)

        logger.info(f"✅ Restricciones duras aplicadas")

    def _restriccion_un_turno_por_dia(self):
        """Una enfermera solo puede trabajar un turno por día"""
        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                self.model.Add(
                    sum(self.shifts[(e, d, t)] for t in range(self.num_turnos)) <= 1
                )

    def _restriccion_cobertura_minima_default(self):
        """Cobertura mínima por defecto (si no hay restricción específica)"""
        demanda = self.configuracion.demanda_por_turno or {}

        restricciones_aplicadas = 0
        for d in range(self.num_dias):
            for t, turno in enumerate(self.turnos):
                turno_demanda = demanda.get(turno.nombre, {})
                minimo = turno_demanda.get('min', 2)  # Default: 2 enfermeras mínimo

                if minimo > 0:
                    self.model.Add(
                        sum(self.shifts[(e, d, t)] for e in range(self.num_enfermeras)) >= minimo
                    )
                    restricciones_aplicadas += 1

        logger.info(f"   📌 Cobertura mínima: {restricciones_aplicadas} restricciones aplicadas")

    def _restriccion_cobertura_minima(self, params):
        """Cobertura mínima de enfermeras por turno (sobrescribe default)"""
        demanda = self.configuracion.demanda_por_turno or {}

        for d in range(self.num_dias):
            for t, turno in enumerate(self.turnos):
                turno_demanda = demanda.get(turno.nombre, {})
                minimo = turno_demanda.get('min', params.get('min', 1))

                self.model.Add(
                    sum(self.shifts[(e, d, t)] for e in range(self.num_enfermeras)) >= minimo
                )

    def _restriccion_cobertura_maxima(self, params):
        """Cobertura máxima de enfermeras por turno"""
        demanda = self.configuracion.demanda_por_turno or {}

        for d in range(self.num_dias):
            for t, turno in enumerate(self.turnos):
                turno_demanda = demanda.get(turno.nombre, {})
                maximo = turno_demanda.get('max', params.get('max', self.num_enfermeras))

                self.model.Add(
                    sum(self.shifts[(e, d, t)] for e in range(self.num_enfermeras)) <= maximo
                )

    def _restriccion_descanso_minimo(self, params):
        """Descanso mínimo entre turnos"""
        horas_minimas = params.get('horas', 11)

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias - 1):
                for t1 in range(self.num_turnos):
                    for t2 in range(self.num_turnos):
                        if self._requiere_descanso(t1, t2, horas_minimas):
                            self.model.Add(
                                self.shifts[(e, d, t1)] + self.shifts[(e, d + 1, t2)] <= 1
                            )

    def _restriccion_turnos_consecutivos_max(self, params):
        """Máximo de turnos consecutivos"""
        max_consecutivos = params.get('max', 5)

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias - max_consecutivos):
                total_trabajados = sum(
                    self.shifts[(e, d + i, t)]
                    for i in range(max_consecutivos + 1)
                    for t in range(self.num_turnos)
                )
                self.model.Add(total_trabajados <= max_consecutivos)

    def _restriccion_turnos_semanales_max(self, params):
        """Máximo de turnos por semana"""
        max_semanales = params.get('max', 5)

        for e in range(self.num_enfermeras):
            for semana in range(self.num_dias // 7):
                inicio = semana * 7
                fin = min(inicio + 7, self.num_dias)

                total_semana = sum(
                    self.shifts[(e, d, t)]
                    for d in range(inicio, fin)
                    for t in range(self.num_turnos)
                )
                self.model.Add(total_semana <= max_semanales)

    def aplicar_objetivo(self):
        """Define el objetivo de optimización"""
        # OBJETIVO PRINCIPAL: Maximizar turnos asignados (evitar días libres innecesarios)
        total_turnos = sum(
            self.shifts[(e, d, t)]
            for e in range(self.num_enfermeras)
            for d in range(self.num_dias)
            for t in range(self.num_turnos)
        )

        self.model.Maximize(total_turnos)
        logger.info("✅ Objetivo: Maximizar turnos asignados")

    def _requiere_descanso(self, turno1_idx, turno2_idx, horas_minimas):
        """Verifica si dos turnos requieren descanso entre ellos"""
        turno1 = self.turnos[turno1_idx]
        turno2 = self.turnos[turno2_idx]

        if turno1.nombre == 'NOCHE' and turno2.nombre == 'MANANA':
            return True

        return False

    def resolver(self) -> Dict:
        """
        Resuelve el modelo y retorna el resultado

        Returns:
            Dict con el resultado de la optimización
        """
        logger.info("=" * 60)
        logger.info("INICIANDO SOLVER OR-TOOLS")
        logger.info("=" * 60)

        # Crear variables
        self.crear_variables()

        # Aplicar restricciones
        self.aplicar_restricciones_duras()

        # Aplicar objetivo
        self.aplicar_objetivo()

        # Resolver
        logger.info("⚙️ Ejecutando solver...")
        inicio = datetime.now()
        status = self.solver.Solve(self.model)
        fin = datetime.now()
        tiempo_ejecucion = (fin - inicio).total_seconds()

        status_str = self._get_status_string(status)
        logger.info(f"🏁 Solver finalizado: {status_str} en {tiempo_ejecucion:.2f}s")

        resultado = {
            'success': status in [cp_model.OPTIMAL, cp_model.FEASIBLE],
            'status': status_str,
            'es_optima': status == cp_model.OPTIMAL,
            'penalizacion_total': 0.0,  # No usado en este modelo
            'tiempo_ejecucion': tiempo_ejecucion,
            'asignaciones': []
        }

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            resultado['asignaciones'] = self._extraer_asignaciones()

            turnos_trabajados = len([a for a in resultado['asignaciones'] if not a['es_dia_libre']])
            dias_libres = len([a for a in resultado['asignaciones'] if a['es_dia_libre']])

            logger.info(f"📊 Turnos trabajados: {turnos_trabajados}")
            logger.info(f"🏖️ Días libres: {dias_libres}")
            logger.info("=" * 60)
        else:
            logger.error(f"❌ No se encontró solución: {status_str}")

        self.resultado = resultado
        return resultado

    def _get_status_string(self, status):
        """Convierte el status del solver a string"""
        status_map = {
            cp_model.OPTIMAL: 'OPTIMAL',
            cp_model.FEASIBLE: 'FEASIBLE',
            cp_model.INFEASIBLE: 'INFEASIBLE',
            cp_model.MODEL_INVALID: 'MODEL_INVALID',
            cp_model.UNKNOWN: 'UNKNOWN'
        }
        return status_map.get(status, 'UNKNOWN')

    def _extraer_asignaciones(self) -> List[Dict]:
        """Extrae las asignaciones del modelo resuelto"""
        asignaciones = []
        fecha_inicio = self.configuracion.fecha_inicio

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                fecha = fecha_inicio + timedelta(days=d)
                turno_asignado = False

                for t in range(self.num_turnos):
                    if self.solver.Value(self.shifts[(e, d, t)]) == 1:
                        asignaciones.append({
                            'enfermera_id': self.enfermeras[e].id,
                            'enfermera_nombre': self.enfermeras[e].nombre,
                            'turno_id': self.turnos[t].id,
                            'turno': self.turnos[t].nombre,
                            'fecha': fecha.isoformat(),
                            'dia': d,
                            'es_dia_libre': False
                        })
                        turno_asignado = True
                        break

                if not turno_asignado:
                    # Día libre
                    asignaciones.append({
                        'enfermera_id': self.enfermeras[e].id,
                        'enfermera_nombre': self.enfermeras[e].nombre,
                        'turno_id': None,
                        'turno': 'LIBRE',
                        'fecha': fecha.isoformat(),
                        'dia': d,
                        'es_dia_libre': True
                    })

        return asignaciones

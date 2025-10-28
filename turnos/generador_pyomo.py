# turnos/generador_pyomo.py
# GENERADOR COMPLETO CON PYOMO - Implementa restricciones SACYL

import logging
from datetime import timedelta, datetime
from pyomo.environ import (
    ConcreteModel, Var, Constraint, Objective,
    Binary, NonNegativeReals, minimize, maximize,
    SolverFactory, value
)

logger = logging.getLogger(__name__)


class GeneradorTurnosPyomo:
    """
    Generador de turnos usando Pyomo para restricciones complejas SACYL
    Implementa RD001-RD020 y RB001-RB015
    """

    def __init__(self, configuracion):
        self.configuracion = configuracion
        self.model = ConcreteModel()

        # Datos base
        self.num_dias = configuracion.num_dias
        self.enfermeras = list(configuracion.enfermeras.all())
        self.turnos = list(configuracion.turnos.all())
        self.num_enfermeras = len(self.enfermeras)
        self.num_turnos = len(self.turnos)

        # Extraer demanda
        self.demanda = self._procesar_demanda()

        logger.info(
            f"✓ Pyomo Model inicializado: {self.num_enfermeras} enf, {self.num_turnos} turnos, {self.num_dias} días")

    def _procesar_demanda(self):
        """Extrae min/optimo/max de demanda_por_turno"""
        demanda = self.configuracion.demanda_por_turno or {}
        resultado = {}

        for turno in self.turnos:
            d = demanda.get(turno.nombre, {})
            if isinstance(d, dict):
                resultado[turno.nombre] = {
                    'min': d.get('min', 1),
                    'optimo': d.get('optimo', 2),
                    'max': d.get('max', 5)
                }
            else:
                val = int(d) if d else 1
                resultado[turno.nombre] = {'min': val, 'optimo': val, 'max': val + 2}

        return resultado

    def crear_variables(self):
        """Define variables de decisión"""
        m = self.model

        # X[e,d,t] = 1 si enfermera e trabaja turno t en día d
        m.E = range(self.num_enfermeras)
        m.D = range(self.num_dias)
        m.T = range(self.num_turnos)

        m.X = Var(m.E, m.D, m.T, domain=Binary)

        # Y[e,d] = 1 si enfermera e libra en día d
        m.Y = Var(m.E, m.D, domain=Binary)

        # Variables auxiliares para objetivos blandos
        m.max_turnos = Var(m.T, domain=NonNegativeReals)  # Max turnos por tipo
        m.min_turnos = Var(m.T, domain=NonNegativeReals)  # Min turnos por tipo

        logger.info(f"✓ Variables creadas: {self.num_enfermeras * self.num_dias * self.num_turnos} binarias")

    def aplicar_rd020_no_solapamiento(self):
        """RD020: Una enfermera, máximo un turno por día"""
        m = self.model

        def rule(m, e, d):
            return sum(m.X[e, d, t] for t in m.T) + m.Y[e, d] == 1

        m.RD020 = Constraint(m.E, m.D, rule=rule)
        logger.info("✓ RD020: No solapamiento aplicada")

    def aplicar_rd019_cobertura(self):
        """RD019: Cobertura mínima y máxima por turno"""
        m = self.model

        def rule_min(m, d, t):
            turno_nombre = self.turnos[t].nombre
            minimo = self.demanda[turno_nombre]['min']
            return sum(m.X[e, d, t] for e in m.E) >= minimo

        def rule_max(m, d, t):
            turno_nombre = self.turnos[t].nombre
            maximo = self.demanda[turno_nombre].get('max', 4)
            return sum(m.X[e, d, t] for e in m.E) <= maximo

        m.RD019_min = Constraint(m.D, m.T, rule=rule_min)
        m.RD019_max = Constraint(m.D, m.T, rule=rule_max)
        logger.info("✓ RD019: Cobertura mínima y máxima aplicada")

        """RD017+RD018: Mínimo 28 días libres/año (22 vac + 6 asuntos)"""
        m = self.model

        dias_libres_requeridos = int((self.num_dias / 365) * 28)

        def rule(m, e):
            return sum(m.Y[e, d] for d in m.D) >= dias_libres_requeridos

        m.RD017_RD018 = Constraint(m.E, rule=rule)
        logger.info(f"✓ RD017+RD018: Mínimo {dias_libres_requeridos} días libres")

    def aplicar_rd006_descanso_12h(self):
        """RD006: Descanso mínimo 12h entre jornadas - VERSION COMPLETA"""

        # Obtener horarios reales de los turnos
        turnos_info = {}
        for turno in self.turnos:
            turnos_info[turno.nombre] = {
                'inicio': turno.hora_inicio,
                'fin': turno.hora_fin
            }

        logger.info(f"Turnos detectados: {list(turnos_info.keys())}")

        # Calcular horas entre cada par de turnos
        pares_prohibidos = []
        for t1_idx, t1 in enumerate(self.turnos):
            for t2_idx, t2 in enumerate(self.turnos):
                if t1_idx == t2_idx:
                    continue

                # Calcular horas entre fin de t1 y inicio de t2
                fin_t1 = t1.hora_fin
                inicio_t2 = t2.hora_inicio

                # Convertir a minutos desde medianoche
                fin_t1_mins = fin_t1.hour * 60 + fin_t1.minute
                inicio_t2_mins = inicio_t2.hour * 60 + inicio_t2.minute

                # Si t2 empieza antes que t1 termina, es día siguiente
                if inicio_t2_mins < fin_t1_mins:
                    inicio_t2_mins += 24 * 60

                horas_descanso = (inicio_t2_mins - fin_t1_mins) / 60

                if horas_descanso < 12:
                    pares_prohibidos.append((t1_idx, t2_idx, t1.nombre, t2.nombre, horas_descanso))
                    logger.debug(f"  Prohibir {t1.nombre}→{t2.nombre}: solo {horas_descanso:.1f}h descanso")

        # Aplicar restricciones para pares prohibidos
        for e in range(self.num_enfermeras):
            for d in range(self.num_dias - 1):
                for t1_idx, t2_idx, t1_nom, t2_nom, horas in pares_prohibidos:
                    # Si trabaja t1 en día d, NO puede trabajar t2 en día d+1
                    self.model.Add(
                        self.shifts[(e, d, t1_idx)] + self.shifts[(e, d + 1, t2_idx)] <= 1
                    )

        logger.info(f"✓ RD006: Descanso 12h aplicado ({len(pares_prohibidos)} pares prohibidos)")

    def aplicar_objetivos_blandos(self):
        """RB001-RB003: Equidad de turnos"""
        m = self.model

        # Definir max/min turnos por tipo
        for t in m.T:
            def rule_max(m, t=t):
                return m.max_turnos[t] >= sum(m.X[e, d, t] for e in m.E for d in m.D) / self.num_enfermeras

            def rule_min(m, t=t):
                return m.min_turnos[t] <= sum(m.X[e, d, t] for e in m.E for d in m.D) / self.num_enfermeras

            setattr(m, f'Max_turno_{t}', Constraint(rule=rule_max))
            setattr(m, f'Min_turno_{t}', Constraint(rule=rule_min))

        # Objetivo: minimizar diferencia max-min
        m.obj = Objective(
            expr=sum(m.max_turnos[t] - m.min_turnos[t] for t in m.T),
            sense=minimize
        )

        logger.info("✓ RB001-RB003: Equidad aplicada")

    def aplicar_limite_turnos_por_semana(self):
        """Limita el número de turnos por enfermera por semana"""
        m = self.model
        max_turnos_por_semana = 4

        def rule(m, e):
            return sum(m.X[e, d, t] for d in m.D for t in m.T) <= max_turnos_por_semana

        m.LIMITE_TURNOS = Constraint(m.E, rule=rule)
        logger.info(f"✓ Limite aplicado: Máximo {max_turnos_por_semana} turnos por semana")

    def resolver(self, solver='cbc', timeout=600):
        """Resuelve el modelo"""
        try:
            # Crear variables y restricciones
            self.crear_variables()
            self.aplicar_rd020_no_solapamiento()
            self.aplicar_rd019_cobertura()
            self.aplicar_rd017_rd018_vacaciones()
            self.aplicar_rd006_descanso_12h()
            self.aplicar_limite_turnos_por_semana()
            self.aplicar_objetivos_blandos()

            # Resolver
            opt = SolverFactory(solver)
            opt.options['seconds'] = timeout
            results = opt.solve(self.model, tee=True)

            # Extraer solución
            if results.solver.termination_condition == 'optimal':
                return self._extraer_solucion(optimal=True)
            elif results.solver.termination_condition == 'feasible':
                return self._extraer_solucion(optimal=False)
            else:
                return {'success': False, 'mensaje': 'Sin solución factible'}

        except Exception as e:
            logger.exception(f"Error Pyomo: {e}")
            return {'success': False, 'error': str(e)}

    def _extraer_solucion(self, optimal=True):
        """Extrae asignaciones del modelo resuelto"""
        m = self.model
        asignaciones = []

        fi = self.configuracion.fecha_inicio
        for e in m.E:
            for d in m.D:
                fecha = fi + timedelta(days=d)
                for t in m.T:
                    if value(m.X[e, d, t]) > 0.5:  # Variable binaria ≈ 1
                        asignaciones.append({
                            'enfermera_id': self.enfermeras[e].id,
                            'enfermera_nombre': self.enfermeras[e].nombre,
                            'fecha': fecha.isoformat(),
                            'turno_id': self.turnos[t].id,
                            'turno_nombre': self.turnos[t].nombre,
                            'es_dia_libre': False
                        })

        logger.info(f"✓ Solución extraída: {len(asignaciones)} asignaciones")

        return {
            'success': True,
            'es_optima': optimal,
            'asignaciones': asignaciones,
            'num_asignaciones': len(asignaciones)
        }

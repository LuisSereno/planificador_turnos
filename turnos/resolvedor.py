# -*- coding: utf-8 -*-
"""Módulo para resolver el modelo de optimización."""
import logging
from datetime import timedelta
from ortools.sat.python import cp_model
from .validador import ValidadorRestricciones as ValidadorRestriccionesNuevo

logger = logging.getLogger(__name__)


class ResolvedorModelo:
    """Maneja la resolución del modelo de optimización."""

    def __init__(self, modelo, configuracion, enfermeras, turnos, shifts):
        self.model = modelo
        self.configuracion = configuracion
        self.enfermeras = enfermeras
        self.turnos = turnos
        self.shifts = shifts

    def resolver(self):
        """Resuelve el modelo y retorna la solución."""
        logger.info("Resolviendo planificación...")

        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = self.configuracion.num_trabajadores
        solver.parameters.max_time_in_seconds = self.configuracion.tiempo_maximo_segundos

        if self.configuracion.seed:
            solver.parameters.random_seed = self.configuracion.seed

        status = solver.Solve(self.model)

        if status == cp_model.OPTIMAL:
            logger.info("✓ Solución ÓPTIMA encontrada")
        elif status == cp_model.FEASIBLE:
            logger.info("✓ Solución FACTIBLE encontrada")
        else:
            logger.error("✗ No se encontró solución")
            return {
                'success': False,
                'status': 'INFEASIBLE',
                'es_optima': False,
                'asignaciones': [],
                'num_asignaciones': 0,
                'mensaje': 'No se encontró una solución factible para las restricciones dadas.',
                'validacion': {}
            }

        return self._extraer_asignaciones(solver, status)

    def _extraer_asignaciones(self, solver, status):
        """Extrae las asignaciones y construye el diccionario de resultado completo."""
        num_dias = self.configuracion.num_dias
        num_enfermeras = len(self.enfermeras)
        num_turnos = len(self.turnos)

        asignaciones = []
        for e in range(num_enfermeras):
            for d in range(num_dias):
                es_dia_libre = True
                for t in range(num_turnos):
                    if solver.Value(self.shifts[e, d, t]) == 1:
                        es_dia_libre = False
                        fecha = self.configuracion.fecha_inicio + timedelta(days=d)
                        asignaciones.append({
                            'enfermera_id': self.enfermeras[e].id,
                            'enfermera_nombre': self.enfermeras[e].nombre,
                            'fecha': fecha.isoformat(),
                            'turno_id': self.turnos[t].id,
                            'turno_nombre': self.turnos[t].nombre,
                            'es_dia_libre': False
                        })
                if es_dia_libre:
                    fecha = self.configuracion.fecha_inicio + timedelta(days=d)
                    asignaciones.append({
                        'enfermera_id': self.enfermeras[e].id,
                        'enfermera_nombre': self.enfermeras[e].nombre,
                        'fecha': fecha.isoformat(),
                        'turno_id': None,
                        'turno_nombre': 'LIBRE',
                        'es_dia_libre': True
                    })

        resultado_parcial = {
            'status': 'OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE',
            'asignaciones': asignaciones,
            'objetivo': solver.ObjectiveValue() if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else None,
            'tiempo_resolucion': solver.WallTime()
        }

        logger.info("Validando la solución encontrada...")
        validador = ValidadorRestriccionesNuevo(self.configuracion, resultado_parcial)
        reporte_validacion = validador.validar()

        es_optima = status == cp_model.OPTIMAL
        num_asignaciones = len(resultado_parcial['asignaciones'])

        resultado_final = {
            'success': True,
            'status': resultado_parcial['status'],
            'es_optima': es_optima,
            'asignaciones': resultado_parcial['asignaciones'],
            'num_asignaciones': num_asignaciones,
            'penalizacion_total': resultado_parcial['objetivo'],
            'tiempo_ejecucion': resultado_parcial['tiempo_resolucion'],
            'validacion': reporte_validacion,
            'mensaje': f"Solución {'ÓPTIMA' if es_optima else 'FACTIBLE'} encontrada con {num_asignaciones} asignaciones."
        }
        
        logger.info(f"Resultado final construido. Success: {resultado_final['success']}, Asignaciones: {num_asignaciones}")
        return resultado_final

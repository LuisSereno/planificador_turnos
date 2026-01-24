# -*- coding: utf-8 -*-
"""Módulo de generación de turnos (compatibilidad con código legacy)."""
import logging
from datetime import timedelta, datetime
from ortools.sat.python import cp_model
from .generador_patrones import AplicadorPatrones
from .generador_refactorizado import GeneradorTurnos as GeneradorTurnosRefactorizado
from .validador import ValidadorRestricciones as ValidadorRestriccionesNuevo

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    fh = logging.FileHandler('planificacion_debug.log', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class GeneradorTurnos:
    """Wrapper para compatibilidad con código legacy. Delega a GeneradorTurnosRefactorizado."""

    def __init__(self, configuracion):
        self._gen = GeneradorTurnosRefactorizado(configuracion)
        self.configuracion = configuracion
        self.model = self._gen.model
        self.num_dias = self._gen.num_dias
        self.enfermeras = self._gen.enfermeras
        self.turnos = self._gen.turnos
        self.num_enfermeras = self._gen.num_enfermeras
        self.num_turnos = self._gen.num_turnos
        self.shifts = self._gen.administrador_variables.shifts
        self.offdays = self._gen.administrador_variables.offdays
        self.turnos_map = self._gen.turnos_map
        self.demanda = self._gen.demanda

    def generar(self):
        """Genera la planificación usando el nuevo sistema."""
        return self._gen.generar()

    def resolver(self):
        """Alias para compatibilidad legacy - resuelve el modelo."""
        return self.generar()


class ValidadorRestricciones:
    """Wrapper para compatibilidad con código legacy. Delega a ValidadorRestriccionesNuevo."""

    def __init__(self, configuracion, resultado):
        self._validador = ValidadorRestriccionesNuevo(configuracion, resultado)
        self.configuracion = configuracion
        self.resultado = resultado
        self.violaciones = self._validador.violaciones
        self.exitos = self._validador.exitos

    def validar(self):
        """Valida la solución usando el nuevo validador."""
        return self._validador.validar()

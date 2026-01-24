# -*- coding: utf-8 -*-
"""Módulo para administrar variables del modelo de optimización."""
import logging

logger = logging.getLogger(__name__)


class AdministradorVariables:
    """Maneja la creación de variables de decisión del modelo."""

    def __init__(self, modelo, num_enfermeras, num_dias, num_turnos, turnos_map):
        self.model = modelo
        self.num_enfermeras = num_enfermeras
        self.num_dias = num_dias
        self.num_turnos = num_turnos
        self.turnos_map = turnos_map
        self.shifts = {}
        self.offdays = {}
        self.extraoffdays = {}

    def crear_todas(self):
        """Crea todas las variables necesarias."""
        self._crear_shifts()
        self._crear_offdays()
        self._crear_extraoffdays()

    def _crear_shifts(self):
        """Crea variables de turnos (shifts)."""
        total_shifts = self.num_enfermeras * self.num_dias * self.num_turnos
        logger.info(f"Creamos {total_shifts} variables de turno (shifts)")

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                for t in range(self.num_turnos):
                    self.shifts[e, d, t] = self.model.NewBoolVar(f'e{e}d{d}t{t}')

    def _crear_offdays(self):
        """Crea variables de días libres (offdays)."""
        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                self.offdays[e, d] = self.model.NewBoolVar(f'off_e{e}d{d}')

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                turnos_ese_dia = [self.shifts[e, d, t] for t in range(self.num_turnos)]
                self.model.Add(sum(turnos_ese_dia) + self.offdays[e, d] == 1)

        logger.info(f"✓ Creadas {self.num_enfermeras * self.num_dias} variables de días libres (offdays)")

    def _crear_extraoffdays(self):
        """Crea variables de días libres extra (después de turno nocturno)."""
        idx_N = self.turnos_map.get('NOCHE')
        if idx_N is None:
            return

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                self.extraoffdays[e, d] = self.model.NewBoolVar(f'extraoff_e{e}d{d}')

                if d == 0:
                    self.model.Add(self.extraoffdays[e, d] == 0)
                else:
                    noche_anterior = self.shifts[e, d - 1, idx_N]
                    self.model.AddBoolAnd([self.offdays[e, d], noche_anterior.Not()]).OnlyEnforceIf(
                        self.extraoffdays[e, d])
                    self.model.AddImplication(self.extraoffdays[e, d], self.offdays[e, d])
                    self.model.AddImplication(self.extraoffdays[e, d], noche_anterior.Not())

        logger.info(
            f"✓ Creadas {self.num_enfermeras * self.num_dias} variables de días libres extra (extraoffdays)")

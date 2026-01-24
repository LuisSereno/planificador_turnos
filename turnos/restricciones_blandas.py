# -*- coding: utf-8 -*-
"""Módulo para aplicar restricciones blandas al modelo de optimización."""
import logging

logger = logging.getLogger(__name__)


class AplicadorRestriccionesBlandas:
    """Maneja la aplicación de restricciones blandas como objetivos de penalización."""

    def __init__(self, modelo, turnos_map, turnos, num_enfermeras, num_dias, shifts, configuracion, demanda, patrones_penalties):
        self.model = modelo
        self.turnos_map = turnos_map
        self.turnos = turnos
        self.num_enfermeras = num_enfermeras
        self.num_dias = num_dias
        self.shifts = shifts
        self.configuracion = configuracion
        self.demanda = demanda
        self.patrones_penalties = patrones_penalties
        self.rb = self._obtener_restricciones_blandas()

    def _obtener_restricciones_blandas(self):
        """Obtiene las restricciones blandas de la configuración."""
        rb = self.configuracion.restricciones_blandas
        if isinstance(rb, list):
            logger.info(f"RB array: {len(rb)}")
            return rb
        if isinstance(rb, dict):
            logger.info(f"RB dict: {len(rb)}")
            return list(rb.values())
        logger.info("RB vacías")
        return []

    def aplicar_todas(self):
        """Aplica todas las restricciones blandas como función objetivo."""
        penalties = []

        penalties.extend(self._aplicar_equidad_turnos())
        penalties.extend(self._aplicar_minimizar_noches())
        penalties.extend(self._aplicar_demanda_optima())
        penalties.extend(self.patrones_penalties)

        if penalties:
            self._construir_funcion_objetivo(penalties)

    def _aplicar_equidad_turnos(self):
        """RB001: Equidad en distribución de turnos."""
        penalties = []
        id_map = {r.get('id'): r for r in self.rb}

        if 'RB001' in id_map or any(r.get('nombre') == 'equidadturnos' for r in self.rb):
            peso = next((r.get('peso', 10) for r in self.rb if r.get('nombre') == 'equidadturnos'), 10)

            contadores_por_enfermera = []
            for e in range(self.num_enfermeras):
                contador = self.model.NewIntVar(0, self.num_dias * len(self.turnos), f'total_turnos_e{e}')
                self.model.Add(contador == sum(
                    [self.shifts[e, d, t] for d in range(self.num_dias) for t in range(len(self.turnos))]))
                contadores_por_enfermera.append(contador)

            max_turnos = self.model.NewIntVar(0, self.num_dias * len(self.turnos), 'max_turnos')
            min_turnos = self.model.NewIntVar(0, self.num_dias * len(self.turnos), 'min_turnos')

            self.model.AddMaxEquality(max_turnos, contadores_por_enfermera)
            self.model.AddMinEquality(min_turnos, contadores_por_enfermera)

            diferencia = self.model.NewIntVar(0, self.num_dias * len(self.turnos), 'diferencia_turnos')
            self.model.Add(diferencia == max_turnos - min_turnos)

            penalties.append((diferencia, peso, 'equidad_turnos'))
            logger.info(f"✓ RB001: Equidad en distribución de turnos (peso {peso})")

        return penalties

    def _aplicar_minimizar_noches(self):
        """RB002: Minimizar turnos nocturnos."""
        penalties = []
        idx_N = self.turnos_map.get('NOCHE')
        id_map = {r.get('id'): r for r in self.rb}

        if 'RB002' in id_map or any(r.get('nombre') == 'minimizarnoches' for r in self.rb):
            if idx_N is not None:
                peso = next((r.get('peso', 6) for r in self.rb if r.get('nombre') == 'minimizarnoches'), 6)

                total_noches = self.model.NewIntVar(0, self.num_enfermeras * self.num_dias, 'total_noches')
                self.model.Add(total_noches == sum(
                    [self.shifts[e, d, idx_N] for e in range(self.num_enfermeras) for d in range(self.num_dias)]))

                penalties.append((total_noches, peso, 'minimizar_noches'))
                logger.info(f"✓ RB002: Minimizar turnos nocturnos (peso {peso})")

        return penalties

    def _aplicar_demanda_optima(self):
        """RB003: Preferir cubrir demanda óptima."""
        penalties = []

        for t in range(len(self.turnos)):
            nombre = self.turnos[t].nombre
            demanda_value = self.demanda.get(nombre)

            if isinstance(demanda_value, dict):
                optimo = demanda_value.get('optimo')
                if optimo:
                    for d in range(self.num_dias):
                        personal = sum([self.shifts[e, d, t] for e in range(self.num_enfermeras)])
                        desviacion = self.model.NewIntVar(-self.num_enfermeras, self.num_enfermeras,
                                                          f'desv_{nombre}_d{d}')
                        self.model.Add(desviacion == personal - optimo)

                        desviacion_abs = self.model.NewIntVar(0, self.num_enfermeras, f'desv_abs_{nombre}_d{d}')
                        self.model.AddAbsEquality(desviacion_abs, desviacion)

                        penalties.append((desviacion_abs, 3, f'demanda_optima_{nombre}_d{d}'))

        return penalties

    def _construir_funcion_objetivo(self, penalties):
        """Construye la función objetivo basada en penalizaciones."""
        logger.info(f"Construyendo función objetivo con {len(penalties)} penalizaciones")
        terminos_objetivo = []

        for penalty_var, peso, descripcion in penalties:
            termino = self.model.NewIntVar(0, peso * self.num_dias * self.num_enfermeras, f'termino_{descripcion}')
            self.model.Add(termino == penalty_var * peso)
            terminos_objetivo.append(termino)

        objetivo_total = self.model.NewIntVar(
            0,
            sum([peso * self.num_dias * self.num_enfermeras for _, peso, _ in penalties]),
            'objetivo_total'
        )
        self.model.Add(objetivo_total == sum(terminos_objetivo))
        self.model.Minimize(objetivo_total)
        logger.info("✓ Función objetivo configurada")

# -*- coding: utf-8 -*-
"""Módulo para aplicar restricciones duras al modelo de optimización."""
import logging

logger = logging.getLogger(__name__)


class AplicadorRestriccionesDuras:
    """Maneja la aplicación de todas las restricciones duras."""

    def __init__(self, modelo, turnos_map, turnos, num_enfermeras, num_dias, shifts, offdays, configuracion, demanda):
        self.model = modelo
        self.turnos_map = turnos_map
        self.turnos = turnos
        self.num_enfermeras = num_enfermeras
        self.num_dias = num_dias
        self.shifts = shifts
        self.offdays = offdays
        self.configuracion = configuracion
        self.demanda = demanda
        self.rd = self._obtener_restricciones_duras()

    def _obtener_restricciones_duras(self):
        """Obtiene las restricciones duras de la configuración."""
        rd = self.configuracion.restricciones_duras
        if isinstance(rd, list):
            logger.info(f"RD array: {len(rd)}")
            return rd
        if isinstance(rd, dict):
            logger.info(f"RD dict: {len(rd)}")
            return list(rd.values())
        logger.info("RD vacías")
        return []

    def aplicar_todas(self):
        """Aplica todas las restricciones duras."""
        self.aplicar_descanso_12h()
        self.aplicar_cobertura_minima_maxima()
        self.aplicar_dias_libres_anuales()
        self.aplicar_descanso_semanal()
        self.aplicar_max_turnos_consecutivos()

    def aplicar_descanso_12h(self):
        """RD006: Descanso mínimo de 12 horas entre turnos."""
        restricciones = 0

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                for t1 in range(len(self.turnos)):
                    for t2 in range(t1 + 1, len(self.turnos)):
                        self.model.Add(self.shifts[e, d, t1] + self.shifts[e, d, t2] <= 1)
                        restricciones += 1

        idx_noche = self.turnos_map.get('NOCHE')
        idx_manana = self.turnos_map.get('MANANA')
        idx_tarde = self.turnos_map.get('TARDE')

        if idx_noche is not None and idx_manana is not None:
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias - 1):
                    self.model.Add(self.shifts[e, d, idx_noche] + self.shifts[e, d + 1, idx_manana] <= 1)
                    restricciones += 1

        if idx_tarde is not None and idx_manana is not None:
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias - 1):
                    self.model.Add(self.shifts[e, d, idx_tarde] + self.shifts[e, d + 1, idx_manana] <= 1)
                    restricciones += 1

        logger.info(f"✓ RD006 Descanso 12h - {restricciones} restricciones aplicadas")

    def aplicar_cobertura_minima_maxima(self):
        """RD019: Cobertura mínima y máxima por turno."""
        logger.info(f"Aplicando RD019 con demanda: {self.demanda}")
        for d in range(self.num_dias):
            for t in range(len(self.turnos)):
                nombre = self.turnos[t].nombre
                demanda_value = self.demanda.get(nombre)

                req_min, req_optimo, req_max = 1, None, self.num_enfermeras

                if isinstance(demanda_value, dict):
                    req_min = demanda_value.get('min', 1)
                    req_optimo = demanda_value.get('optimo')
                    req_max = demanda_value.get('max', self.num_enfermeras)
                    logger.debug(
                        f"  - {nombre} d{d}: min={req_min} requerido, optimo={req_optimo} preferido, max={req_max} límite")
                elif isinstance(demanda_value, (int, float)):
                    req_min = int(demanda_value)
                    logger.debug(f"  - {nombre} d{d}: min={req_min} requerido, max={req_max} límite")

                personal_asignado = sum([self.shifts[e, d, t] for e in range(self.num_enfermeras)])

                if req_min > 0:
                    self.model.Add(personal_asignado >= req_min)
                self.model.Add(personal_asignado <= req_max)

    def aplicar_dias_libres_anuales(self):
        """RD017/RD018: Días libres mínimos por enfermera."""
        dias_libres_requeridos = max(1, int(self.num_dias / 365 * 28))
        for e in range(self.num_enfermeras):
            dias_trabajados = sum(
                [self.shifts[e, d, t] for d in range(self.num_dias) for t in range(len(self.turnos))])
            self.model.Add(dias_trabajados <= self.num_dias - dias_libres_requeridos)
        logger.info(f"✓ RD017/RD018: Mínimo {dias_libres_requeridos} días libres por enfermera")

    def aplicar_descanso_semanal(self):
        """RD007: Descanso semanal."""
        if self.num_dias >= 300:
            num_semanas = self.num_dias // 7
            for e in range(self.num_enfermeras):
                for semana in range(num_semanas):
                    inicio_semana = semana * 7
                    fin_semana = min((semana + 1) * 7, self.num_dias)
                    turnos_en_semana = sum(
                        [self.shifts[e, d, t] for d in range(inicio_semana, fin_semana) for t in range(len(self.turnos))])
                    self.model.Add(turnos_en_semana <= fin_semana - inicio_semana - 1)
            logger.info("✓ RD007: Descanso semanal aplicado (1 día libre cada 7 días)")
        else:
            for e in range(self.num_enfermeras):
                dias_libres_totales = sum([self.offdays[e, d] for d in range(self.num_dias)])
                self.model.Add(dias_libres_totales >= 1)
            logger.info(f"✓ RD007 ADAPTADA para {self.num_dias} días: mínimo 1 día libre total")

    def aplicar_max_turnos_consecutivos(self):
        """Aplica límite de turnos consecutivos."""
        restriccion_max_consec = next((r for r in self.rd if r.get('nombre') == 'turnosconsecutivosmax'), None)
        if restriccion_max_consec:
            max_consecutivos = restriccion_max_consec.get('parametros', {}).get('max', 5)
            ventana = max_consecutivos + 1
            for e in range(self.num_enfermeras):
                for inicio in range(self.num_dias - ventana + 1):
                    turnos_ventana = []
                    for offset in range(ventana):
                        dia = inicio + offset
                        for t in range(len(self.turnos)):
                            turnos_ventana.append(self.shifts[e, dia, t])
                    if turnos_ventana:
                        self.model.Add(sum(turnos_ventana) <= max_consecutivos)
            logger.info(f"✓ RD: Máximo {max_consecutivos} turnos consecutivos")

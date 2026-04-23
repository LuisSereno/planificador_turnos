# -*- coding: utf-8 -*-
"""Módulo para aplicar restricciones duras al modelo de optimización."""
import logging
from datetime import timedelta, datetime
from .dominio.normalizacion import normalizar_nombre

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

        # 1. Prohibir más de un turno por día (ya existente)
        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                for t1 in range(len(self.turnos)):
                    for t2 in range(t1 + 1, len(self.turnos)):
                        self.model.Add(self.shifts[e, d, t1] + self.shifts[e, d, t2] <= 1)
                        restricciones += 1

        # 2. Prohibir secuencias que violen el descanso de 12h entre días consecutivos
        # Iteramos sobre todos los pares de turnos posibles
        for t1_idx, t1 in enumerate(self.turnos):
            for t2_idx, t2 in enumerate(self.turnos):
                # Calculamos el fin del turno 1 y el inicio del turno 2
                # Asumimos que t1 es en el día D y t2 es en el día D+1
                
                # Fin de t1: si termina al día siguiente (hora_fin < hora_inicio), sumamos 24h
                fin_t1 = t1.hora_fin.hour + t1.hora_fin.minute / 60.0
                inicio_t1 = t1.hora_inicio.hour + t1.hora_inicio.minute / 60.0
                
                if fin_t1 <= inicio_t1:
                    fin_t1 += 24  # Termina al día siguiente
                
                # Inicio de t2 (en el día siguiente, así que sumamos 24h a su hora base)
                inicio_t2 = t2.hora_inicio.hour + t2.hora_inicio.minute / 60.0 + 24
                
                # Diferencia en horas
                horas_descanso = inicio_t2 - fin_t1
                
                # Si el descanso es menor a 12 horas, prohibimos la secuencia
                if horas_descanso < 12:
                    logger.info(f"  - Prohibiendo secuencia {t1.nombre} (Día D) -> {t2.nombre} (Día D+1): Solo {horas_descanso:.1f}h descanso")
                    for e in range(self.num_enfermeras):
                        for d in range(self.num_dias - 1):
                            self.model.Add(self.shifts[e, d, t1_idx] + self.shifts[e, d + 1, t2_idx] <= 1)
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
        restriccion_max_consec = next((r for r in self.rd if normalizar_nombre(r.get('nombre', '')) == 'TURNO_CONSECUTIVOS_MAX'), None)
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

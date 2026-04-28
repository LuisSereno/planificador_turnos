# -*- coding: utf-8 -*-
"""
Utilidades para cálculos de tiempo y descanso entre turnos.
"""
from datetime import datetime, timedelta


def calcular_descanso_entre_turnos(fecha_turno_a, turno_a_info, fecha_turno_b, turno_b_info):
    """
    Calcula el descanso real en horas entre el fin del turno A y el inicio del turno B.

    Args:
        fecha_turno_a: date del día asignado al turno A
        turno_a_info: TurnoInfo (o similar) con atributos hora_inicio y hora_fin
        fecha_turno_b: date del día asignado al turno B
        turno_b_info: TurnoInfo (o similar) con atributos hora_inicio y hora_fin

    Returns:
        float: horas de descanso (puede ser negativo si los turnos se solapan)
    """
    # Fin del turno A (puede cruzar medianoche)
    fin_a = datetime.combine(fecha_turno_a, turno_a_info.hora_fin)
    inicio_a = datetime.combine(fecha_turno_a, turno_a_info.hora_inicio)
    if fin_a < inicio_a:
        fin_a += timedelta(days=1)

    # Inicio del turno B
    inicio_b = datetime.combine(fecha_turno_b, turno_b_info.hora_inicio)

    descanso = (inicio_b - fin_a).total_seconds() / 3600.0
    return descanso

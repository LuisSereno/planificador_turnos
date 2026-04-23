# -*- coding: utf-8 -*-
"""
Vocabulario canónico para restricciones, patrones y objetivos.
Define los identificadores oficiales que deben usar el motor, validador y configuración.
"""

# ============================================================================
# RESTRICCIONES DURAS CANÓNICAS
# ============================================================================
RESTRICCIONES_DURAS_CANONICAS = {
    'TURNO_POR_DIA': 'Un solo turno por día por enfermera',
    'TURNO_CONSECUTIVOS_MAX': 'Máximo turnos consecutivos sin descanso',
    'DESCANSO_ENTRE_TURNOS': 'Descanso mínimo entre turnos (ej. 12h)',
    'COBERTURA_MINIMA': 'Cobertura mínima requerida por turno',
    'COBERTURA_MAXIMA': 'Cobertura máxima permitida por turno',
    'DIAS_LIBRES_ANUALES': 'Días libres anuales mínimos',
    'DESCANSO_SEMANAL': 'Descanso semanal obligatorio',
    'NOCHES_CONSECUTIVAS_MAX': 'Máximo noches consecutivas',
}

# ============================================================================
# RESTRICCIONES BLANDAS CANÓNICAS
# ============================================================================
RESTRICCIONES_BLANDAS_CANONICAS = {
    'EQUIDAD_TURNOS': 'Equidad en distribución de turnos',
    'MINIMIZAR_NOCHES': 'Minimizar asignación de noches',
    'EQUIDAD_NOCHES': 'Equidad en número de noches',
    'EQUIDAD_FINDES': 'Equidad en fines de semana trabajados',
    'EQUIDAD_FESTIVOS': 'Equidad en festivos trabajados',
    'MINIMIZAR_CAMBIOS': 'Minimizar cambios de turno bruscos',
    'PREFERENCIAS_ENFERMERA': 'Respetar preferencias individuales',
}

# ============================================================================
# PATRONES CANÓNICOS
# ============================================================================
PATRONES_CANONICOS = {
    'SECUENCIA_OBLIGATORIA': 'Secuencia obligatoria de turnos (ej. M→T→N)',
    'DESCANSO_POST_TURNO': 'Descanso obligatorio post-turno específico',
    'MAX_CONSECUTIVOS': 'Máximo turnos consecutivos de un tipo',
    'ROTACION_CICLICA': 'Rotación cíclica base del cuadrante',
    'COBERTURA_MINIMA': 'Cobertura mínima por turno',
    'BLOQUEO_TRANSICION': 'Transición bloqueada entre turnos',
    'DISTRIBUCION_EQUITATIVA': 'Distribución equitativa de carga',
}

# ============================================================================
# TIPOS DE CELDA EN PLANILLA
# ============================================================================
TIPOS_CELDA = {
    'TURNO': 'Turno normal asignado',
    'LIBRE': 'Día libre (sin asignación)',
    'VACACIONES': 'Vacaciones planificadas',
    'PERMISO': 'Permiso retribuido o no retribuido',
    'BAJA': 'Baja médica',
    'FORMACION': 'Jornada de formación',
    'ASIGNACION_FIJA': 'Asignación fija inamovible',
}

# ============================================================================
# TIPOS DE INCIDENCIA
# ============================================================================
TIPOS_INCIDENCIA = {
    'VACACIONES': 'Vacaciones planificadas',
    'PERMISO': 'Permiso (retribuido/no retribuido)',
    'BAJA': 'Baja médica o accidente',
    'FORMACION': 'Jornada de formación',
    'LIBRANZA_BLOQUEADA': 'Libranza bloqueada (no asignar turno)',
    'ASIGNACION_FIJA': 'Asignación fija a turno específico',
}

# ============================================================================
# NIVELES DE PRIORIDAD LEXICOGRÁFICA DEL SOLVER
# ============================================================================
PRIORIDADES_SOLVER = {
    1: {
        'nombre': 'RESTRICCIONES_DURAS',
        'descripcion': 'Cumplir TODAS las restricciones duras',
        'peso_relativo': 'CRÍTICO',
    },
    2: {
        'nombre': 'MINIMIZAR_DESVIACION_ROTACION',
        'descripcion': 'Minimizar celdas que se desvíen de la rotación base',
        'peso_relativo': 'ALTO',
    },
    3: {
        'nombre': 'MINIMIZAR_DESVIACION_HORAS_MENSUALES',
        'descripcion': 'Cada enfermera cerca de sus horas_mes_objetivo',
        'peso_relativo': 'ALTO',
    },
    4: {
        'nombre': 'MINIMIZAR_DESVIACION_SALDO_ANUAL',
        'descripcion': 'Considerar horas_acumuladas_previas del balance histórico',
        'peso_relativo': 'MEDIO-ALTO',
    },
    5: {
        'nombre': 'EQUILIBRAR_NOCHES',
        'descripcion': 'Minimizar varianza de noches entre enfermeras',
        'peso_relativo': 'MEDIO',
    },
    6: {
        'nombre': 'EQUILIBRAR_FINDES',
        'descripcion': 'Minimizar varianza de fines de semana trabajados',
        'peso_relativo': 'MEDIO',
    },
    7: {
        'nombre': 'EQUILIBRAR_FESTIVOS',
        'descripcion': 'Minimizar varianza de festivos trabajados',
        'peso_relativo': 'MEDIO',
    },
}

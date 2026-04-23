# -*- coding: utf-8 -*-
"""
Capa de normalización de nombres para restricciones, patrones y configuraciones.
Traduce nombres legacy a identificadores canónicos con logging de warnings.
"""
import logging

logger = logging.getLogger(__name__)

# Mapeo de nombres legacy → canónicos para restricciones duras
RESTRICCIONES_DURAS_MAP = {
    'turnos_consecutivos_max': 'TURNO_CONSECUTIVOS_MAX',
    'turnosconsecutivosmax': 'TURNO_CONSECUTIVOS_MAX',
    'turnos_nocturnos_consecutivos_max': 'NOCHES_CONSECUTIVAS_MAX',
    'turnosnocturnosconsecutivosmax': 'NOCHES_CONSECUTIVAS_MAX',
    'un_turno_por_dia': 'TURNO_POR_DIA',
    'unturnopordia': 'TURNO_POR_DIA',
    'descanso_12h': 'DESCANSO_ENTRE_TURNOS',
    'descanso12h': 'DESCANSO_ENTRE_TURNOS',
    'cobertura_minima': 'COBERTURA_MINIMA',
    'coberturaminima': 'COBERTURA_MINIMA',
    'cobertura_maxima': 'COBERTURA_MAXIMA',
    'coberturamaxima': 'COBERTURA_MAXIMA',
    'dias_libres_anuales': 'DIAS_LIBRES_ANUALES',
    'diaslibresanuales': 'DIAS_LIBRES_ANUALES',
    'descanso_semanal': 'DESCANSO_SEMANAL',
    'descansosemanal': 'DESCANSO_SEMANAL',
}

# Mapeo de nombres legacy → canónicos para restricciones blandas
RESTRICCIONES_BLANDAS_MAP = {
    'equidad_turnos': 'EQUIDAD_TURNOS',
    'equidadturnos': 'EQUIDAD_TURNOS',
    'minimizar_noches': 'MINIMIZAR_NOCHES',
    'minimizarnoches': 'MINIMIZAR_NOCHES',
    'equidad_noches': 'EQUIDAD_NOCHES',
    'equidadnoches': 'EQUIDAD_NOCHES',
    'equidad_fines_semana': 'EQUIDAD_FINDES',
    'equidadfinessemana': 'EQUIDAD_FINDES',
    'equidad_findes': 'EQUIDAD_FINDES',
    'equidadfindes': 'EQUIDAD_FINDES',
    'equidad_festivos': 'EQUIDAD_FESTIVOS',
    'equidadfestivos': 'EQUIDAD_FESTIVOS',
    'minimizar_cambios': 'MINIMIZAR_CAMBIOS',
    'minimizarcambios': 'MINIMIZAR_CAMBIOS',
}

# Mapeo de nombres legacy → canónicos para patrones
PATRONES_MAP = {
    'SECUENCIA_TURNOS': 'SECUENCIA_OBLIGATORIA',
    'ROTACION_TURNOS': 'ROTACION_CICLICA',
    'ROTACION': 'ROTACION_CICLICA',
    'DESCANSO_POST_TURNO': 'DESCANSO_POST_TURNO',
    'MAX_CONSECUTIVOS': 'MAX_CONSECUTIVOS',
    'COBERTURA_MINIMA': 'COBERTURA_MINIMA',
    'BLOQUEO_TRANSICION': 'BLOQUEO_TRANSICION',
    'DISTRIBUCION_EQUITATIVA': 'DISTRIBUCION_EQUITATIVA',
}

# Mapeo combinado (todos los tipos)
NORMALIZACION_MAP = {
    **RESTRICCIONES_DURAS_MAP,
    **RESTRICCIONES_BLANDAS_MAP,
    **PATRONES_MAP,
}


def normalizar_nombre(nombre: str) -> str:
    """
    Normaliza un nombre de restricción o patrón a su forma canónica.
    
    Args:
        nombre: Nombre original (puede ser legacy o ya canónico)
        
    Returns:
        Nombre normalizado en formato canónico (UPPER_SNAKE_CASE)
    """
    if not nombre:
        return nombre
    
    # Si ya está en el mapeo, normalizar
    if nombre in NORMALIZACION_MAP:
        canonical = NORMALIZACION_MAP[nombre]
        if canonical != nombre:
            logger.warning(
                f"Nombre legacy normalizado: '{nombre}' → '{canonical}'"
            )
        return canonical
    
    # Si no está en el mapeo, asumir que ya es canónico o devolver como está
    # Convertir a uppercase para consistencia
    return nombre.upper()


def normalizar_restriccion(restriccion: dict) -> dict:
    """
    Normaliza una restricción (dura o blanda) completa.
    
    Args:
        restriccion: Diccionario con campos de restricción
        
    Returns:
        Diccionario con nombre normalizado
    """
    if not isinstance(restriccion, dict):
        return restriccion
    
    resultado = restriccion.copy()
    if 'nombre' in resultado:
        resultado['nombre'] = normalizar_nombre(resultado['nombre'])
    
    return resultado


def normalizar_patron(patron: dict) -> dict:
    """
    Normaliza un patrón completo.
    
    Args:
        patron: Diccionario con campos de patrón
        
    Returns:
        Diccionario con tipo normalizado
    """
    if not isinstance(patron, dict):
        return patron
    
    resultado = patron.copy()
    if 'tipo' in resultado:
        resultado['tipo'] = normalizar_nombre(resultado['tipo'])
    
    return resultado


def normalizar_lista_restricciones(restricciones: list) -> list:
    """
    Normaliza una lista de restricciones.
    
    Args:
        restricciones: Lista de diccionarios de restricciones
        
    Returns:
        Lista con restricciones normalizadas
    """
    if not isinstance(restricciones, list):
        return restricciones
    
    return [normalizar_restriccion(r) for r in restricciones]


def normalizar_lista_patrones(patrones: list) -> list:
    """
    Normaliza una lista de patrones.
    
    Args:
        patrones: Lista de diccionarios de patrones
        
    Returns:
        Lista con patrones normalizados
    """
    if not isinstance(patrones, list):
        return patrones
    
    return [normalizar_patron(p) for p in patrones]


def normalizar_lista_nombres(nombres: list, eliminar_duplicados: bool = False) -> list:
    """
    Normaliza una lista de nombres de restricciones/patrones.
    
    Args:
        nombres: Lista de nombres (legacy o canónicos)
        eliminar_duplicados: Si True, elimina duplicados después de normalizar
    
    Returns:
        Lista de nombres normalizados
    """
    resultado = [normalizar_nombre(n) for n in nombres]
    
    if eliminar_duplicados:
        seen = set()
        unique = []
        for n in resultado:
            if n not in seen:
                seen.add(n)
                unique.append(n)
        return unique
    
    return resultado

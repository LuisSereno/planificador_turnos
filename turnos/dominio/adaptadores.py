# -*- coding: utf-8 -*-
"""
Adaptadores de compatibilidad para configuraciones legacy.
Traduce configuraciones antiguas al nuevo formato de dominio con logging de warnings.
"""
import logging
from typing import Dict, List, Optional
from datetime import date

from .normalizacion import normalizar_nombre, normalizar_lista_restricciones
from .vocabulario import RESTRICCIONES_DURAS_CANONICAS, PATRONES_CANONICOS
from .dtos import (
    TipoIncidencia,
    Incidencia,
    RotacionCiclo,
    TurnoInfo,
)

logger = logging.getLogger(__name__)


class AdaptadorConfiguracionLegacy:
    """
    Traduce configuraciones antiguas (JSON libre) al nuevo formato de dominio.
    
    Ejemplo de uso:
        adaptador = AdaptadorConfiguracionLegacy()
        config_nueva = adaptador.adaptar(config_antigua)
    """
    
    def adaptar(self, config_antigua: dict) -> dict:
        """
        Adapta una configuración legacy al nuevo formato.
        
        Args:
            config_antigua: Diccionario con nomenclatura antigua
            
        Returns:
            Diccionario con nomenclatura normalizada y estructura nueva
        """
        config_nueva = {}
        
        # Normalizar restricciones duras
        if 'restricciones_duras' in config_antigua:
            config_nueva['restricciones_duras'] = normalizar_lista_restricciones(
                config_antigua['restricciones_duras']
            )
            logger.info("Restricciones duras normalizadas")
        
        # Normalizar restricciones blandas
        if 'restricciones_blandas' in config_antigua:
            from .normalizacion import normalizar_lista_restricciones
            config_nueva['restricciones_blandas'] = normalizar_lista_restricciones(
                config_antigua['restricciones_blandas']
            )
            logger.info("Restricciones blandas normalizadas")
        
        # Normalizar patrones
        if 'patrones' in config_antigua:
            from .normalizacion import normalizar_lista_patrones
            config_nueva['patrones'] = normalizar_lista_patrones(
                config_antigua['patrones']
            )
            logger.info("Patrones normalizados")
        
        # Adaptar otros campos
        for key, value in config_antigua.items():
            if key not in ['restricciones_duras', 'restricciones_blandas', 'patrones']:
                config_nueva[key] = value
        
        logger.warning(
            f"Configuración legacy adaptada: {len(config_antigua)} campos procesados"
        )
        
        return config_nueva


class AdaptadorPatronesLegacy:
    """
    Convierte patrones ManyToMany a JSON normalizado.
    """
    
    def convertir_patrones_m2m_a_json(self, patrones_queryset) -> list:
        """
        Convierte un queryset de patrones (ManyToMany) a lista de diccionarios.
        
        Args:
            patrones_queryset: Queryset de objetos PatronTurno
            
        Returns:
            Lista de diccionarios con formato normalizado
        """
        patrones_json = []
        
        for patron in patrones_queryset:
            patron_dict = {
                'id': patron.id if hasattr(patron, 'id') else None,
                'nombre': patron.nombre if hasattr(patron, 'nombre') else str(patron),
                'tipo': getattr(patron, 'tipo', None),
            }
            
            # Normalizar el nombre del patrón
            if patron_dict['tipo']:
                patron_dict['tipo'] = normalizar_nombre(patron_dict['tipo'])
            
            patrones_json.append(patron_dict)
        
        logger.warning(
            f"Convertidos {len(patrones_json)} patrones de ManyToMany a JSON"
        )
        
        return patrones_json


class AdaptadorRestriccionesLegacy:
    """
    Normaliza nombres de restricciones en configuraciones existentes.
    """
    
    def normalizar_restricciones_en_dict(self, config: dict) -> dict:
        """
        Normaliza todos los nombres de restricciones en un diccionario.
        
        Args:
            config: Diccionario con restricciones
            
        Returns:
            Diccionario con nombres normalizados
        """
        config_normalizada = config.copy()
        
        # Normalizar en restricciones_duras
        if 'restricciones_duras' in config_normalizada:
            for i, restriccion in enumerate(config_normalizada['restricciones_duras']):
                if isinstance(restriccion, dict) and 'nombre' in restriccion:
                    restriccion['nombre'] = normalizar_nombre(restriccion['nombre'])
        
        # Normalizar en restricciones_blandas
        if 'restricciones_blandas' in config_normalizada:
            for i, restriccion in enumerate(config_normalizada['restricciones_blandas']):
                if isinstance(restriccion, dict) and 'nombre' in restriccion:
                    restriccion['nombre'] = normalizar_nombre(restriccion['nombre'])
        
        logger.info("Restricciones normalizadas en configuración")
        
        return config_normalizada


class AdaptadorIncidenciasLegacy:
    """
    Convierte formatos antiguos de incidencias al nuevo DTO.
    """
    
    def convertir_incidencia(self, incidencia_dict: dict) -> Incidencia:
        """
        Convierte un diccionario legacy de incidencia al DTO Incidencia.
        
        Args:
            incidencia_dict: Diccionario con formato antiguo
            
        Returns:
            Objeto Incidencia del dominio
        """
        # Mapear tipos legacy a enum
        tipo_map = {
            'vacaciones': TipoIncidencia.VACACIONES,
            'VACACIONES': TipoIncidencia.VACACIONES,
            'permiso': TipoIncidencia.PERMISO,
            'PERMISO': TipoIncidencia.PERMISO,
            'baja': TipoIncidencia.BAJA,
            'BAJA': TipoIncidencia.BAJA,
            'formacion': TipoIncidencia.FORMACION,
            'FORMACION': TipoIncidencia.FORMACION,
            'libranza_bloqueada': TipoIncidencia.LIBRANZA_BLOQUEADA,
            'asignacion_fija': TipoIncidencia.ASIGNACION_FIJA,
        }
        
        tipo_str = incidencia_dict.get('tipo', incidencia_dict.get('tipo_incidencia', ''))
        tipo = tipo_map.get(tipo_str, TipoIncidencia.PERMISO)
        
        if tipo_str not in tipo_map:
            logger.warning(f"Tipo de incidencia legacy desconocido: '{tipo_str}' → {tipo.value}")
        
        return Incidencia(
            enfermera_id=incidencia_dict.get('enfermera_id'),
            tipo=tipo,
            fecha_inicio=incidencia_dict.get('fecha_inicio'),
            fecha_fin=incidencia_dict.get('fecha_fin'),
            turno_fijo_id=incidencia_dict.get('turno_fijo_id'),
            observaciones=incidencia_dict.get('observaciones', ''),
        )
    
    def convertir_lista_incidencias(self, incidencias_list: list) -> List[Incidencia]:
        """
        Convierte una lista de diccionarios legacy a lista de DTOs Incidencia.
        
        Args:
            incidencias_list: Lista de diccionarios legacy
            
        Returns:
            Lista de objetos Incidencia
        """
        return [self.convertir_incidencia(inc) for inc in incidencias_list]


class AdaptadorRotacionLegacy:
    """
    Convierte patrones abstractos genéricos a rotaciones cíclicas explícitas.
    """
    
    def convertir_patron_a_rotacion(
        self,
        nombre: str,
        secuencia_turnos: list,
        turnos_info: Dict[int, TurnoInfo],
    ) -> RotacionCiclo:
        """
        Convierte una secuencia abstracta de turnos a un ciclo de rotación explícito.
        
        Args:
            nombre: Nombre del patrón
            secuencia_turnos: Lista de IDs de turnos o None para libres
            turnos_info: Diccionario de información de turnos
            
        Returns:
            Objeto RotacionCiclo
        """
        celdas = []
        for turno_id in secuencia_turnos:
            if turno_id is None:
                celdas.append(None)  # Día libre
            elif turno_id in turnos_info:
                celdas.append(turnos_info[turno_id])
            else:
                logger.warning(f"Turno ID {turno_id} no encontrado en turnos_info")
                celdas.append(None)
        
        logger.warning(
            f"Patrón abstracto '{nombre}' convertido a rotación cíclica de {len(celdas)} días"
        )
        
        return RotacionCiclo(
            nombre=nombre,
            ciclo_dias=len(celdas),
            celdas=celdas,
        )

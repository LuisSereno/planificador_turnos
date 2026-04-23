# -*- coding: utf-8 -*-
"""
Constructor determinista de la rotación base.
Genera la matriz de planificación inicial basada en ciclos de rotación explícitos.
"""
import logging
from datetime import date, timedelta
from typing import List, Dict, Optional

from ..dominio.dtos import (
    MatrizPlanificacion,
    CeldaPlanificacion,
    TipoCelda,
    TurnoInfo,
    RotacionCiclo,
)

logger = logging.getLogger(__name__)


class RotacionBaseBuilder:
    """
    Construye la matriz de planificación base a partir de rotaciones cíclicas.
    
    Esta es la fase 1 del pipeline: generación determinista (sin solver) de la 
    asignación inicial siguiendo los ciclos de rotación configurados.
    """
    
    def __init__(
        self,
        fechas: List[date],
        enfermeras: Dict[int, str],  # id -> nombre
        asignaciones_rotacion: Dict[int, RotacionCiclo],  # enfermera_id -> rotación
        desfases: Dict[int, int],  # enfermera_id -> desfase en días
    ):
        self.fechas = fechas
        self.enfermeras = enfermeras
        self.asignaciones_rotacion = asignaciones_rotacion
        self.desfases = desfases
        
    def construir(self) -> MatrizPlanificacion:
        """
        Construye la matriz de planificación base.
        
        Returns:
            MatrizPlanificacion con todas las celdas asignadas según rotación
        """
        logger.info(f"Construyendo rotación base para {len(self.fechas)} días y {len(self.enfermeras)} enfermeras")
        
        matriz = MatrizPlanificacion(
            fechas=self.fechas,
            enfermeras=self.enfermeras,
        )
        
        fecha_inicio = self.fechas[0]
        
        for enfermera_id, enfermera_nombre in self.enfermeras.items():
            # Obtener rotación y desfase de esta enfermera
            rotacion = self.asignaciones_rotacion.get(enfermera_id)
            desfase = self.desfases.get(enfermera_id, 0)
            
            if not rotacion:
                logger.warning(f"Enfermera {enfermera_nombre} sin rotación asignada")
                continue
            
            # Generar celdas para cada fecha
            for idx, fecha in enumerate(self.fechas):
                dia_en_ciclo = (idx + desfase) % rotacion.ciclo_dias
                turno = rotacion.obtener_turno(dia_en_ciclo)
                
                celda = CeldaPlanificacion(
                    enfermera_id=enfermera_id,
                    enfermera_nombre=enfermera_nombre,
                    fecha=fecha,
                    turno=turno,
                    tipo_celda=TipoCelda.TURNO if turno else TipoCelda.LIBRE,
                    es_modificable=True,
                    pertenece_rotacion_base=True,
                )
                
                matriz.asignar_celda(celda)
        
        logger.info(f"Rotación base construida: {matriz.total_celdas()} celdas")
        return matriz

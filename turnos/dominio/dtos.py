# -*- coding: utf-8 -*-
"""
DTOs (Data Transfer Objects) para el motor de planificación.
Representan las estructuras de datos internas del dominio sin depender de Django models.
"""
from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional
from enum import Enum

# Calendario de festivos inyectable (set de date objects).
# Usar set_calendario_festivos() para configurar.
_calendario_festivos: Optional[set] = None


def set_calendario_festivos(festivos: Optional[set]):
    """Inyecta un conjunto de fechas festivas (date objects) para el dominio."""
    global _calendario_festivos
    _calendario_festivos = festivos


class TipoCelda(Enum):
    """Tipos explícitos de celda en la planilla"""
    TURNO = 'TURNO'
    LIBRE = 'LIBRE'
    VACACIONES = 'VACACIONES'
    PERMISO = 'PERMISO'
    BAJA = 'BAJA'
    FORMACION = 'FORMACION'
    ASIGNACION_FIJA = 'ASIGNACION_FIJA'


class TipoIncidencia(Enum):
    """Tipos de incidencia que afectan la planificación"""
    VACACIONES = 'VACACIONES'
    PERMISO = 'PERMISO'
    BAJA = 'BAJA'
    FORMACION = 'FORMACION'
    LIBRANZA_BLOQUEADA = 'LIBRANZA_BLOQUEADA'
    ASIGNACION_FIJA = 'ASIGNACION_FIJA'


@dataclass
class TurnoInfo:
    """Información de un tipo de turno"""
    id: int
    nombre: str
    hora_inicio: time
    hora_fin: time
    duracion_horas: float
    es_nocturno: bool = False
    es_sustituto_libre: bool = False
    
    @property
    def es_tipo_libre(self) -> bool:
        """True si este turno actúa como 'Libre' (sustituto o sin horas)"""
        return self.es_sustituto_libre or self.duracion_horas == 0


@dataclass
class CeldaPlanificacion:
    """
    Representa una celda individual en la matriz de planificación.
    Una celda es la intersección de una enfermera con una fecha.
    """
    enfermera_id: int
    enfermera_nombre: str
    fecha: date
    turno: Optional[TurnoInfo] = None
    tipo_celda: TipoCelda = TipoCelda.TURNO
    es_modificable: bool = True
    observaciones: str = ''
    
    # Metadata para el solver
    pertenece_rotacion_base: bool = False
    desviacion_de_rotacion: bool = False
    
    # Snapshot inmutable del turno original de la rotacion (Phase 1).
    # No se modifica por fases posteriores (AjustadorHoras, solver, etc.)
    _turno_base_original_id: Optional[int] = None
    
    @property
    def turno_base_original_id(self) -> Optional[int]:
        """ID del turno en la rotacion original (inmutable, sobrevive a ajustes)."""
        return self._turno_base_original_id
    
    @property
    def es_libre(self) -> bool:
        return self.tipo_celda == TipoCelda.LIBRE or (self.turno is None and self.tipo_celda == TipoCelda.TURNO)
    
    @property
    def horas_asignadas(self) -> float:
        if self.turno:
            return self.turno.duracion_horas
        return 0.0
    
    @property
    def es_noche(self) -> bool:
        return self.turno is not None and self.turno.es_nocturno
    
    @property
    def es_fin_de_semana(self) -> bool:
        return self.fecha.weekday() >= 5  # Sábado=5, Domingo=6
    
    @property
    def es_festivo(self) -> bool:
        """Determina si la fecha es festivo.

        Usa el calendario de festivos inyectado via set_calendario_festivos().
        Si no hay calendario configurado, devuelve False.
        """
        if _calendario_festivos is not None:
            return self.fecha in _calendario_festivos
        return False
    
    @property
    def turno_base_id(self):
        """Obtiene el ID del turno base si pertenece a la rotación"""
        return self.turno.id if self.turno and self.pertenece_rotacion_base else None
    
    @property
    def turno_id(self):
        """Obtiene el ID del turno asignado"""
        return self.turno.id if self.turno else None
    
    @turno_id.setter
    def turno_id(self, value):
        """Establece el turno por ID (requiere lookup externo)"""
        # El setter no puede resolver el objeto TurnoInfo directamente
        # Se debe asignar through celda.turno directamente
        pass


@dataclass
class BalanceEnfermera:
    """Balance de horas y carga para una enfermera en un período"""
    enfermera_id: int
    enfermera_nombre: str
    horas_asignadas: float = 0.0
    horas_objetivo: float = 0.0
    desviacion_horas: float = 0.0
    
    turnos_asignados: int = 0
    noches_asignadas: int = 0
    fines_semana_asignados: int = 0
    festivos_asignados: int = 0
    
    # Acumulados históricos
    horas_acumuladas_previas: float = 0.0
    noches_acumuladas: int = 0
    fines_semana_acumulados: int = 0
    festivos_acumulados: int = 0
    
    # Incidencias post-generación
    horas_perdidas_incidencias: float = 0.0
    
    @property
    def horas_totales_con_historico(self) -> float:
        return self.horas_asignadas + self.horas_acumuladas_previas
    
    @property
    def desviacion_porcentaje(self) -> float:
        if self.horas_objetivo == 0:
            return 0.0
        return (self.desviacion_horas / self.horas_objetivo) * 100


@dataclass
class Incidencia:
    """Representa una incidencia que afecta la planificación"""
    enfermera_id: int
    enfermera_nombre: str
    tipo: TipoIncidencia
    fecha_inicio: date
    fecha_fin: date
    turno_fijo: Optional[TurnoInfo] = None
    observaciones: str = ''
    
    def afecta_fecha(self, fecha: date) -> bool:
        return self.fecha_inicio <= fecha <= self.fecha_fin


@dataclass
class RotacionCiclo:
    """Define un ciclo de rotación explícito"""
    nombre: str
    ciclo_dias: int
    celdas: list  # Lista de TurnoInfo o None (para libres)
    
    def obtener_turno(self, dia_offset: int) -> Optional[TurnoInfo]:
        """Obtiene el turno correspondiente a un día dentro del ciclo"""
        indice = dia_offset % self.ciclo_dias
        return self.celdas[indice]


@dataclass
class MatrizPlanificacion:
    """
    Matriz completa de planificación.
    Estructura: {enfermera_id: {fecha: CeldaPlanificacion}}
    """
    celdas: dict = field(default_factory=dict)
    fechas: list = field(default_factory=list)
    enfermeras: dict = field(default_factory=dict)  # id -> nombre
    turnos_disponibles: list = field(default_factory=list)  # IDs de turnos disponibles para el solver
    
    def obtener_celda(self, enfermera_id: int, fecha: date) -> Optional[CeldaPlanificacion]:
        if enfermera_id in self.celdas and fecha in self.celdas[enfermera_id]:
            return self.celdas[enfermera_id][fecha]
        return None
    
    def asignar_celda(self, celda: CeldaPlanificacion):
        if celda.enfermera_id not in self.celdas:
            self.celdas[celda.enfermera_id] = {}
        self.celdas[celda.enfermera_id][celda.fecha] = celda
    
    def obtener_celdas_enfermera(self, enfermera_id: int) -> dict:
        return self.celdas.get(enfermera_id, {})
    
    def obtener_celdas_fecha(self, fecha: date) -> dict:
        """Obtiene todas las celdas de una fecha"""
        resultado = {}
        for enf_id, celdas_enf in self.celdas.items():
            if fecha in celdas_enf:
                resultado[enf_id] = celdas_enf[fecha]
        return resultado
    
    def total_celdas(self) -> int:
        total = 0
        for celdas_enf in self.celdas.values():
            total += len(celdas_enf)
        return total
    
    def clone(self) -> 'MatrizPlanificacion':
        """Crea una copia profunda de la matriz"""
        import copy
        return copy.deepcopy(self)


@dataclass
class ResultadoOverlay:
    """Resultado de aplicar incidencias sobre la planificación generada"""
    matriz_final: MatrizPlanificacion
    celdas_sobreescritas: list = field(default_factory=list)
    # Cada entrada: {enfermera_id, fecha, turno_original_id, tipo_incidencia, horas_perdidas}
    huecos_cobertura: list = field(default_factory=list)
    # Cada entrada: {fecha, turno_id, deficit}


@dataclass
class ResultadoPlanificacion:
    """Resultado estructurado de la planificación"""
    exitosa: bool
    matriz: MatrizPlanificacion
    balances: dict  # enfermera_id -> BalanceEnfermera
    metricas: dict
    
    # Información del solver
    estado_solver: str = ''  # 'OPTIMAL', 'FEASIBLE', 'INFEASIBLE', etc.
    tiempo_resolucion: float = 0.0
    celdas_modificadas: int = 0
    celdas_totales: int = 0
    
    # Validación
    restricciones_duras_cumplidas: bool = True
    violaciones: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    
    @property
    def porcentaje_modificaciones(self) -> float:
        if self.celdas_totales == 0:
            return 0.0
        return (self.celdas_modificadas / self.celdas_totales) * 100

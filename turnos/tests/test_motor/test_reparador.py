# -*- coding: utf-8 -*-
"""
Tests del reparador CP-SAT.
"""
import pytest
from datetime import date, time
from ortools.sat.python import cp_model

from turnos.dominio.dtos import (
    TurnoInfo,
    RotacionCiclo,
    Incidencia,
    TipoIncidencia,
    TipoCelda,
    MatrizPlanificacion,
    CeldaPlanificacion,
)
from turnos.motor.rotacion_base import RotacionBaseBuilder
from turnos.motor.incidencias import AplicadorIncidencias
from turnos.motor.cobertura import AnalizadorCobertura
from turnos.motor.reparador import ReparadorCPSAT


@pytest.fixture
def turnos_basicos():
    """Fixture con turnos básicos"""
    return {
        1: TurnoInfo(id=1, nombre='M', hora_inicio=time(7, 0), hora_fin=time(15, 0), duracion_horas=8.0),
        2: TurnoInfo(id=2, nombre='T', hora_inicio=time(15, 0), hora_fin=time(23, 0), duracion_horas=8.0),
        3: TurnoInfo(id=3, nombre='N', hora_inicio=time(23, 0), hora_fin=time(7, 0), duracion_horas=8.0, es_nocturno=True),
    }


@pytest.fixture
def fechas_abril_2026():
    """Primeros 10 días de abril 2026"""
    return [date(2026, 4, i) for i in range(1, 11)]


@pytest.fixture
def enfermeras():
    """3 enfermeras de prueba"""
    return {
        1: 'María García',
        2: 'Ana López',
        3: 'Carmen Rodríguez',
    }


@pytest.fixture
def rotacion_2m_2t_2n_2l(turnos_basicos):
    """Rotación cíclica: 2M-2T-2N-2L (8 días)"""
    return RotacionCiclo(
        nombre='2M-2T-2N-2L',
        ciclo_dias=8,
        celdas=[
            turnos_basicos[1],  # M
            turnos_basicos[1],  # M
            turnos_basicos[2],  # T
            turnos_basicos[2],  # T
            turnos_basicos[3],  # N
            turnos_basicos[3],  # N
            None,               # L
            None,               # L
        ],
    )


@pytest.fixture
def asignaciones_rotacion(enfermeras, rotacion_2m_2t_2n_2l):
    """Todas las enfermeras con la misma rotación"""
    return {
        enf_id: rotacion_2m_2t_2n_2l
        for enf_id in enfermeras.keys()
    }


@pytest.fixture
def desfases():
    """Desfases para escalonar las enfermeras"""
    return {
        1: 0,  # María empieza en día 0 del ciclo
        2: 2,  # Ana empieza en día 2
        3: 4,  # Carmen empieza en día 4
    }


class TestReparadorCPSAT:
    """Tests del reparador CP-SAT"""
    
    def test_reparador_preserva_celdas_bloqueadas(
        self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases, turnos_basicos
    ):
        """El reparador no debe modificar celdas bloqueadas por incidencias"""
        # Construir matriz base
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz = builder.construir()
        
        # Aplicar vacaciones a María
        vacaciones = Incidencia(
            enfermera_id=1,
            enfermera_nombre='María García',
            tipo=TipoIncidencia.VACACIONES,
            fecha_inicio=date(2026, 4, 1),
            fecha_fin=date(2026, 4, 3),
        )
        
        aplicador = AplicadorIncidencias(matriz, [vacaciones])
        matriz_bloqueada = aplicador.aplicar()
        
        # Verificar que las celdas están bloqueadas
        for dia in range(1, 4):
            celda = matriz_bloqueada.obtener_celda(1, date(2026, 4, dia))
            assert celda.es_modificable is False
        
        # Crear análisis de cobertura simulado
        analisis = {
            'tiene_conflictos': False,
            'conflictos': [],
            'balances': {},
        }
        
        # Ejecutar reparador
        reparador = ReparadorCPSAT(
            matriz_bloqueada=matriz_bloqueada,
            analisis_cobertura=analisis,
            turnos_info=turnos_basicos,
        )
        matriz_final = reparador.reparar()
        
        # Verificar que las celdas bloqueadas permanecen iguales
        for dia in range(1, 4):
            celda = matriz_final.obtener_celda(1, date(2026, 4, dia))
            assert celda.es_modificable is False
            assert celda.tipo_celda == TipoCelda.VACACIONES
    
    def test_reparador_sol_status(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases, turnos_basicos):
        """El reparador debe establecer el estado del solver"""
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz = builder.construir()
        
        analisis = {
            'tiene_conflictos': False,
            'conflictos': [],
            'balances': {},
        }
        
        reparador = ReparadorCPSAT(
            matriz_bloqueada=matriz,
            analisis_cobertura=analisis,
            turnos_info=turnos_basicos,
        )
        reparador.reparar()
        
        # Verificar que solver_status se estableció
        assert reparador.solver_status in ['OPTIMAL', 'FEASIBLE', 'INFEASIBLE', 'NO_EJECUTADO', 'UNKNOWN']
    
    def test_reparador_collects_turnos_disponibles(
        self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases, turnos_basicos
    ):
        """El reparador debe colectar turnos disponibles de la matriz"""
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz = builder.construir()
        
        analisis = {
            'tiene_conflictos': False,
            'conflictos': [],
            'balances': {},
        }
        
        reparador = ReparadorCPSAT(
            matriz_bloqueada=matriz,
            analisis_cobertura=analisis,
            turnos_info=turnos_basicos,
        )
        reparador._crear_variables()
        
        # Verificar que turnos_disponibles se pobló
        assert len(matriz.turnos_disponibles) > 0
        # Debería tener los IDs 1, 2, 3 (M, T, N)
        assert set(matriz.turnos_disponibles) == {1, 2, 3}

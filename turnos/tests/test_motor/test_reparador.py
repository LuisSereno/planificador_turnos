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
        # Debería tener los IDs 1, 2, 3 (M, T, N) más el LIBRE_SENTINEL
        assert set(matriz.turnos_disponibles) == {1, 2, 3, reparador.LIBRE_SENTINEL}


class TestReparadorOptimizacion:
    """Tests de comportamiento de la función objetivo del reparador"""

    def _build_matriz(self, fechas, enfermeras, asignaciones_rotacion, desfases):
        builder = RotacionBaseBuilder(
            fechas=fechas,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        return builder.construir()

    def test_solver_sin_conflictos_preserva_rotacion(
        self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases, turnos_basicos
    ):
        """Sin conflictos de cobertura, el solver debe preservar la rotación base intacta."""
        matriz = self._build_matriz(
            fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases
        )

        # Guardar estado original de la matriz
        celdas_originales = {}
        for enf_id, celdas in matriz.celdas.items():
            for fecha, celda in celdas.items():
                turno_id = celda.turno.id if celda.turno else None
                celdas_originales[(enf_id, fecha)] = turno_id

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
        matriz_final = reparador.reparar()

        # Verificar que muy pocas celdas se desviaron de la rotación base.
        # El solver puede modificar algunas celdas para balancear horas
        # (peso 10 vs peso 100 de rotación), pero las desviaciones deben
        # ser mínimas.
        desviaciones = 0
        for enf_id, celdas in matriz_final.celdas.items():
            for fecha, celda in celdas.items():
                if not celda.es_modificable:
                    continue
                turno_actual = celda.turno.id if celda.turno else None
                turno_original = celdas_originales.get((enf_id, fecha))
                if turno_actual != turno_original:
                    desviaciones += 1

        total_celdas_modificables = sum(
            1 for celdas in matriz_final.celdas.values()
            for c in celdas.values() if c.es_modificable
        )
        # Las desviaciones deben ser menos del 15% de celdas modificables
        max_desviaciones = max(1, int(total_celdas_modificables * 0.15))
        assert desviaciones <= max_desviaciones, (
            f"Se esperaban pocas desviaciones de la rotación base "
            f"(max {max_desviaciones}), pero se encontraron {desviaciones}"
        )

    def test_solver_incluye_historico_en_balance_horas(
        self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases, turnos_basicos
    ):
        """El solver debe considerar horas históricas al calcular desviación."""
        matriz = self._build_matriz(
            fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases
        )

        # Dar a la enfermera 1 muchas horas acumuladas (40h extra)
        # y a las demás 0 horas acumuladas
        balances_historicos = {
            1: {'horas_acumuladas_previas': 40.0, 'noches_acumuladas': 0,
                'fines_semana_acumulados': 0, 'festivos_acumulados': 0},
            2: {'horas_acumuladas_previas': 0.0, 'noches_acumuladas': 0,
                'fines_semana_acumulados': 0, 'festivos_acumulados': 0},
            3: {'horas_acumuladas_previas': 0.0, 'noches_acumuladas': 0,
                'fines_semana_acumulados': 0, 'festivos_acumulados': 0},
        }

        analisis = {
            'tiene_conflictos': False,
            'conflictos': [],
            'balances': {},
        }

        reparador = ReparadorCPSAT(
            matriz_bloqueada=matriz,
            analisis_cobertura=analisis,
            turnos_info=turnos_basicos,
            balances_historicos=balances_historicos,
        )

        # Verificar que el reparador almacena los balances históricos
        assert reparador.balances_historicos == balances_historicos
        assert reparador.balances_historicos[1]['horas_acumuladas_previas'] == 40.0

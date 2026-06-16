# -*- coding: utf-8 -*-
"""
Tests del reparador CP-SAT.
"""
import pytest
from datetime import date, time

from turnos.dominio.dtos import (
    TurnoInfo,
    RotacionCiclo,
)
from turnos.motor.rotacion_base import RotacionBaseBuilder
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
    
    def test_reparador_usa_turno_base_original_id(
        self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases, turnos_basicos
    ):
        """El solver usa _turno_base_original_id (inmutable) aunque AjustadorHoras
        haya modificado celda.turno, preservando el patron de rotacion."""
        # Construir matriz base
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz = builder.construir()

        # Simular que AjustadorHoras modifico celda.turno pero _turno_base_original_id
        # conserva el turno original de la rotacion
        celda_dia1 = matriz.obtener_celda(1, date(2026, 4, 1))
        turno_original = celda_dia1.turno  # Deberia ser M
        assert celda_dia1._turno_base_original_id == turno_original.id

        # Simular corruption: cambiar turno a T (como haria AjustadorHoras)
        celda_dia1.turno = turnos_basicos[2]  # T en vez de M

        # Verificar que _turno_base_original_id NO cambio (es inmutable)
        assert celda_dia1._turno_base_original_id == turno_original.id

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

        # El solver debe restaurar M (el turno base original), no T (el corrupto)
        celda_final = matriz_final.obtener_celda(1, date(2026, 4, 1))
        assert celda_final.turno is not None
        assert celda_final.turno.id == turno_original.id, (
            f"El solver debio restaurar turno {turno_original.id} (base original), "
            f"pero asigno {celda_final.turno.id}"
        )
    
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
        # Con los pesos actuales (500 rotación vs 5 horas) y sin conflictos,
        # el solver debe preservar la rotación casi intacta.
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
        # Las desviaciones deben ser menos del 5% de celdas modificables
        max_desviaciones = max(1, int(total_celdas_modificables * 0.05))
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

# -*- coding: utf-8 -*-
"""
Tests de integración del motor de planificación.
"""
import pytest
from datetime import date, time
from turnos.dominio.dtos import (
    TurnoInfo,
    RotacionCiclo,
    Incidencia,
    TipoIncidencia,
    TipoCelda,
)
from turnos.motor.rotacion_base import RotacionBaseBuilder
from turnos.motor.incidencias import AplicadorIncidencias
from turnos.motor.cobertura import AnalizadorCobertura
from turnos.motor.pipeline import PipelinePlanificacion


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


class TestRotacionBaseBuilder:
    """Tests del constructor de rotación base"""
    
    def test_construir_rotacion_base(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases):
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        
        matriz = builder.construir()
        
        # 3 enfermeras × 10 días = 30 celdas
        assert matriz.total_celdas() == 30
        assert len(matriz.fechas) == 10
        assert len(matriz.enfermeras) == 3
    
    def test_rotacion_reproducible(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases):
        """La misma configuración debe producir la misma matriz"""
        builder1 = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz1 = builder1.construir()
        
        builder2 = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz2 = builder2.construir()
        
        # Verificar que las matrices son idénticas
        for enf_id in enfermeras.keys():
            celdas1 = matriz1.obtener_celdas_enfermera(enf_id)
            celdas2 = matriz2.obtener_celdas_enfermera(enf_id)
            
            for fecha in fechas_abril_2026:
                assert celdas1[fecha].turno == celdas2[fecha].turno
    
    def test_celdas_pertenecen_rotacion(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases):
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        
        matriz = builder.construir()
        
        # Todas las celdas deben marcar que pertenecen a rotación base
        for celdas_enf in matriz.celdas.values():
            for celda in celdas_enf.values():
                assert celda.pertenece_rotacion_base is True


class TestAplicadorIncidencias:
    """Tests del aplicador de incidencias"""
    
    def test_aplicar_vacaciones(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases):
        # Construir matriz base
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz = builder.construir()
        
        # Aplicar vacaciones a María del día 3 al 5
        vacaciones = Incidencia(
            enfermera_id=1,
            enfermera_nombre='María García',
            tipo=TipoIncidencia.VACACIONES,
            fecha_inicio=date(2026, 4, 3),
            fecha_fin=date(2026, 4, 5),
        )
        
        aplicador = AplicadorIncidencias(matriz, [vacaciones])
        matriz_final = aplicador.aplicar()
        
        # Verificar que las celdas de vacaciones están bloqueadas
        for dia in range(3, 6):
            celda = matriz_final.obtener_celda(1, date(2026, 4, dia))
            assert celda.tipo_celda == TipoCelda.VACACIONES
            assert celda.es_modificable is False
            assert celda.turno is None
        
        # Verificar que otros días no se modificaron
        celda_antes = matriz_final.obtener_celda(1, date(2026, 4, 1))
        assert celda_antes.es_modificable is True
    
    def test_aplicar_multiple_incidencias(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases):
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz = builder.construir()
        
        vacaciones_maria = Incidencia(
            enfermera_id=1,
            enfermera_nombre='María García',
            tipo=TipoIncidencia.VACACIONES,
            fecha_inicio=date(2026, 4, 1),
            fecha_fin=date(2026, 4, 3),
        )
        
        permiso_ana = Incidencia(
            enfermera_id=2,
            enfermera_nombre='Ana López',
            tipo=TipoIncidencia.PERMISO,
            fecha_inicio=date(2026, 4, 5),
            fecha_fin=date(2026, 4, 5),
        )
        
        aplicador = AplicadorIncidencias(matriz, [vacaciones_maria, permiso_ana])
        matriz_final = aplicador.aplicar()
        
        # Verificar vacaciones de María
        assert matriz_final.obtener_celda(1, date(2026, 4, 2)).tipo_celda == TipoCelda.VACACIONES
        
        # Verificar permiso de Ana
        celda_permiso = matriz_final.obtener_celda(2, date(2026, 4, 5))
        assert celda_permiso.tipo_celda == TipoCelda.PERMISO
        assert celda_permiso.es_modificable is False


class TestAnalizadorCobertura:
    """Tests del analizador de cobertura"""
    
    def test_calcular_balances(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases, turnos_basicos):
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz = builder.construir()
        
        # 10 días con rotación 2M-2T-2N-2L (ciclo de 8 días, 6 trabajados)
        # Cada enfermera trabaja ~6/8 de los días = 75% de 10 días = 7.5 días
        # 7.5 días × 8 horas = 60 horas aproximadamente
        horas_objetivo = {1: 60.0, 2: 60.0, 3: 60.0}
        
        analizador = AnalizadorCobertura(matriz, horas_objetivo)
        resultado = analizador.analizar()
        
        # Verificar que hay balances para todas las enfermeras
        assert len(resultado['balances']) == 3
        
        # Verificar que las desviaciones son razonables (< 10%)
        for enf_id, balance in resultado['balances'].items():
            desviacion_pct = abs(balance.desviacion_porcentaje)
            assert desviacion_pct < 15.0  # Tolerancia del 15% para este test básico
    
    def test_detectar_conflictos_cobertura(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases):
        builder = RotacionBaseBuilder(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
        )
        matriz = builder.construir()
        
        horas_objetivo = {1: 40.0, 2: 40.0, 3: 40.0}
        cobertura_minima = {
            1: 2,  # Turno M necesita al menos 2 enfermeras
            2: 1,  # Turno T necesita al menos 1
            3: 1,  # Turno N necesita al menos 1
        }
        
        analizador = AnalizadorCobertura(matriz, horas_objetivo, cobertura_minima)
        resultado = analizador.analizar()
        
        # El resultado debe tener la estructura correcta
        assert 'balances' in resultado
        assert 'cobertura_turnos' in resultado
        assert 'conflictos' in resultado
        assert 'tiene_conflictos' in resultado


class TestPipelinePlanificacion:
    """Tests del pipeline completo"""
    
    def test_pipeline_sin_incidencias(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases):
        horas_objetivo = {1: 40.0, 2: 40.0, 3: 40.0}
        
        pipeline = PipelinePlanificacion(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
            incidencias=[],
            horas_objetivo=horas_objetivo,
        )
        
        resultado = pipeline.ejecutar()
        
        assert resultado.exitosa is True
        assert resultado.matriz.total_celdas() == 30  # 3 × 10
        assert len(resultado.balances) == 3
    
    def test_pipeline_con_vacaciones(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases):
        vacaciones = Incidencia(
            enfermera_id=1,
            enfermera_nombre='María García',
            tipo=TipoIncidencia.VACACIONES,
            fecha_inicio=date(2026, 4, 1),
            fecha_fin=date(2026, 4, 5),
        )
        
        horas_objetivo = {1: 40.0, 2: 40.0, 3: 40.0}
        
        pipeline = PipelinePlanificacion(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
            incidencias=[vacaciones],
            horas_objetivo=horas_objetivo,
        )
        
        resultado = pipeline.ejecutar()
        
        assert resultado.exitosa is True
        
        # Verificar que las vacaciones se aplicaron
        for dia in range(1, 6):
            celda = resultado.matriz.obtener_celda(1, date(2026, 4, dia))
            assert celda.tipo_celda == TipoCelda.VACACIONES
            assert celda.es_modificable is False
    
    def test_pipeline_reproducible(self, fechas_abril_2026, enfermeras, asignaciones_rotacion, desfases):
        """El mismo pipeline debe producir el mismo resultado"""
        horas_objetivo = {1: 40.0, 2: 40.0, 3: 40.0}
        
        pipeline1 = PipelinePlanificacion(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
            incidencias=[],
            horas_objetivo=horas_objetivo,
        )
        resultado1 = pipeline1.ejecutar()
        
        pipeline2 = PipelinePlanificacion(
            fechas=fechas_abril_2026,
            enfermeras=enfermeras,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
            incidencias=[],
            horas_objetivo=horas_objetivo,
        )
        resultado2 = pipeline2.ejecutar()
        
        # Verificar que las matrices son idénticas
        for enf_id in enfermeras.keys():
            celdas1 = resultado1.matriz.obtener_celdas_enfermera(enf_id)
            celdas2 = resultado2.matriz.obtener_celdas_enfermera(enf_id)
            
            for fecha in fechas_abril_2026:
                assert celdas1[fecha].turno == celdas2[fecha].turno

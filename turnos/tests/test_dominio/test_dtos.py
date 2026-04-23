# -*- coding: utf-8 -*-
"""
Tests de los DTOs del dominio.
"""
import pytest
from datetime import date, time
from turnos.dominio.dtos import (
    CeldaPlanificacion,
    TipoCelda,
    TurnoInfo,
    BalanceEnfermera,
    Incidencia,
    TipoIncidencia,
    RotacionCiclo,
    MatrizPlanificacion,
)


class TestTurnoInfo:
    def test_creacion_turno(self):
        turno = TurnoInfo(
            id=1,
            nombre='MAÑANA',
            hora_inicio=time(7, 0),
            hora_fin=time(15, 0),
            duracion_horas=8.0,
        )
        assert turno.nombre == 'MAÑANA'
        assert turno.duracion_horas == 8.0
        assert not turno.es_nocturno
    
    def test_turno_nocturno(self):
        turno = TurnoInfo(
            id=2,
            nombre='NOCHE',
            hora_inicio=time(23, 0),
            hora_fin=time(7, 0),
            duracion_horas=8.0,
            es_nocturno=True,
        )
        assert turno.es_nocturno


class TestCeldaPlanificacion:
    def test_celda_con_turno(self):
        turno = TurnoInfo(id=1, nombre='M', hora_inicio=time(7, 0), hora_fin=time(15, 0), duracion_horas=8.0)
        celda = CeldaPlanificacion(
            enfermera_id=1,
            enfermera_nombre='María García',
            fecha=date(2026, 4, 1),
            turno=turno,
            tipo_celda=TipoCelda.TURNO,
        )
        
        assert celda.es_libre is False
        assert celda.horas_asignadas == 8.0
        assert celda.es_noche is False
    
    def test_celda_libre(self):
        celda = CeldaPlanificacion(
            enfermera_id=1,
            enfermera_nombre='María García',
            fecha=date(2026, 4, 1),
            tipo_celda=TipoCelda.LIBRE,
        )
        
        assert celda.es_libre is True
        assert celda.horas_asignadas == 0.0
    
    def test_celda_fin_de_semana(self):
        # 2026-04-04 es sábado
        celda = CeldaPlanificacion(
            enfermera_id=1,
            enfermera_nombre='María García',
            fecha=date(2026, 4, 4),
            tipo_celda=TipoCelda.TURNO,
        )
        
        assert celda.es_fin_de_semana is True
    
    def test_celda_dia_laboral(self):
        # 2026-04-01 es miércoles
        celda = CeldaPlanificacion(
            enfermera_id=1,
            enfermera_nombre='María García',
            fecha=date(2026, 4, 1),
            tipo_celda=TipoCelda.TURNO,
        )
        
        assert celda.es_fin_de_semana is False


class TestBalanceEnfermera:
    def test_balance_basico(self):
        balance = BalanceEnfermera(
            enfermera_id=1,
            enfermera_nombre='María García',
            horas_asignadas=160.0,
            horas_objetivo=160.0,
            desviacion_horas=0.0,
        )
        
        assert balance.desviacion_porcentaje == 0.0
    
    def test_balance_con_desviacion(self):
        balance = BalanceEnfermera(
            enfermera_id=1,
            enfermera_nombre='María García',
            horas_asignadas=170.0,
            horas_objetivo=160.0,
            desviacion_horas=10.0,
        )
        
        assert balance.desviacion_porcentaje == pytest.approx(6.25, rel=0.01)
    
    def test_balance_con_historico(self):
        balance = BalanceEnfermera(
            enfermera_id=1,
            enfermera_nombre='María García',
            horas_asignadas=160.0,
            horas_objetivo=1800.0,
            horas_acumuladas_previas=1700.0,
        )
        
        assert balance.horas_totales_con_historico == 1860.0


class TestIncidencia:
    def test_incidencia_afecta_fecha(self):
        incidencia = Incidencia(
            enfermera_id=1,
            enfermera_nombre='María García',
            tipo=TipoIncidencia.VACACIONES,
            fecha_inicio=date(2026, 4, 1),
            fecha_fin=date(2026, 4, 7),
        )
        
        assert incidencia.afecta_fecha(date(2026, 4, 3)) is True
        assert incidencia.afecta_fecha(date(2026, 4, 1)) is True
        assert incidencia.afecta_fecha(date(2026, 4, 7)) is True
        assert incidencia.afecta_fecha(date(2026, 3, 31)) is False
        assert incidencia.afecta_fecha(date(2026, 4, 8)) is False


class TestRotacionCiclo:
    def test_ciclo_simple(self):
        turno_m = TurnoInfo(id=1, nombre='M', hora_inicio=time(7, 0), hora_fin=time(15, 0), duracion_horas=8.0)
        turno_t = TurnoInfo(id=2, nombre='T', hora_inicio=time(15, 0), hora_fin=time(23, 0), duracion_horas=8.0)
        
        ciclo = RotacionCiclo(
            nombre='2M-2T',
            ciclo_dias=4,
            celdas=[turno_m, turno_m, turno_t, turno_t],
        )
        
        assert ciclo.obtener_turno(0) == turno_m
        assert ciclo.obtener_turno(1) == turno_m
        assert ciclo.obtener_turno(2) == turno_t
        assert ciclo.obtener_turno(3) == turno_t
    
    def test_ciclo_con_repeticion(self):
        turno_m = TurnoInfo(id=1, nombre='M', hora_inicio=time(7, 0), hora_fin=time(15, 0), duracion_horas=8.0)
        
        ciclo = RotacionCiclo(
            nombre='1M',
            ciclo_dias=1,
            celdas=[turno_m],
        )
        
        assert ciclo.obtener_turno(0) == turno_m
        assert ciclo.obtener_turno(1) == turno_m
        assert ciclo.obtener_turno(10) == turno_m
    
    def test_ciclo_con_dia_libre(self):
        turno_m = TurnoInfo(id=1, nombre='M', hora_inicio=time(7, 0), hora_fin=time(15, 0), duracion_horas=8.0)
        
        ciclo = RotacionCiclo(
            nombre='2M-2L',
            ciclo_dias=4,
            celdas=[turno_m, turno_m, None, None],
        )
        
        assert ciclo.obtener_turno(0) == turno_m
        assert ciclo.obtener_turno(2) is None


class TestMatrizPlanificacion:
    def test_matriz_vacia(self):
        matriz = MatrizPlanificacion()
        assert matriz.total_celdas() == 0
        assert matriz.obtener_celda(1, date(2026, 4, 1)) is None
    
    def test_asignar_y_obtener_celda(self):
        celda = CeldaPlanificacion(
            enfermera_id=1,
            enfermera_nombre='María García',
            fecha=date(2026, 4, 1),
            tipo_celda=TipoCelda.TURNO,
        )
        
        matriz = MatrizPlanificacion()
        matriz.asignar_celda(celda)
        
        resultado = matriz.obtener_celda(1, date(2026, 4, 1))
        assert resultado is not None
        assert resultado.enfermera_id == 1
        assert resultado.fecha == date(2026, 4, 1)
    
    def test_obtener_celdas_enfermera(self):
        matriz = MatrizPlanificacion()
        
        for dia in range(1, 4):
            celda = CeldaPlanificacion(
                enfermera_id=1,
                enfermera_nombre='María García',
                fecha=date(2026, 4, dia),
                tipo_celda=TipoCelda.TURNO,
            )
            matriz.asignar_celda(celda)
        
        celdas_enfermera = matriz.obtener_celdas_enfermera(1)
        assert len(celdas_enfermera) == 3
    
    def test_total_celdas(self):
        matriz = MatrizPlanificacion()
        
        for enf_id in range(1, 3):
            for dia in range(1, 4):
                celda = CeldaPlanificacion(
                    enfermera_id=enf_id,
                    enfermera_nombre=f'Enfermera {enf_id}',
                    fecha=date(2026, 4, dia),
                    tipo_celda=TipoCelda.TURNO,
                )
                matriz.asignar_celda(celda)
        
        assert matriz.total_celdas() == 6  # 2 enfermeras × 3 días

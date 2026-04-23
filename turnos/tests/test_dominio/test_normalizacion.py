# -*- coding: utf-8 -*-
"""
Tests de la capa de normalización de nombres.
"""
import pytest
from turnos.dominio.normalizacion import (
    normalizar_nombre,
    normalizar_restriccion,
    normalizar_patron,
    normalizar_lista_restricciones,
    normalizar_lista_patrones,
    normalizar_lista_nombres,
    RESTRICCIONES_DURAS_MAP,
    RESTRICCIONES_BLANDAS_MAP,
    PATRONES_MAP,
)


class TestNormalizarNombre:
    """Tests de la función principal de normalización"""
    
    def test_normalizar_restriccion_dura_con_guiones(self):
        assert normalizar_nombre('turnos_consecutivos_max') == 'TURNO_CONSECUTIVOS_MAX'
    
    def test_normalizar_restriccion_dura_sin_guiones(self):
        assert normalizar_nombre('turnosconsecutivosmax') == 'TURNO_CONSECUTIVOS_MAX'
    
    def test_normalizar_equidad_turnos(self):
        assert normalizar_nombre('equidad_turnos') == 'EQUIDAD_TURNOS'
        assert normalizar_nombre('equidadturnos') == 'EQUIDAD_TURNOS'
    
    def test_normalizar_minimizar_noches(self):
        assert normalizar_nombre('minimizar_noches') == 'MINIMIZAR_NOCHES'
        assert normalizar_nombre('minimizarnoches') == 'MINIMIZAR_NOCHES'
    
    def test_normalizar_patron_secuencia(self):
        assert normalizar_nombre('SECUENCIA_TURNOS') == 'SECUENCIA_OBLIGATORIA'
        # Case-sensitive - solo detecta exacto
    
    def test_normalizar_patron_rotacion(self):
        assert normalizar_nombre('ROTACION_TURNOS') == 'ROTACION_CICLICA'
        assert normalizar_nombre('ROTACION') == 'ROTACION_CICLICA'
    
    def test_nombre_ya_canonico(self):
        """Un nombre ya canónico debe permanecer igual"""
        assert normalizar_nombre('TURNO_CONSECUTIVOS_MAX') == 'TURNO_CONSECUTIVOS_MAX'
        assert normalizar_nombre('EQUIDAD_TURNOS') == 'EQUIDAD_TURNOS'
    
    def test_nombre_desconocido(self):
        """Un nombre desconocido debe retornarse uppercase"""
        assert normalizar_nombre('nombre_desconocido') == 'NOMBRE_DESCONOCIDO'


class TestNormalizarRestriccion:
    """Tests específicos para restricciones"""
    
    def test_restriccion_dura_valida(self):
        # La función acepta dicts con campo 'nombre'
        restriccion = {'nombre': 'turnos_consecutivos_max', 'valor': 6}
        resultado = normalizar_restriccion(restriccion)
        assert resultado['nombre'] == 'TURNO_CONSECUTIVOS_MAX'
    
    def test_restriccion_blanda_valida(self):
        restriccion = {'nombre': 'equidad_turnos', 'peso': 10}
        resultado = normalizar_restriccion(restriccion)
        assert resultado['nombre'] == 'EQUIDAD_TURNOS'
    
    def test_restriccion_no_existe(self):
        # No levanta error, solo loguea warning
        restriccion = {'nombre': 'restriccion_inexistente'}
        resultado = normalizar_restriccion(restriccion)
        # Mantenga underscores al convertir a uppercase
        assert resultado['nombre'] == 'RESTRICCION_INEXISTENTE'


class TestNormalizarPatron:
    """Tests específicos para patrones"""
    
    def test_patron_valido(self):
        # SECUENCIA_TURNOS está en el mapa de patrones
        patron = {'tipo': 'SECUENCIA_TURNOS'}
        resultado = normalizar_patron(patron)
        # Debería normalizar el campo 'tipo'
        assert resultado['tipo'] == 'SECUENCIA_OBLIGATORIA'
    
    def test_patron_no_existe(self):
        # No levanta error, solo loguea warning y convierte a uppercase
        patron = {'tipo': 'patron_inexistente'}
        resultado = normalizar_patron(patron)
        assert resultado['tipo'] == 'PATRON_INEXISTENTE'


class TestNormalizarLista:
    """Tests de normalización de listas de nombres"""
    
    def test_lista_mixta(self):
        nombres = ['turnos_consecutivos_max', 'EQUIDAD_TURNOS', 'ROTACION']
        resultado = normalizar_lista_nombres(nombres)
        
        assert resultado == [
            'TURNO_CONSECUTIVOS_MAX',
            'EQUIDAD_TURNOS',
            'ROTACION_CICLICA',
        ]
    
    def test_lista_vacia(self):
        assert normalizar_lista_nombres([]) == []
    
    def test_lista_con_duplicados(self):
        nombres = ['turnos_consecutivos_max', 'turnosconsecutivosmax']
        resultado = normalizar_lista_nombres(nombres, eliminar_duplicados=True)
        
        assert len(resultado) == 1
        assert resultado[0] == 'TURNO_CONSECUTIVOS_MAX'

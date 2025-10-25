import pytest
from turnos.generador import GeneradorTurnos


@pytest.mark.django_db
class TestGeneradorTurnos:
    def test_inicializacion(self, configuracion_basica):
        generador = GeneradorTurnos(configuracion_basica)
        assert generador.num_dias == 7
        assert generador.num_enfermeras == 5
        assert generador.num_turnos == 3
    
    def test_crear_variables(self, configuracion_basica):
        generador = GeneradorTurnos(configuracion_basica)
        generador.crear_variables()
        expected_vars = 5 * 7 * 3
        assert len(generador.shifts) == expected_vars
    
    def test_resolver_basico(self, configuracion_basica):
        generador = GeneradorTurnos(configuracion_basica)
        resultado = generador.resolver()
        assert 'success' in resultado
        assert 'asignaciones' in resultado

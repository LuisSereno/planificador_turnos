import pytest
from datetime import time
from turnos.models import Enfermera, TipoTurno


@pytest.mark.django_db
class TestEnfermera:
    def test_crear_enfermera(self):
        enfermera = Enfermera.objects.create(
            nombre='MarÃ­a GarcÃ­a',
            email='maria@hospital.com',
            dni='12345678A',
            activa=True
        )
        assert enfermera.nombre == 'MarÃ­a GarcÃ­a'
        assert str(enfermera) == 'MarÃ­a GarcÃ­a'


@pytest.mark.django_db
class TestTipoTurno:
    def test_duracion_turno_normal(self):
        turno = TipoTurno.objects.create(
            nombre='MANANA',
            hora_inicio=time(7, 0),
            hora_fin=time(15, 0)
        )
        assert turno.duracion_horas == 8.0
    
    def test_duracion_turno_nocturno(self):
        turno = TipoTurno.objects.create(
            nombre='NOCHE',
            hora_inicio=time(23, 0),
            hora_fin=time(7, 0)
        )
        assert turno.duracion_horas == 8.0

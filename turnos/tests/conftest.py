import pytest
from django.contrib.auth import get_user_model
from datetime import date, time
from turnos.models import Enfermera, TipoTurno, ConfiguracionPlanificacion

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123'
    )


@pytest.fixture
def enfermeras(db):
    enfermeras = []
    for i in range(1, 6):
        enfermera = Enfermera.objects.create(
            nombre=f'Enfermera {i}',
            email=f'enfermera{i}@hospital.com',
            dni=f'1234567{i}A',
            activa=True
        )
        enfermeras.append(enfermera)
    return enfermeras


@pytest.fixture
def turnos(db):
    manana = TipoTurno.objects.create(
        nombre='MANANA',
        hora_inicio=time(7, 0),
        hora_fin=time(15, 0),
        activo=True
    )
    tarde = TipoTurno.objects.create(
        nombre='TARDE',
        hora_inicio=time(15, 0),
        hora_fin=time(23, 0),
        activo=True
    )
    noche = TipoTurno.objects.create(
        nombre='NOCHE',
        hora_inicio=time(23, 0),
        hora_fin=time(7, 0),
        activo=True
    )
    return [manana, tarde, noche]


@pytest.fixture
def configuracion_basica(db, user, enfermeras, turnos):
    # Usar mes completo (abril 2026 = 30 días) para cumplir validación mensual
    config = ConfiguracionPlanificacion.objects.create(
        nombre='Config Test',
        num_dias=30,
        fecha_inicio=date(2026, 4, 1),
        creado_por=user
    )
    config.enfermeras.set(enfermeras)
    config.turnos.set(turnos)
    return config

from django.core.management.base import BaseCommand
from turnos.models import Enfermera, TipoTurno, ConfiguracionPlanificacion
from faker import Faker
import random


class Command(BaseCommand):
    help = 'Genera datos de prueba aleatorios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enfermeras',
            type=int,
            default=0,
            help='Número de enfermeras a crear',
        )
        parser.add_argument(
            '--configuraciones',
            type=int,
            default=0,
            help='Número de configuraciones a crear',
        )

    def handle(self, *args, **options):
        fake = Faker('es_ES')

        if options['enfermeras'] > 0:
            self.generar_enfermeras(fake, options['enfermeras'])

        if options['configuraciones'] > 0:
            self.generar_configuraciones(fake, options['configuraciones'])

    def generar_enfermeras(self, fake, cantidad):
        self.stdout.write(f'Generando {cantidad} enfermeras...')

        creadas = 0
        for i in range(cantidad):
            try:
                nombre = fake.name()
                email = fake.email()

                Enfermera.objects.create(
                    nombre=nombre,
                    email=email,
                    telefono=fake.phone_number(),
                    dni=fake.bothify(text='########?').upper(),
                    fecha_alta=fake.date_between(start_date='-2y', end_date='today'),
                    activa=random.choice([True, True, True, False]),  # 75% activas
                    notas=fake.text(max_nb_chars=200) if random.random() > 0.5 else ''
                )
                creadas += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠ Error creando enfermera: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'✓ {creadas} enfermeras creadas'))

    def generar_configuraciones(self, fake, cantidad):
        self.stdout.write(f'Generando {cantidad} configuraciones...')

        # Asegurarse de que existan tipos de turno
        if TipoTurno.objects.count() == 0:
            self.stdout.write(
                self.style.ERROR('✗ No existen tipos de turno. Ejecuta: python manage.py crear_tipos_turno'))
            return

        # Asegurarse de que existan enfermeras
        if Enfermera.objects.count() < 5:
            self.stdout.write(self.style.WARNING('⚠ Se recomienda tener al menos 5 enfermeras'))

        creadas = 0
        for i in range(cantidad):
            try:
                config = ConfiguracionPlanificacion.objects.create(
                    nombre=f'Configuración de Prueba {fake.month_name()} {fake.year()}',
                    descripcion=fake.text(max_nb_chars=300),
                    num_dias=random.choice([7, 14, 30]),
                    fecha_inicio=fake.date_between(start_date='today', end_date='+3m'),
                    activa=True,
                    tiempo_maximo_segundos=random.choice([30, 60, 90, 120]),
                    num_trabajadores=random.choice([2, 4, 6]),
                    demanda_por_turno={
                        'MAÑANA': {'min': 2, 'max': 5, 'optimo': 3},
                        'TARDE': {'min': 2, 'max': 4, 'optimo': 3},
                        'NOCHE': {'min': 1, 'max': 3, 'optimo': 2}
                    }
                )

                # Asignar enfermeras aleatorias
                enfermeras = Enfermera.objects.filter(activa=True).order_by('?')[:random.randint(5, 10)]
                config.enfermeras.set(enfermeras)

                # Asignar tipos de turno
                config.turnos.set(TipoTurno.objects.filter(activo=True))

                creadas += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠ Error creando configuración: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'✓ {creadas} configuraciones creadas'))

from django.core.management.base import BaseCommand
from turnos.models import TipoTurno
from datetime import time


class Command(BaseCommand):
    help = 'Crea los tipos de turno estándar (Mañana, Tarde, Noche)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recrear',
            action='store_true',
            help='Elimina tipos existentes y los recrea',
        )

    def handle(self, *args, **options):
        tipos_turno = [
            {
                'nombre': 'MAÑANA',
                'hora_inicio': time(7, 0),
                'hora_fin': time(15, 0),
                'color': '#ffc107',
            },
            {
                'nombre': 'TARDE',
                'hora_inicio': time(15, 0),
                'hora_fin': time(23, 0),
                'color': '#17a2b8',
            },
            {
                'nombre': 'NOCHE',
                'hora_inicio': time(23, 0),
                'hora_fin': time(7, 0),
                'color': '#6f42c1',
            },
        ]

        if options['recrear']:
            confirmacion = input('¿Estás seguro de que quieres eliminar todos los tipos de turno existentes? (s/n): ')
            if confirmacion.lower() == 's':
                count = TipoTurno.objects.all().count()
                TipoTurno.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'✓ {count} tipos de turno eliminados'))
            else:
                self.stdout.write(self.style.WARNING('Operación cancelada'))
                return

        creados = 0
        existentes = 0

        for turno_data in tipos_turno:
            turno, created = TipoTurno.objects.get_or_create(
                nombre=turno_data['nombre'],
                defaults={
                    'hora_inicio': turno_data['hora_inicio'],
                    'hora_fin': turno_data['hora_fin'],
                    'color': turno_data['color'],
                    'activo': True,
                }
            )

            if created:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Tipo de turno "{turno.get_nombre_display()}" creado: '
                        f'{turno.hora_inicio.strftime("%H:%M")} - {turno.hora_fin.strftime("%H:%M")}'
                    )
                )
            else:
                existentes += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ Tipo de turno "{turno.get_nombre_display()}" ya existe'
                    )
                )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'✓ Creados: {creados}'))
        self.stdout.write(self.style.WARNING(f'⚠ Ya existían: {existentes}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Total tipos de turno: {TipoTurno.objects.count()}'))

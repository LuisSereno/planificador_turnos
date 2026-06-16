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
                'nombre': 'MANANA',
                'codigo_corto': 'M',
                'hora_inicio': time(7, 0),
                'hora_fin': time(15, 0),
            },
            {
                'nombre': 'TARDE',
                'codigo_corto': 'T',
                'hora_inicio': time(15, 0),
                'hora_fin': time(23, 0),
            },
            {
                'nombre': 'NOCHE',
                'codigo_corto': 'N',
                'hora_inicio': time(23, 0),
                'hora_fin': time(7, 0),
            },
        ]

        if options['recrear']:
            confirmacion = input('Estas seguro de que quieres eliminar todos los tipos de turno existentes? (s/n): ')
            if confirmacion.lower() == 's':
                count = TipoTurno.objects.all().count()
                TipoTurno.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'{count} tipos de turno eliminados'))
            else:
                self.stdout.write(self.style.WARNING('Operacion cancelada'))
                return

        creados = 0
        existentes = 0

        for turno_data in tipos_turno:
            existente = TipoTurno.objects.filter(nombre=turno_data['nombre']).first()
            if existente:
                turno = existente
                created = False
                if not turno.codigo_corto:
                    turno.codigo_corto = turno_data['codigo_corto']
                    turno.save(update_fields=['codigo_corto'])
            else:
                turno = TipoTurno.objects.create(
                    nombre=turno_data['nombre'],
                    codigo_corto=turno_data['codigo_corto'],
                    hora_inicio=turno_data['hora_inicio'],
                    hora_fin=turno_data['hora_fin'],
                    activo=True,
                )
                created = True

            if created:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Tipo de turno "{turno.get_nombre_display()}" [{turno.codigo_corto}] creado: '
                        f'{turno.hora_inicio.strftime("%H:%M")} - {turno.hora_fin.strftime("%H:%M")}'
                    )
                )
            else:
                existentes += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Tipo de turno "{turno.get_nombre_display()}" ya existe'
                    )
                )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Creados: {creados}'))
        self.stdout.write(self.style.WARNING(f'Ya existian: {existentes}'))
        self.stdout.write(self.style.SUCCESS(f'Total tipos de turno: {TipoTurno.objects.count()}'))

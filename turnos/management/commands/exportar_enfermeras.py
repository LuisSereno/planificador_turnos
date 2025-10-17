import csv
from django.core.management.base import BaseCommand
from turnos.models import Enfermera
from datetime import datetime


class Command(BaseCommand):
    help = 'Exporta todas las enfermeras a un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            default=f'enfermeras_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            help='Nombre del archivo CSV de salida (default: enfermeras_YYYYMMDD_HHMMSS.csv)'
        )
        parser.add_argument(
            '--solo-activas',
            action='store_true',
            help='Exporta solo enfermeras activas',
        )

    def handle(self, *args, **options):
        archivo = options['archivo']
        solo_activas = options['solo_activas']

        enfermeras = Enfermera.objects.all()
        if solo_activas:
            enfermeras = enfermeras.filter(activa=True)

        enfermeras = enfermeras.order_by('nombre')

        try:
            with open(archivo, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'nombre', 'email', 'telefono', 'dni', 'fecha_alta', 'activa', 'notas']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()

                count = 0
                for enfermera in enfermeras:
                    writer.writerow({
                        'id': enfermera.id,
                        'nombre': enfermera.nombre,
                        'email': enfermera.email,
                        'telefono': enfermera.telefono or '',
                        'dni': enfermera.dni or '',
                        'fecha_alta': enfermera.fecha_alta.strftime('%Y-%m-%d') if enfermera.fecha_alta else '',
                        'activa': 'true' if enfermera.activa else 'false',
                        'notas': enfermera.notas or '',
                    })
                    count += 1

                self.stdout.write(self.style.SUCCESS(f'✓ {count} enfermeras exportadas a: {archivo}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error al exportar: {str(e)}'))

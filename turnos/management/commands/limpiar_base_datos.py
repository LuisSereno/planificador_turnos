from django.core.management.base import BaseCommand
from django.db import connection
from turnos.models import (
    Enfermera, TipoTurno, ConfiguracionPlanificacion,
    Ejecucion, Planilla,
)


class Command(BaseCommand):
    help = 'Limpia datos de la base de datos según diferentes criterios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ejecuciones-antiguas',
            type=int,
            metavar='DIAS',
            help='Elimina ejecuciones completadas más antiguas que N días',
        )
        parser.add_argument(
            '--ejecuciones-fallidas',
            action='store_true',
            help='Elimina todas las ejecuciones fallidas',
        )
        parser.add_argument(
            '--enfermeras-inactivas',
            action='store_true',
            help='Elimina enfermeras marcadas como inactivas',
        )
        parser.add_argument(
            '--todo',
            action='store_true',
            help='PELIGRO: Elimina TODOS los datos (excepto usuarios)',
        )
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma la eliminación sin preguntar',
        )

    def handle(self, *args, **options):
        if options['todo']:
            if not options['confirmar']:
                confirmacion = input(
                    'PELIGRO! Esto eliminara TODOS los datos (excepto usuarios). '
                    'Escribe "ELIMINAR TODO" para confirmar: '
                )
                if confirmacion != 'ELIMINAR TODO':
                    self.stdout.write(self.style.WARNING('Operacion cancelada'))
                    return

            self.limpiar_todo()
            return

        eliminados = 0

        if options['ejecuciones_antiguas']:
            dias = options['ejecuciones_antiguas']
            eliminados += self.limpiar_ejecuciones_antiguas(dias, options['confirmar'])

        if options['ejecuciones_fallidas']:
            eliminados += self.limpiar_ejecuciones_fallidas(options['confirmar'])

        if options['enfermeras_inactivas']:
            eliminados += self.limpiar_enfermeras_inactivas(options['confirmar'])

        if eliminados == 0 and not options['todo']:
            self.stdout.write(self.style.WARNING('No se especifico ninguna opcion de limpieza'))
            self.stdout.write('Usa --help para ver las opciones disponibles')

    def limpiar_ejecuciones_antiguas(self, dias, confirmar):
        from datetime import timedelta
        from django.utils import timezone

        fecha_limite = timezone.now() - timedelta(days=dias)
        ejecuciones = Ejecucion.objects.filter(
            fecha_inicio__lt=fecha_limite,
            estado='COMPLETADA'
        )

        count = ejecuciones.count()

        if count == 0:
            self.stdout.write(f'No hay ejecuciones completadas con mas de {dias} dias')
            return 0

        if not confirmar:
            confirmacion = input(f'Eliminar {count} ejecuciones completadas con mas de {dias} dias? (s/n): ')
            if confirmacion.lower() != 's':
                self.stdout.write(self.style.WARNING('Operacion cancelada'))
                return 0

        ejecuciones.delete()
        self.stdout.write(self.style.SUCCESS(f'{count} ejecuciones antiguas eliminadas'))
        return count

    def limpiar_ejecuciones_fallidas(self, confirmar):
        ejecuciones = Ejecucion.objects.filter(estado='ERROR')
        count = ejecuciones.count()

        if count == 0:
            self.stdout.write('No hay ejecuciones fallidas')
            return 0

        if not confirmar:
            confirmacion = input(f'Eliminar {count} ejecuciones fallidas? (s/n): ')
            if confirmacion.lower() != 's':
                self.stdout.write(self.style.WARNING('Operacion cancelada'))
                return 0

        ejecuciones.delete()
        self.stdout.write(self.style.SUCCESS(f'{count} ejecuciones fallidas eliminadas'))
        return count

    def limpiar_enfermeras_inactivas(self, confirmar):
        enfermeras = Enfermera.objects.filter(activa=False)
        count = enfermeras.count()

        if count == 0:
            self.stdout.write('No hay enfermeras inactivas')
            return 0

        if not confirmar:
            confirmacion = input(f'Eliminar {count} enfermeras inactivas? (s/n): ')
            if confirmacion.lower() != 's':
                self.stdout.write(self.style.WARNING('Operacion cancelada'))
                return 0

        enfermeras.delete()
        self.stdout.write(self.style.SUCCESS(f'{count} enfermeras inactivas eliminadas'))
        return count

    def limpiar_todo(self):
        self.stdout.write(self.style.ERROR('Limpiando TODA la base de datos...'))

        models = [
            ('Ejecuciones', Ejecucion),
            ('Planillas', Planilla),
            ('Configuraciones', ConfiguracionPlanificacion),
            ('Enfermeras', Enfermera),
            ('Tipos de Turno', TipoTurno),
        ]

        for nombre, modelo in models:
            count = modelo.objects.count()
            modelo.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'{count} {nombre} eliminados'))

        self.stdout.write(self.style.SUCCESS('\nBase de datos limpiada completamente'))

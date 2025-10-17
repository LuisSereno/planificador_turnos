from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Carga todos los fixtures de demostración'

    def handle(self, *args, **options):
        fixtures = [
            'initial_data',
            'demo_enfermeras',
            'usuarios_demo',
            'demo_configuracion',
            'plantillas_demo',
        ]

        for fixture in fixtures:
            self.stdout.write(f'Cargando {fixture}...')
            try:
                call_command('loaddata', fixture)
                self.stdout.write(self.style.SUCCESS(f'✓ {fixture} cargado'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error en {fixture}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS('\n✓ Todos los fixtures cargados'))

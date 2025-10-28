from django.core.management.base import BaseCommand
from turnos.models import Configuracion
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Ejecuta el proceso de planificación de turnos para una configuración específica'

    def add_arguments(self, parser):
        parser.add_argument('config_id', type=int, help='ID de la configuración a usar')

    def handle(self, *args, **options):
        config_id = options['config_id']
        logger.info(f"Buscando configuración con ID: {config_id}")
        
        try:
            config = Configuracion.objects.get(pk=config_id)
            logger.info(f"Configuración encontrada: {config.nombre}")
            
            from turnos.generador import GeneradorTurnos
            generador = GeneradorTurnos(config)
            resultado = generador.resolver()
            
            if resultado.get('success'):
                self.stdout.write(self.style.SUCCESS(f"Planificación completada para config ID {config_id}"))
                self.stdout.write(f"Asignaciones creadas: {resultado['num_asignaciones']}")
                if resultado['validacion']['violaciones']:
                    self.stdout.write(self.style.WARNING("Se encontraron violaciones:"))
                    for v in resultado['validacion']['violaciones']:
                        self.stdout.write(f" - {v['nombre']}: {v.get('detalles', '')}")
            else:
                self.stdout.write(self.style.ERROR(f"Error en planificación: {resultado.get('mensaje', '')}"))
                
        except Configuracion.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No se encontró configuración con ID {config_id}"))
        except Exception as e:
            logger.exception("Error durante la planificación")
            self.stdout.write(self.style.ERROR(f"Error inesperado: {str(e)}"))

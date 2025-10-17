import csv
from django.core.management.base import BaseCommand, CommandError
from turnos.models import Enfermera
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from datetime import datetime


class Command(BaseCommand):
    help = 'Importa enfermeras desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            'archivo_csv',
            type=str,
            help='Ruta al archivo CSV con los datos de las enfermeras'
        )
        parser.add_argument(
            '--actualizar',
            action='store_true',
            help='Actualiza enfermeras existentes (por email)',
        )
        parser.add_argument(
            '--ejemplo',
            action='store_true',
            help='Muestra un ejemplo del formato CSV esperado',
        )

    def handle(self, *args, **options):
        if options['ejemplo']:
            self.mostrar_ejemplo()
            return

        archivo_csv = options['archivo_csv']
        actualizar = options['actualizar']

        try:
            with open(archivo_csv, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                # Validar headers
                headers_esperados = ['nombre', 'email', 'telefono', 'dni', 'fecha_alta', 'activa', 'notas']
                headers_encontrados = reader.fieldnames

                if not all(h in headers_encontrados for h in ['nombre', 'email']):
                    raise CommandError(
                        'El archivo CSV debe contener al menos las columnas: nombre, email'
                    )

                creadas = 0
                actualizadas = 0
                errores = 0

                self.stdout.write(self.style.SUCCESS(f'Procesando archivo: {archivo_csv}'))
                self.stdout.write('=' * 60)

                for row_num, row in enumerate(reader, start=2):
                    try:
                        nombre = row['nombre'].strip()
                        email = row['email'].strip().lower()

                        if not nombre or not email:
                            self.stdout.write(
                                self.style.ERROR(f'✗ Fila {row_num}: Nombre y email son obligatorios')
                            )
                            errores += 1
                            continue

                        # Validar email
                        try:
                            validate_email(email)
                        except ValidationError:
                            self.stdout.write(
                                self.style.ERROR(f'✗ Fila {row_num}: Email inválido: {email}')
                            )
                            errores += 1
                            continue

                        # Parsear fecha_alta si existe
                        fecha_alta = None
                        if 'fecha_alta' in row and row['fecha_alta']:
                            try:
                                fecha_alta = datetime.strptime(row['fecha_alta'], '%Y-%m-%d').date()
                            except ValueError:
                                try:
                                    fecha_alta = datetime.strptime(row['fecha_alta'], '%d/%m/%Y').date()
                                except ValueError:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f'⚠ Fila {row_num}: Fecha inválida, usando fecha actual'
                                        )
                                    )

                        # Parsear activa
                        activa = True
                        if 'activa' in row and row['activa']:
                            activa = row['activa'].lower() in ['true', '1', 'si', 'sí', 's', 'yes', 'y']

                        # Datos opcionales
                        telefono = row.get('telefono', '').strip()
                        dni = row.get('dni', '').strip()
                        notas = row.get('notas', '').strip()

                        # Crear o actualizar
                        enfermera, created = Enfermera.objects.update_or_create(
                            email=email,
                            defaults={
                                'nombre': nombre,
                                'telefono': telefono,
                                'dni': dni,
                                'fecha_alta': fecha_alta,
                                'activa': activa,
                                'notas': notas,
                            }
                        )

                        if created:
                            creadas += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Fila {row_num}: Enfermera creada: {nombre} ({email})')
                            )
                        elif actualizar:
                            actualizadas += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Fila {row_num}: Enfermera actualizada: {nombre} ({email})')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'⚠ Fila {row_num}: Enfermera ya existe (usar --actualizar para modificar): {email}'
                                )
                            )

                    except Exception as e:
                        errores += 1
                        self.stdout.write(
                            self.style.ERROR(f'✗ Fila {row_num}: Error: {str(e)}')
                        )

                # Resumen
                self.stdout.write('\n' + '=' * 60)
                self.stdout.write(self.style.SUCCESS(f'✓ Enfermeras creadas: {creadas}'))
                if actualizar:
                    self.stdout.write(self.style.SUCCESS(f'✓ Enfermeras actualizadas: {actualizadas}'))
                self.stdout.write(self.style.ERROR(f'✗ Errores: {errores}'))
                self.stdout.write(self.style.SUCCESS(f'✓ Total enfermeras en BD: {Enfermera.objects.count()}'))

        except FileNotFoundError:
            raise CommandError(f'Archivo no encontrado: {archivo_csv}')
        except Exception as e:
            raise CommandError(f'Error al procesar archivo: {str(e)}')

    def mostrar_ejemplo(self):
        self.stdout.write(self.style.SUCCESS('\nEjemplo de formato CSV:'))
        self.stdout.write('=' * 60)
        ejemplo = """nombre,email,telefono,dni,fecha_alta,activa,notas
"María García López","maria.garcia@hospital.es","+34 612345678","12345678A","2024-01-15","true","Preferencia turno mañana"
"Ana Martínez Ruiz","ana.martinez@hospital.es","+34 623456789","23456789B","2024-02-01","true","Disponibilidad completa"
"Carmen Rodríguez","carmen.rodriguez@hospital.es","+34 634567890","34567890C","2024-03-01","false","De baja temporal"
"""
        self.stdout.write(ejemplo)
        self.stdout.write('\nNotas:')
        self.stdout.write('  - Campos obligatorios: nombre, email')
        self.stdout.write('  - Formato fecha: YYYY-MM-DD o DD/MM/YYYY')
        self.stdout.write('  - Campo activa: true/false, 1/0, si/no, yes/no')
        self.stdout.write('  - Encoding: UTF-8')

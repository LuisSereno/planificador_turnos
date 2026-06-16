from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from turnos.models import TipoTurno, Workspace
from datetime import time


class Command(BaseCommand):
    help = '''Gestiona los tipos de turno de un workspace.
    
    Permite crear tipos personalizados (Mañana, Tarde, Noche, Libre, Descanso, etc.)
    con acrónimos configurables manualmente.
    
    Ejemplos:
      # Crear los tipos estándar
      python manage.py crear_tipos_turno --crear-estandar
      
      # Crear un tipo personalizado
      python manage.py crear_tipos_turno --crear Libre L --sin-horario
      python manage.py crear_tipos_turno --crear Descanso D --sin-horario
      python manage.py crear_tipos_turno --crear "Guardia 24h" G24 --horas 07:00 07:00
      
      # Listar tipos existentes
      python manage.py crear_tipos_turno --listar
      
      # Actualizar un tipo
      python manage.py crear_tipos_turno --actualizar Mañana --codigo M
      
      # Recrear todos (elimina y recrea los estándar)
      python manage.py crear_tipos_turno --recrear
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-id',
            type=int,
            default=None,
            help='ID del workspace (por defecto None, es decir global)',
        )
        
        # Operaciones
        parser.add_argument(
            '--crear-estandar',
            action='store_true',
            help='Crea los tipos de turno estándar (Mañana, Tarde, Noche)',
        )
        
        parser.add_argument(
            '--crear',
            nargs=2,
            metavar=('NOMBRE', 'CODIGO'),
            help='Crea un nuevo tipo de turno personalizado',
        )
        
        parser.add_argument(
            '--horas',
            nargs=2,
            metavar=('INICIO', 'FIN'),
            help='Horarios para el turno (HH:MM HH:MM)',
        )
        
        parser.add_argument(
            '--sin-horario',
            action='store_true',
            help='Crear un turno sin horario específico (Libre, Descanso, etc.)',
        )
        
        parser.add_argument(
            '--incidencia',
            action='store_true',
            help='Marcar el turno como incidencia (no se asigna automáticamente)',
        )
        
        parser.add_argument(
            '--sustituto-libre',
            action='store_true',
            help='Marcar el turno como sustituto de Libre (actúa como día sin turno)',
        )
        
        parser.add_argument(
            '--descripcion',
            type=str,
            default='',
            help='Descripción del tipo de turno',
        )
        
        parser.add_argument(
            '--listar',
            action='store_true',
            help='Lista todos los tipos de turno existentes',
        )
        
        parser.add_argument(
            '--actualizar',
            type=str,
            help='Actualiza un tipo de turno existente',
        )
        
        parser.add_argument(
            '--activar',
            action='store_true',
            help='Activar el tipo de turno',
        )
        
        parser.add_argument(
            '--desactivar',
            action='store_true',
            help='Desactivar el tipo de turno',
        )
        
        parser.add_argument(
            '--recrear',
            action='store_true',
            help='Elimina todos los tipos y recrea los estándar',
        )

    def handle(self, *args, **options):
        workspace_id = options.get('workspace_id')
        workspace = None
        if workspace_id:
            try:
                workspace = Workspace.objects.get(id=workspace_id)
                self.stdout.write(self.style.SUCCESS(f'Workspace: {workspace.nombre}'))
            except Workspace.DoesNotExist:
                raise CommandError(f'Workspace con ID {workspace_id} no existe')
        
        if options['listar']:
            self._listar(workspace)
        elif options['recrear']:
            self._recrear(workspace)
        elif options['crear_estandar']:
            self._crear_estandar(workspace)
        elif options['crear']:
            self._crear_personalizado(workspace, options)
        elif options['actualizar']:
            self._actualizar(workspace, options)
        else:
            self.stdout.write(self.style.WARNING('Especifica una operación (--crear-estandar, --crear, --listar, --actualizar, --recrear)'))

    def _listar(self, workspace):
        """Lista todos los tipos de turno"""
        turnos = TipoTurno.objects.filter(workspace=workspace).all()
        if not turnos:
            self.stdout.write(self.style.WARNING('No hay tipos de turno definidos'))
            return
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('TIPOS DE TURNO DISPONIBLES')
        self.stdout.write('=' * 80)
        
        for turno in turnos:
            status = '✓ ACTIVO' if turno.activo else '✗ INACTIVO'
            tipo = '(INCIDENCIA)' if turno.es_incidencia else '(TURNO)'
            
            if turno.hora_inicio and turno.hora_fin:
                horario = f'{turno.hora_inicio.strftime("%H:%M")} - {turno.hora_fin.strftime("%H:%M")} ({turno.duracion_horas}h)'
            else:
                horario = 'Sin horario específico'
            
            self.stdout.write(
                f"  {turno.nombre:20} [{turno.codigo_corto:3}] {horario:30} {status:12} {tipo}"
            )
            if turno.descripcion:
                self.stdout.write(f"    → {turno.descripcion}")
        
        self.stdout.write('=' * 80 + '\n')

    def _crear_estandar(self, workspace):
        """Crea los tipos de turno estándar"""
        tipos_turno = [
            {
                'nombre': 'Mañana',
                'codigo_corto': 'M',
                'hora_inicio': time(7, 0),
                'hora_fin': time(15, 0),
                'descripcion': 'Turno de mañana (07:00 - 15:00)',
                'es_incidencia': False,
            },
            {
                'nombre': 'Tarde',
                'codigo_corto': 'T',
                'hora_inicio': time(15, 0),
                'hora_fin': time(23, 0),
                'descripcion': 'Turno de tarde (15:00 - 23:00)',
                'es_incidencia': False,
            },
            {
                'nombre': 'Noche',
                'codigo_corto': 'N',
                'hora_inicio': time(23, 0),
                'hora_fin': time(7, 0),
                'descripcion': 'Turno de noche (23:00 - 07:00)',
                'es_incidencia': False,
            },
        ]

        creados = 0
        existentes = 0

        for turno_data in tipos_turno:
            try:
                turno, created = TipoTurno.objects.get_or_create(
                    workspace=workspace,
                    nombre=turno_data['nombre'],
                    defaults={
                        'codigo_corto': turno_data['codigo_corto'],
                        'hora_inicio': turno_data['hora_inicio'],
                        'hora_fin': turno_data['hora_fin'],
                        'descripcion': turno_data['descripcion'],
                        'es_incidencia': turno_data['es_incidencia'],
                        'activo': True,
                    }
                )

                if created:
                    creados += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Tipo "{turno.nombre}" [{turno.codigo_corto}] creado '
                            f'({turno.hora_inicio.strftime("%H:%M")} - {turno.hora_fin.strftime("%H:%M")})'
                        )
                    )
                else:
                    existentes += 1
                    self.stdout.write(
                        self.style.WARNING(f'→ Tipo "{turno.nombre}" ya existe')
                    )
            except ValidationError as e:
                self.stdout.write(self.style.ERROR(f'✗ Error al crear "{turno_data["nombre"]}": {e}'))

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Creados: {creados}'))
        self.stdout.write(self.style.WARNING(f'Ya existían: {existentes}'))
        self.stdout.write(self.style.SUCCESS(f'Total tipos de turno: {TipoTurno.objects.filter(workspace=workspace).count()}'))

    def _crear_personalizado(self, workspace, options):
        """Crea un tipo de turno personalizado"""
        nombre, codigo = options['crear']
        
        # Validar código
        if len(codigo) > 5:
            raise CommandError('El código corto no puede tener más de 5 caracteres')
        
        # Preparar datos
        turno_data = {
            'workspace': workspace,
            'nombre': nombre,
            'codigo_corto': codigo,
            'descripcion': options.get('descripcion', ''),
            'es_incidencia': options.get('incidencia', False),
            'es_sustituto_libre': options.get('sustituto_libre', False),
            'activo': True,
        }
        
        # Configurar horarios
        if options['sin_horario']:
            turno_data['hora_inicio'] = None
            turno_data['hora_fin'] = None
        elif options.get('horas'):
            try:
                inicio_str, fin_str = options['horas']
                turno_data['hora_inicio'] = self._parsear_hora(inicio_str)
                turno_data['hora_fin'] = self._parsear_hora(fin_str)
            except ValueError as e:
                raise CommandError(f'Error al parsear horarios: {e}')
        else:
            raise CommandError('Especifica --sin-horario o --horas HH:MM HH:MM')
        
        # Crear
        try:
            turno = TipoTurno.objects.create(**turno_data)
            turno.full_clean()
            turno.save()
            
            self.stdout.write(self.style.SUCCESS(f'✓ Tipo "{turno.nombre}" [{turno.codigo_corto}] creado exitosamente'))
            if turno.hora_inicio and turno.hora_fin:
                self.stdout.write(f"  Horario: {turno.hora_inicio.strftime('%H:%M')} - {turno.hora_fin.strftime('%H:%M')} ({turno.duracion_horas}h)")
            else:
                self.stdout.write('  Horario: Sin horario específico')
            if turno.es_sustituto_libre:
                self.stdout.write('  Clasificación: SUSTITUTO DE LIBRE (se trata como día sin turno)')
            elif turno.es_incidencia:
                self.stdout.write('  Clasificación: INCIDENCIA (no se asigna automáticamente)')
            
        except ValidationError as e:
            raise CommandError(f'Error al crear tipo: {e}')

    def _actualizar(self, workspace, options):
        """Actualiza un tipo de turno existente"""
        nombre_actual = options['actualizar']
        
        try:
            turno = TipoTurno.objects.get(workspace=workspace, nombre=nombre_actual)
        except TipoTurno.DoesNotExist:
            raise CommandError(f'No existe tipo de turno "{nombre_actual}"')
        
        # Actualizar campos
        if options.get('codigo'):
            turno.codigo_corto = options['codigo']
        
        if options.get('horas'):
            try:
                inicio_str, fin_str = options['horas']
                turno.hora_inicio = self._parsear_hora(inicio_str)
                turno.hora_fin = self._parsear_hora(fin_str)
            except ValueError as e:
                raise CommandError(f'Error al parsear horarios: {e}')
        
        if options.get('descripcion'):
            turno.descripcion = options['descripcion']
        
        if options['activar']:
            turno.activo = True
        elif options['desactivar']:
            turno.activo = False
        
        try:
            turno.full_clean()
            turno.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Tipo "{turno.nombre}" actualizado exitosamente'))
        except ValidationError as e:
            raise CommandError(f'Error al actualizar tipo: {e}')

    def _recrear(self, workspace):
        """Elimina todos los tipos y recrea los estándar"""
        confirmacion = input('Estás seguro de que quieres eliminar TODOS los tipos de turno existentes? (s/n): ')
        if confirmacion.lower() != 's':
            self.stdout.write(self.style.WARNING('Operación cancelada'))
            return
        
        count = TipoTurno.objects.filter(workspace=workspace).count()
        TipoTurno.objects.filter(workspace=workspace).delete()
        self.stdout.write(self.style.WARNING(f'{count} tipos de turno eliminados'))
        
        self._crear_estandar(workspace)

    @staticmethod
    def _parsear_hora(hora_str):
        """Parsea una cadena HH:MM a un objeto time"""
        try:
            h, m = hora_str.split(':')
            return time(int(h), int(m))
        except (ValueError, AttributeError):
            raise ValueError(f'Formato inválido para hora: {hora_str}. Usa HH:MM')


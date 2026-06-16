from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q
from django.contrib.auth.models import User
from turnos.models import (
    Enfermera, TipoTurno, ConfiguracionPlanificacion,
    Ejecucion,
)


class Command(BaseCommand):
    help = 'Muestra estadísticas del sistema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('ESTADÍSTICAS DEL SISTEMA - PLANIFICADOR DE TURNOS'))
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))

        # Enfermeras
        total_enfermeras = Enfermera.objects.count()
        activas = Enfermera.objects.filter(activa=True).count()
        inactivas = Enfermera.objects.filter(activa=False).count()

        self.stdout.write(self.style.SUCCESS('ENFERMERAS'))
        self.stdout.write(f'  Total: {total_enfermeras}')
        self.stdout.write(f'  Activas: {activas}')
        self.stdout.write(f'  Inactivas: {inactivas}')
        self.stdout.write('')

        # Tipos de Turno
        total_turnos = TipoTurno.objects.count()
        turnos_activos = TipoTurno.objects.filter(activo=True).count()

        self.stdout.write(self.style.SUCCESS('TIPOS DE TURNO'))
        self.stdout.write(f'  Total: {total_turnos}')
        self.stdout.write(f'  Activos: {turnos_activos}')
        self.stdout.write('')

        # Configuraciones
        total_configs = ConfiguracionPlanificacion.objects.count()
        configs_activas = ConfiguracionPlanificacion.objects.filter(activa=True).count()

        self.stdout.write(self.style.SUCCESS('CONFIGURACIONES'))
        self.stdout.write(f'  Total: {total_configs}')
        self.stdout.write(f'  Activas: {configs_activas}')
        self.stdout.write('')

        # Ejecuciones
        total_ejecuciones = Ejecucion.objects.count()
        completadas = Ejecucion.objects.filter(estado='COMPLETADA').count()
        fallidas = Ejecucion.objects.filter(estado='ERROR').count()
        pendientes = Ejecucion.objects.filter(estado='PENDIENTE').count()
        procesando = Ejecucion.objects.filter(estado='PROCESANDO').count()

        self.stdout.write(self.style.SUCCESS('EJECUCIONES'))
        self.stdout.write(f'  Total: {total_ejecuciones}')
        self.stdout.write(f'  Completadas: {completadas}')
        self.stdout.write(f'  Fallidas: {fallidas}')
        self.stdout.write(f'  Pendientes: {pendientes}')
        self.stdout.write(f'  Procesando: {procesando}')

        if completadas > 0:
            tasa_exito = (completadas / total_ejecuciones) * 100
            self.stdout.write(f'  Tasa de exito: {tasa_exito:.1f}%')

            stats = Ejecucion.objects.filter(estado='COMPLETADA').aggregate(
                pen_promedio=Avg('penalizacion_total'),
            )

            if stats['pen_promedio']:
                self.stdout.write(f'  Penalizacion promedio: {stats["pen_promedio"]:.2f}')

            # Duracion promedio calculada via property
            duraciones = [
                e.duracion for e in
                Ejecucion.objects.filter(estado='COMPLETADA')
                if e.duracion is not None
            ]
            if duraciones:
                dur_promedio = sum(duraciones) / len(duraciones)
                self.stdout.write(f'  Duracion promedio: {dur_promedio:.2f}s')

        self.stdout.write('')

        # Usuarios
        total_usuarios = User.objects.count()
        usuarios_activos = User.objects.filter(is_active=True).count()
        admins = User.objects.filter(is_superuser=True).count()
        staff = User.objects.filter(is_staff=True).count()

        self.stdout.write(self.style.SUCCESS('USUARIOS'))
        self.stdout.write(f'  Total: {total_usuarios}')
        self.stdout.write(f'  Activos: {usuarios_activos}')
        self.stdout.write(f'  Administradores: {admins}')
        self.stdout.write(f'  Staff: {staff}')
        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))

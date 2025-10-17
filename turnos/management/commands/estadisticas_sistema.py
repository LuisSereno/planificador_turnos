from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q
from turnos.models import (
    Enfermera, TipoTurno, ConfiguracionPlanificacion,
    EjecucionPlanificacion, Usuario, AuditLog
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

        self.stdout.write(self.style.SUCCESS('👥 ENFERMERAS'))
        self.stdout.write(f'  Total: {total_enfermeras}')
        self.stdout.write(f'  Activas: {activas}')
        self.stdout.write(f'  Inactivas: {inactivas}')
        self.stdout.write('')

        # Tipos de Turno
        total_turnos = TipoTurno.objects.count()
        turnos_activos = TipoTurno.objects.filter(activo=True).count()

        self.stdout.write(self.style.SUCCESS('🕐 TIPOS DE TURNO'))
        self.stdout.write(f'  Total: {total_turnos}')
        self.stdout.write(f'  Activos: {turnos_activos}')
        self.stdout.write('')

        # Configuraciones
        total_configs = ConfiguracionPlanificacion.objects.count()
        configs_activas = ConfiguracionPlanificacion.objects.filter(activa=True).count()

        self.stdout.write(self.style.SUCCESS('⚙️  CONFIGURACIONES'))
        self.stdout.write(f'  Total: {total_configs}')
        self.stdout.write(f'  Activas: {configs_activas}')
        self.stdout.write('')

        # Ejecuciones
        total_ejecuciones = EjecucionPlanificacion.objects.count()
        completadas = EjecucionPlanificacion.objects.filter(estado='COMPLETADA').count()
        fallidas = EjecucionPlanificacion.objects.filter(estado='ERROR').count()
        pendientes = EjecucionPlanificacion.objects.filter(estado='PENDIENTE').count()
        procesando = EjecucionPlanificacion.objects.filter(estado='PROCESANDO').count()

        self.stdout.write(self.style.SUCCESS('▶️  EJECUCIONES'))
        self.stdout.write(f'  Total: {total_ejecuciones}')
        self.stdout.write(f'  Completadas: {completadas}')
        self.stdout.write(f'  Fallidas: {fallidas}')
        self.stdout.write(f'  Pendientes: {pendientes}')
        self.stdout.write(f'  Procesando: {procesando}')

        if completadas > 0:
            tasa_exito = (completadas / total_ejecuciones) * 100
            self.stdout.write(f'  Tasa de éxito: {tasa_exito:.1f}%')

            # Promedio de penalización y duración
            stats = EjecucionPlanificacion.objects.filter(estado='COMPLETADA').aggregate(
                pen_promedio=Avg('penalizacion_total'),
                dur_promedio=Avg('duracion')
            )

            if stats['pen_promedio']:
                self.stdout.write(f'  Penalización promedio: {stats["pen_promedio"]:.2f}')
            if stats['dur_promedio']:
                self.stdout.write(f'  Duración promedio: {stats["dur_promedio"]:.2f}s')

        self.stdout.write('')

        # Usuarios
        total_usuarios = Usuario.objects.count()
        usuarios_activos = Usuario.objects.filter(is_active=True).count()
        admins = Usuario.objects.filter(rol='ADMIN').count()
        gestores = Usuario.objects.filter(rol='GESTOR').count()

        self.stdout.write(self.style.SUCCESS('👤 USUARIOS'))
        self.stdout.write(f'  Total: {total_usuarios}')
        self.stdout.write(f'  Activos: {usuarios_activos}')
        self.stdout.write(f'  Administradores: {admins}')
        self.stdout.write(f'  Gestores: {gestores}')
        self.stdout.write('')

        # Auditoría
        total_logs = AuditLog.objects.count()

        self.stdout.write(self.style.SUCCESS('📋 AUDITORÍA'))
        self.stdout.write(f'  Total de logs: {total_logs}')
        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))

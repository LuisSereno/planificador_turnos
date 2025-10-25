"""
Admin configuration for the turnos app
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Workspace, Enfermera, TipoTurno, ConfiguracionPlanificacion,
    Ejecucion, Planilla, AsignacionTurno
)


@admin.register(TipoTurno)
class TipoTurnoAdmin(admin.ModelAdmin):
    list_display = ['get_nombre_display', 'hora_inicio', 'hora_fin', 'duracion_horas', 'activo', 'color_badge']
    list_filter = ['nombre', 'activo']
    ordering = ['nombre']

    fieldsets = (
        ('Información del Turno', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Horarios', {
            'fields': ('hora_inicio', 'hora_fin')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )

    def color_badge(self, obj):
        """Muestra un badge de color según el turno"""
        colors = {
            'MANANA': '#ffc107',
            'TARDE': '#17a2b8',
            'NOCHE': '#343a40'
        }
        color = colors.get(obj.nombre, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 5px;">{}</span>',
            color,
            obj.get_nombre_display()
        )

    color_badge.short_description = 'Vista previa'


@admin.register(ConfiguracionPlanificacion)
class ConfiguracionPlanificacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activa', 'num_dias', 'fecha_inicio', 'creado_por', 'fecha_creacion', 'ver_detalle']
    list_filter = ['activa', 'fecha_creacion', 'fecha_inicio']
    search_fields = ['nombre', 'descripcion']
    date_hierarchy = 'fecha_creacion'
    filter_horizontal = ['enfermeras', 'turnos']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'activa')
        }),
        ('Configuración Temporal', {
            'fields': ('num_dias', 'fecha_inicio')
        }),
        ('Personal y Turnos', {
            'fields': ('enfermeras', 'turnos')
        }),
        ('Demanda', {
            'fields': ('demanda_por_turno',)
        }),
        ('Restricciones', {
            'fields': ('restricciones_duras', 'restricciones_blandas'),
            'classes': ('collapse',)
        }),
        ('Configuración de Ejecución', {
            'fields': ('num_trabajadores', 'tiempo_maximo_segundos', 'seed')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )

    def ver_detalle(self, obj):
        """Link para ver el detalle"""
        url = reverse('turnos:config_detalle', args=[obj.id])
        return format_html('<a href="{}" target="_blank">Ver detalle</a>', url)

    ver_detalle.short_description = 'Detalle'

    def save_model(self, request, obj, form, change):
        """Asigna el usuario actual si es una creación nueva"""
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Ejecucion)
class EjecucionAdmin(admin.ModelAdmin):
    list_display = ['id', 'configuracion', 'estado_badge', 'fecha_inicio', 'duracion', 'es_optima',
                    'penalizacion_total', 'ver_resultado']
    list_filter = ['estado', 'es_optima', 'fecha_inicio']
    search_fields = ['configuracion__nombre']
    date_hierarchy = 'fecha_inicio'
    readonly_fields = ['fecha_inicio', 'fecha_fin', 'duracion', 'mensajes']

    fieldsets = (
        ('Configuración', {
            'fields': ('configuracion',)
        }),
        ('Estado de Ejecución', {
            'fields': ('estado', 'fecha_inicio', 'fecha_fin', 'duracion')
        }),
        ('Resultados', {
            'fields': ('es_optima', 'penalizacion_total', 'resultado', 'mensajes')
        }),
        ('Planilla Generada', {
            'fields': ('planilla',)
        }),
    )

    def estado_badge(self, obj):
        """Muestra un badge de color según el estado"""
        colors = {
            'PENDIENTE': '#6c757d',
            'PROCESANDO': '#ffc107',
            'COMPLETADA': '#28a745',
            'ERROR': '#dc3545'
        }
        color = colors.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 5px;">{}</span>',
            color,
            obj.get_estado_display()
        )

    estado_badge.short_description = 'Estado'

    def ver_resultado(self, obj):
        """Link para ver el resultado"""
        if obj.estado == 'COMPLETADA':
            url = reverse('turnos:ejecucion_detalle', args=[obj.id])
            return format_html('<a href="{}" target="_blank">Ver resultado</a>', url)
        return '-'

    ver_resultado.short_description = 'Resultado'


@admin.register(Planilla)
class PlanillaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ejecucion', 'fecha_inicio', 'fecha_fin', 'num_dias', 'total_asignaciones']
    list_filter = ['fecha_inicio', 'fecha_fin']
    search_fields = ['nombre', 'descripcion', 'ejecucion__configuracion__nombre']
    date_hierarchy = 'fecha_inicio'
    readonly_fields = ['total_asignaciones']

    def total_asignaciones(self, obj):
        """Muestra el total de asignaciones"""
        count = obj.asignaciones.count()
        return format_html('<b>{}</b> asignaciones', count)

    total_asignaciones.short_description = 'Total Asignaciones'


@admin.register(AsignacionTurno)
class AsignacionTurnoAdmin(admin.ModelAdmin):
    list_display = ['enfermera', 'turno', 'fecha', 'planilla', 'es_dia_libre']
    list_filter = ['fecha', 'turno', 'es_dia_libre']
    search_fields = ['enfermera__nombre', 'planilla__nombre']
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Asignación', {
            'fields': ('planilla', 'enfermera', 'fecha')
        }),
        ('Turno', {
            'fields': ('turno', 'es_dia_libre')
        }),
        ('Información Adicional', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'creado_por', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    filter_horizontal = ['usuarios']


@admin.register(Enfermera)
class EnfermeraAdmin(admin.ModelAdmin):
    # TEMPORALMENTE sin workspace hasta que se ejecuten las migraciones
    list_display = ['nombre', 'email', 'activa']
    list_filter = ['activa']
    search_fields = ['nombre', 'email', 'dni']

    # DESPUÉS de ejecutar las migraciones, descomenta estas líneas:
    # list_display = ['nombre', 'workspace', 'email', 'activa']
    # list_filter = ['workspace', 'activa']


# Personalización del admin site
admin.site.site_header = "Sistema de Planificación de Turnos"
admin.site.site_title = "Administración de Turnos"
admin.site.index_title = "Panel de Administración"

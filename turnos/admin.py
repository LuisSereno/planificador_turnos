"""
Admin configuration for the turnos app
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django import forms
from .models import (
    Workspace, Enfermera, TipoTurno, ConfiguracionPlanificacion,
    Ejecucion, Planilla, AsignacionTurno, PatronTurnos, TipoPatron,
    ContratoEnfermera, RotacionBase, CeldaRotacion, AsignacionRotacionEnfermera,
    Incidencia, BalanceHistoricoEnfermera,
)


@admin.register(TipoTurno)
class TipoTurnoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo_corto', 'hora_inicio', 'hora_fin', 'duracion_horas', 'es_incidencia', 'activo', 'color_badge']
    list_filter = ['nombre', 'es_incidencia', 'activo']
    search_fields = ['nombre', 'codigo_corto']
    ordering = ['nombre']

    fieldsets = (
        ('Información del Turno', {
            'fields': ('nombre', 'codigo_corto', 'descripcion')
        }),
        ('Horarios', {
            'fields': ('hora_inicio', 'hora_fin'),
            'description': 'Opcional para turnos como Libre o Descanso'
        }),
        ('Clasificación', {
            'fields': ('es_incidencia',),
            'description': 'Marcar si se trata de una incidencia (no se asigna automáticamente)'
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )

    def color_badge(self, obj):
        """Muestra un badge de color según el turno"""
        colors = {
            'Mañana': '#ffc107',
            'Tarde': '#17a2b8',
            'Noche': '#343a40',
            'Libre': '#28a745',
            'Descanso': '#6c757d',
        }
        color = colors.get(obj.nombre, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 5px;">{} [{}]</span>',
            color,
            obj.nombre,
            obj.codigo_corto
        )

    color_badge.short_description = 'Vista previa'


class PatronTurnosAdminForm(forms.ModelForm):
    """Formulario con ayuda contextual según el tipo"""
    
    class Meta:
        model = PatronTurnos
        fields = '__all__'
        widgets = {
            'configuracion': forms.Textarea(attrs={
                'rows': 10,
                'placeholder': '''Ejemplos según tipo:

DESCANSO_POST_TURNO:
{
  "turno_tipo": "NOCHE",
  "cantidad_consecutiva": 2,
  "dias_descanso_requeridos": 3
}

MAX_CONSECUTIVOS:
{
  "turno_tipo": "CUALQUIERA",
  "cantidad_maxima": 5
}

SECUENCIA_OBLIGATORIA:
{
  "secuencia": ["MAÑANA", "TARDE", "NOCHE"],
  "ciclica": true
}

BLOQUEO_TRANSICION:
{
  "turno_origen": "NOCHE",
  "turno_destino": "MAÑANA",
  "dias_minimos_entre": 1
}

COBERTURA_MINIMA:
{
  "turno_tipo": "NOCHE",
  "enfermeras_minimas": 2,
  "aplicar_dias": [5, 6, 0]
}'''
            })
        }

@admin.register(PatronTurnos)
class PatronTurnosAdmin(admin.ModelAdmin):
    form = PatronTurnosAdminForm
    list_display = ['nombre', 'tipo', 'activo', 'es_restriccion_dura', 'peso_penalizacion', 'fecha_creacion']
    list_filter = ['tipo', 'activo', 'es_restriccion_dura']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'tipo', 'activo')
        }),
        ('Configuración de Restricción', {
            'fields': ('es_restriccion_dura', 'peso_penalizacion', 'configuracion')
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_modificacion', 'creado_por'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.creado_por:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(ConfiguracionPlanificacion)
class ConfiguracionPlanificacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activa', 'num_dias', 'fecha_inicio', 'creado_por', 'fecha_creacion', 'ver_detalle']
    list_filter = ['activa', 'fecha_creacion', 'fecha_inicio']
    search_fields = ['nombre', 'descripcion']
    date_hierarchy = 'fecha_creacion'
    filter_horizontal = ['enfermeras', 'turnos', 'patrones_turnos']
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
            'fields': ('restricciones_duras', 'restricciones_blandas', 'patrones_turnos'),
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


# ============================================================================
# ADMIN PARA NUEVOS MODELOS DE DOMINIO
# ============================================================================


class CeldaRotacionInline(admin.TabularInline):
    """Inline para editar celdas de rotación dentro de RotacionBase"""
    model = CeldaRotacion
    extra = 1
    ordering = ['orden']


@admin.register(RotacionBase)
class RotacionBaseAdmin(admin.ModelAdmin):
    """Administración de rotaciones base"""
    list_display = ['nombre', 'ciclo_dias', 'workspace', 'descripcion_corta']
    list_filter = ['workspace']
    search_fields = ['nombre', 'descripcion']
    inlines = [CeldaRotacionInline]
    
    fieldsets = (
        ('Información de Rotación', {
            'fields': ('nombre', 'descripcion', 'workspace')
        }),
        ('Configuración del Ciclo', {
            'fields': ('ciclo_dias',)
        }),
    )
    
    def descripcion_corta(self, obj):
        if obj.descripcion:
            return obj.descripcion[:50] + '...' if len(obj.descripcion) > 50 else obj.descripcion
        return '-'
    descripcion_corta.short_description = 'Descripción'


@admin.register(AsignacionRotacionEnfermera)
class AsignacionRotacionEnfermeraAdmin(admin.ModelAdmin):
    """Administración de asignaciones de rotación a enfermeras"""
    list_display = ['enfermera', 'rotacion', 'desfase', 'fecha_inicio', 'fecha_fin', 'activa']
    list_filter = ['rotacion', 'fecha_inicio']
    search_fields = ['enfermera__nombre', 'rotacion__nombre']
    date_hierarchy = 'fecha_inicio'
    
    fieldsets = (
        ('Asignación', {
            'fields': ('enfermera', 'rotacion', 'desfase')
        }),
        ('Vigencia', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
    )
    
    def activa(self, obj):
        from django.utils import timezone
        if not obj.fecha_fin:
            return True
        return obj.fecha_fin >= timezone.now().date()
    activa.boolean = True
    activa.short_description = 'Activa'


@admin.register(ContratoEnfermera)
class ContratoEnfermeraAdmin(admin.ModelAdmin):
    """Administración de contratos de enfermeras"""
    list_display = ['enfermera', 'horas_semana_objetivo', 'horas_anuales_objetivo', 'porcentaje_jornada', 'vigente']
    list_filter = ['porcentaje_jornada', 'fecha_inicio_vigencia']
    search_fields = ['enfermera__nombre', 'enfermera__email']
    
    fieldsets = (
        ('Enfermera', {
            'fields': ('enfermera',)
        }),
        ('Horas Objetivo', {
            'fields': ('horas_semana_objetivo', 'horas_anuales_objetivo', 'porcentaje_jornada')
        }),
        ('Vigencia', {
            'fields': ('fecha_inicio_vigencia', 'fecha_fin_vigencia')
        }),
    )
    
    def vigente(self, obj):
        from django.utils import timezone
        if not obj.fecha_fin_vigencia:
            return True
        return obj.fecha_fin_vigencia >= timezone.now().date()
    vigente.boolean = True
    vigente.short_description = 'Vigente'


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    """Administración de incidencias"""
    list_display = ['enfermera', 'tipo', 'fecha_inicio', 'fecha_fin', 'duracion_dias', 'tiene_turno_fijo']
    list_filter = ['tipo', 'fecha_inicio']
    search_fields = ['enfermera__nombre', 'observaciones']
    date_hierarchy = 'fecha_inicio'
    
    fieldsets = (
        ('Incidencia', {
            'fields': ('enfermera', 'tipo', 'observaciones')
        }),
        ('Período', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Asignación Fija', {
            'fields': ('turno_fijo',),
            'classes': ('collapse',),
            'description': 'Solo para tipo ASIGNACION_FIJA'
        }),
    )
    
    def duracion_dias(self, obj):
        return (obj.fecha_fin - obj.fecha_inicio).days + 1
    duracion_dias.short_description = 'Duración (días)'
    
    def tiene_turno_fijo(self, obj):
        return '✓' if obj.turno_fijo else '-'
    tiene_turno_fijo.short_description = 'Turno Fijo'


@admin.register(BalanceHistoricoEnfermera)
class BalanceHistoricoEnfermeraAdmin(admin.ModelAdmin):
    """Administración de balances históricos"""
    list_display = [
        'enfermera', 
        'periodo_referencia', 
        'horas_acumuladas_previas',
        'noches_acumuladas',
        'fines_semana_acumulados',
        'festivos_acumulados',
        'fecha_actualizacion',
    ]
    list_filter = ['periodo_referencia', 'fecha_actualizacion']
    search_fields = ['enfermera__nombre']
    
    fieldsets = (
        ('Enfermera y Período', {
            'fields': ('enfermera', 'periodo_referencia')
        }),
        ('Horas Acumuladas', {
            'fields': ('horas_acumuladas_previas',)
        }),
        ('Distribución de Turnos', {
            'fields': ('noches_acumuladas', 'fines_semana_acumulados', 'festivos_acumulados')
        }),
        ('Último Turno', {
            'fields': ('ultimo_turno_fecha', 'ultimo_turno_tipo'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['fecha_actualizacion']

from django.views.generic import TemplateView
from .views import CambiarWorkspaceView
"""
URL configuration for turnos app
"""
from django.urls import path
from . import views
from django.views.generic import RedirectView, TemplateView

app_name = 'turnos'

urlpatterns = [
    path('configuracion/<int:pk>/restricciones/', ConfiguracionRestriccionesView.as_view(), name='config_restricciones'),
    path('workspace/cambiar/', CambiarWorkspaceView.as_view(), name='cambiar_workspace'),
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Configuraciones
    path('configuraciones/', views.ConfiguracionListView.as_view(), name='config_lista'),
    path('configuraciones/nueva/', views.ConfiguracionCreateView.as_view(), name='config_nueva'),
    # Wizard simple (deprecado - puedes eliminarlo)
    path('configuraciones/wizard/', views.ConfiguracionWizardView.as_view(), name='config_wizard'),

    # Wizard paso a paso (SessionWizardView) - CORREGIDO
    path('configuraciones/wizard/step-by-step/',
         views.ConfiguracionWizardViewStepByStep.as_view(views.FORMS),
         name='config_wizard_step_by_step'),

    path('configuraciones/wizard/step-by-step/<slug:step>/',
         views.ConfiguracionWizardViewStepByStep.as_view(views.FORMS),
         name='config_wizard_step'),

    path('configuraciones/<int:pk>/', views.ConfiguracionDetailView.as_view(), name='config_detalle'),
    path('configuraciones/<int:pk>/editar/', views.ConfiguracionUpdateView.as_view(), name='config_editar'),
    path('configuraciones/<int:pk>/eliminar/', views.ConfiguracionDeleteView.as_view(), name='config_eliminar'),
    path('configuraciones/<int:pk>/duplicar/', views.ConfiguracionDuplicarView.as_view(), name='config_duplicar'),
    path('configuraciones/<int:pk>/ejecutar/', views.EjecutarPlanificacionView.as_view(), name='ejecutar_planificacion'),
    path('configuraciones/<int:pk>/exportar/json/', views.ExportarConfiguracionJSONView.as_view(), name='config_exportar_json'),

    # Ejecuciones
    path('ejecuciones/', views.EjecucionListView.as_view(), name='ejecucion_lista'),
    path('ejecuciones/<int:pk>/', views.EjecucionDetailView.as_view(), name='ejecucion_detalle'),
    path('ejecuciones/<int:pk>/eliminar/', views.EjecucionDeleteView.as_view(), name='ejecucion_eliminar'),
    path('ejecuciones/rapida/', views.EjecucionRapidaView.as_view(), name='ejecutar_rapido'),

    # Exportaciones
    path('ejecuciones/<int:pk>/exportar/excel/', views.ExportarEjecucionExcelView.as_view(), name='ejecucion_exportar_excel'),
    path('ejecuciones/<int:pk>/exportar/pdf/', views.ExportarEjecucionPDFView.as_view(), name='ejecucion_exportar_pdf'),
    path('ejecuciones/<int:pk>/exportar/csv/', views.ExportarEjecucionCSVView.as_view(), name='ejecucion_exportar_csv'),
    path('ejecuciones/<int:pk>/exportar/json/', views.ExportarEjecucionJSONView.as_view(), name='ejecucion_exportar_json'),
    path('ejecuciones/<int:pk>/exportar/ical/', views.ExportarEjecucionICalView.as_view(), name='ejecucion_exportar_ical'),

    # Enfermeras
    path('enfermeras/', views.EnfermeraListView.as_view(), name='enfermera_lista'),
    path('enfermeras/nueva/', views.EnfermeraCreateView.as_view(), name='enfermera_nueva'),
    path('enfermeras/<int:pk>/', views.EnfermeraDetailView.as_view(), name='enfermera_detalle'),
    path('enfermeras/<int:pk>/editar/', views.EnfermeraUpdateView.as_view(), name='enfermera_editar'),
    path('enfermeras/<int:pk>/eliminar/', views.EnfermeraDeleteView.as_view(), name='enfermera_eliminar'),
    path('enfermeras/importar/', views.ImportarEnfermerasView.as_view(), name='enfermera_importar'),
    path('enfermeras/plantilla/', views.DescargarPlantillaEnfermerasView.as_view(), name='enfermera_plantilla_excel'),

    # Tipos de Turno
    path('tipos-turno/', views.TipoTurnoListView.as_view(), name='tipo_turno_lista'),
    path('tipos-turno/nuevo/', views.TipoTurnoCreateView.as_view(), name='tipo_turno_nuevo'),
    path('tipos-turno/<int:pk>/editar/', views.TipoTurnoUpdateView.as_view(), name='tipo_turno_editar'),
    path('tipos-turno/<int:pk>/eliminar/', views.TipoTurnoDeleteView.as_view(), name='tipo_turno_eliminar'),
    path('tipos-turno/predeterminados/', views.CrearTurnosPredeterminadosView.as_view(), name='tipo_turno_crear_predeterminados'),

    # Planillas
    path('planillas/', views.PlanillaListView.as_view(), name='planilla_lista'),
    path('planillas/<int:pk>/', views.PlanillaDetailView.as_view(), name='planilla_detalle'),
    path('planillas/<int:pk>/eliminar/', views.PlanillaDeleteView.as_view(), name='planilla_eliminar'),
    path('planillas/<int:pk>/exportar/excel/', views.ExportarPlanillaExcelView.as_view(), name='planilla_exportar_excel'),
    path('planillas/<int:pk>/exportar/pdf/', views.ExportarPlanillaPDFView.as_view(), name='planilla_exportar_pdf'),

    # Reportes
    path('reportes/', views.ReportesView.as_view(), name='reportes'),
    path('reportes/carga/', views.ReporteCargaView.as_view(), name='reporte_carga'),
    path('reportes/conflictos/', views.ReporteConflictosView.as_view(), name='reporte_conflictos'),
    path('reportes/tendencias/', views.ReporteTendenciasView.as_view(), name='reporte_tendencias'),

    # Resultados
    path('resultados/<int:pk>/calendario/', views.ResultadoCalendarioView.as_view(), name='resultado_calendario'),
    path('resultados/<int:pk>/estadisticas/', views.ResultadoEstadisticasView.as_view(), name='resultado_estadisticas'),
    path('resultados/<int:pk>/tabla/', views.ResultadoTablaView.as_view(), name='resultado_tabla'),
    path('resultados/comparar/', views.ResultadoCompararView.as_view(), name='resultado_comparar'),

    # Usuario
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('preferencias/', views.PreferenciasView.as_view(), name='preferencias'),
    path('preferencias/guardar/', views.GuardarPreferenciasView.as_view(), name='guardar_preferencias'),

    # Utilidades
    path('maintenance/', views.MaintenanceView.as_view(), name='maintenance'),
    # URLs que faltan
    path('terminos/', TemplateView.as_view(template_name='terminos.html'), name='terminos'),
    path('privacidad/', TemplateView.as_view(template_name='privacidad.html'), name='privacidad'),

]

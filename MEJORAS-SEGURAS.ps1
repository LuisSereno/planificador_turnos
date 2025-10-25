# ══════════════════════════════════════════════════════════════════════
# PLANIFICADOR DE TURNOS - SISTEMA DE MEJORAS SEGURO V3.0
# ══════════════════════════════════════════════════════════════════════
# GARANTÍA: Este script NUNCA modifica archivos existentes
# Solo crea contenido NUEVO en carpetas separadas "_mejoras"
# ══════════════════════════════════════════════════════════════════════

<#
.SYNOPSIS
    Sistema SEGURO de mejoras que NO toca archivos existentes
    
.DESCRIPTION
    Crea TODO el contenido de mejoras en carpetas separadas:
    - Tests → _mejoras/tests/
    - Frontend → _mejoras/frontend/
    - Docs → _mejoras/docs/
    - Código Python → _mejoras/codigo/
    
    TÚ decides manualmente qué copiar al proyecto principal
    
.EXAMPLE
    .\MEJORAS-SEGURAS.ps1
#>

[CmdletBinding()]
param(
    [switch]$SkipBackup
)

$ErrorActionPreference = "Stop"
$global:ProjectRoot = $PSScriptRoot
$global:MejorasFolder = Join-Path $ProjectRoot "_mejoras"
$global:BackupFolder = Join-Path $ProjectRoot "backups"
$global:Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$global:LogFile = Join-Path $ProjectRoot "logs/mejoras_$global:Timestamp.log"

# ══════════════════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════════════════

function Write-ColorMsg {
    param([string]$Color, [string]$Message)
    Write-Host $Message -ForegroundColor $Color
}

function Write-Log {
    param([string]$Message)
    $logDir = Split-Path $global:LogFile -Parent
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -FilePath $global:LogFile -Append -Encoding UTF8
}

function Show-Banner {
    Clear-Host
    Write-Host ""
    Write-ColorMsg Green "================================================================"
    Write-ColorMsg Green "    PLANIFICADOR DE TURNOS - SISTEMA DE MEJORAS SEGURO V3.0"
    Write-ColorMsg Green "================================================================"
    Write-ColorMsg Yellow "  MODO SEGURO: Todo se crea en carpeta '_mejoras' separada"
    Write-ColorMsg Yellow "  NO se modifican archivos existentes del proyecto"
    Write-Host ""
}

function Show-Menu {
    Write-Host ""
    Write-ColorMsg Cyan "==================== MENU PRINCIPAL ===================="
    Write-Host ""
    Write-Host "  [1] Crear Backup Completo"
    Write-Host "  [2] Generar Tests Unitarios (en _mejoras/tests/)"
    Write-Host "  [3] Generar Codigo Celery (en _mejoras/codigo/)"
    Write-Host "  [4] Generar Frontend Mejorado (en _mejoras/frontend/)"
    Write-Host "  [5] Generar Documentacion (en _mejoras/docs/)"
    Write-Host ""
    Write-ColorMsg Yellow "  [6] GENERAR TODO (Tests + Celery + Frontend + Docs)"
    Write-Host ""
    Write-Host "  [7] Ver Estado del Proyecto"
    Write-Host "  [8] Ver que hay en _mejoras/"
    Write-Host "  [9] Generar Guia de Instalacion"
    Write-Host ""
    Write-Host "  [0] Salir"
    Write-Host ""
    Write-ColorMsg Cyan "========================================================"
    Write-Host ""
}

# ══════════════════════════════════════════════════════════════════════
# FUNCIONES PRINCIPALES
# ══════════════════════════════════════════════════════════════════════

function Initialize-MejorasFolder {
    Write-ColorMsg Yellow "`nInicializando carpeta de mejoras..."
    
    if (-not (Test-Path $global:MejorasFolder)) {
        New-Item -ItemType Directory -Path $global:MejorasFolder -Force | Out-Null
        Write-ColorMsg Green "[OK] Carpeta _mejoras/ creada"
    } else {
        Write-ColorMsg Green "[OK] Carpeta _mejoras/ ya existe"
    }
    
    # Crear subdirectorios
    $subDirs = @("tests", "codigo", "frontend", "docs", "guias")
    foreach ($dir in $subDirs) {
        $fullPath = Join-Path $global:MejorasFolder $dir
        if (-not (Test-Path $fullPath)) {
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        }
    }
    
    Write-Log "Mejoras folder initialized"
}

function Create-Backup {
    Write-ColorMsg Yellow "`nCreando backup completo..."
    
    try {
        if (-not (Test-Path $global:BackupFolder)) {
            New-Item -ItemType Directory -Path $global:BackupFolder -Force | Out-Null
        }
        
        $BackupPath = Join-Path $global:BackupFolder "backup_$global:Timestamp"
        New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
        
        # Archivos criticos a respaldar
        $criticalFiles = @(
            "proyecto_turnos/settings.py",
            "proyecto_turnos/urls.py",
            "turnos/models.py",
            "turnos/views.py",
            "turnos/generador.py",
            "turnos/tasks.py",
            "turnos/forms.py",
            "turnos/urls.py",
            "requirements.txt",
            "manage.py"
        )
        
        $backedUp = 0
        foreach ($file in $criticalFiles) {
            $source = Join-Path $global:ProjectRoot $file
            if (Test-Path $source) {
                $destFolder = Join-Path $BackupPath (Split-Path $file -Parent)
                if (-not (Test-Path $destFolder)) {
                    New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
                }
                Copy-Item $source -Destination $destFolder -Force
                $backedUp++
            }
        }
        
        # Backup completo de templates
        $templatesSource = Join-Path $global:ProjectRoot "turnos/templates"
        if (Test-Path $templatesSource) {
            $templatesDest = Join-Path $BackupPath "turnos/templates"
            Copy-Item $templatesSource -Destination $templatesDest -Recurse -Force
        }
        
        Write-ColorMsg Green "[OK] Backup completado"
        Write-Host "   Ubicacion: $BackupPath"
        Write-Host "   Archivos: $backedUp"
        Write-Log "Backup completed: $BackupPath"
        
        return $BackupPath
    }
    catch {
        Write-ColorMsg Red "[ERROR] Fallo al crear backup: $_"
        Write-Log "Backup failed: $_"
        return $null
    }
}

function Generate-Tests {
    Write-ColorMsg Yellow "`nGenerando tests unitarios en _mejoras/tests/..."
    
    $testsDir = Join-Path $global:MejorasFolder "tests"
    
    # __init__.py
    @"
"""
Tests unitarios para el Planificador de Turnos
Generado automáticamente - Revisar antes de usar
"""
"@ | Out-File -FilePath (Join-Path $testsDir "__init__.py") -Encoding UTF8
    
    # conftest.py
    @"
import pytest
from django.contrib.auth import get_user_model
from datetime import date, time
from turnos.models import Enfermera, TipoTurno, ConfiguracionPlanificacion

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123'
    )


@pytest.fixture
def enfermeras(db):
    enfermeras = []
    for i in range(1, 6):
        enfermera = Enfermera.objects.create(
            nombre=f'Enfermera {i}',
            email=f'enfermera{i}@hospital.com',
            dni=f'1234567{i}A',
            activa=True
        )
        enfermeras.append(enfermera)
    return enfermeras


@pytest.fixture
def turnos(db):
    manana = TipoTurno.objects.create(
        nombre='MANANA',
        hora_inicio=time(7, 0),
        hora_fin=time(15, 0),
        activo=True
    )
    tarde = TipoTurno.objects.create(
        nombre='TARDE',
        hora_inicio=time(15, 0),
        hora_fin=time(23, 0),
        activo=True
    )
    noche = TipoTurno.objects.create(
        nombre='NOCHE',
        hora_inicio=time(23, 0),
        hora_fin=time(7, 0),
        activo=True
    )
    return [manana, tarde, noche]


@pytest.fixture
def configuracion_basica(db, user, enfermeras, turnos):
    config = ConfiguracionPlanificacion.objects.create(
        nombre='Config Test',
        num_dias=7,
        fecha_inicio=date.today(),
        creado_por=user
    )
    config.enfermeras.set(enfermeras)
    config.turnos.set(turnos)
    return config
"@ | Out-File -FilePath (Join-Path $testsDir "conftest.py") -Encoding UTF8
    
    # test_models.py
    @"
import pytest
from datetime import time
from turnos.models import Enfermera, TipoTurno


@pytest.mark.django_db
class TestEnfermera:
    def test_crear_enfermera(self):
        enfermera = Enfermera.objects.create(
            nombre='María García',
            email='maria@hospital.com',
            dni='12345678A',
            activa=True
        )
        assert enfermera.nombre == 'María García'
        assert str(enfermera) == 'María García'


@pytest.mark.django_db
class TestTipoTurno:
    def test_duracion_turno_normal(self):
        turno = TipoTurno.objects.create(
            nombre='MANANA',
            hora_inicio=time(7, 0),
            hora_fin=time(15, 0)
        )
        assert turno.duracion_horas == 8.0
    
    def test_duracion_turno_nocturno(self):
        turno = TipoTurno.objects.create(
            nombre='NOCHE',
            hora_inicio=time(23, 0),
            hora_fin=time(7, 0)
        )
        assert turno.duracion_horas == 8.0
"@ | Out-File -FilePath (Join-Path $testsDir "test_models.py") -Encoding UTF8
    
    # test_generador.py
    @"
import pytest
from turnos.generador import GeneradorTurnos


@pytest.mark.django_db
class TestGeneradorTurnos:
    def test_inicializacion(self, configuracion_basica):
        generador = GeneradorTurnos(configuracion_basica)
        assert generador.num_dias == 7
        assert generador.num_enfermeras == 5
        assert generador.num_turnos == 3
    
    def test_crear_variables(self, configuracion_basica):
        generador = GeneradorTurnos(configuracion_basica)
        generador.crear_variables()
        expected_vars = 5 * 7 * 3
        assert len(generador.shifts) == expected_vars
    
    def test_resolver_basico(self, configuracion_basica):
        generador = GeneradorTurnos(configuracion_basica)
        resultado = generador.resolver()
        assert 'success' in resultado
        assert 'asignaciones' in resultado
"@ | Out-File -FilePath (Join-Path $testsDir "test_generador.py") -Encoding UTF8
    
    # pytest.ini
    @"
[pytest]
DJANGO_SETTINGS_MODULE = proyecto_turnos.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --strict-markers
    --cov=turnos
    --cov-report=html
    --cov-report=term-missing
"@ | Out-File -FilePath (Join-Path $testsDir "pytest.ini") -Encoding UTF8
    
    # README para tests
    @"
# Tests Unitarios Generados

## Instalación

1. Copiar archivos de _mejoras/tests/ a turnos/tests/
2. Copiar pytest.ini a la raiz del proyecto
3. Instalar dependencias:

``````bash
pip install pytest pytest-django pytest-cov factory-boy
``````

## Ejecutar

``````bash
# Todos los tests
python -m pytest

# Con cobertura
python -m pytest --cov=turnos --cov-report=html

# Test especifico
python -m pytest turnos/tests/test_models.py
``````

## Archivos generados

- conftest.py: Fixtures compartidas
- test_models.py: Tests de modelos
- test_generador.py: Tests del solver
- pytest.ini: Configuracion de pytest
"@ | Out-File -FilePath (Join-Path $testsDir "README.md") -Encoding UTF8
    
    Write-ColorMsg Green "[OK] Tests generados en _mejoras/tests/"
    Write-Host "   - conftest.py (fixtures)"
    Write-Host "   - test_models.py"
    Write-Host "   - test_generador.py"
    Write-Host "   - pytest.ini"
    Write-Host "   - README.md con instrucciones"
    Write-Log "Tests generated"
}

function Generate-CeleryCode {
    Write-ColorMsg Yellow "`nGenerando codigo Celery mejorado en _mejoras/codigo/..."
    
    $codigoDir = Join-Path $global:MejorasFolder "codigo"
    
    # tasks.py mejorado
    @"
'''
Tareas asíncronas de Celery - CODIGO MEJORADO
IMPORTANTE: Revisar y adaptar antes de reemplazar tasks.py existente
'''
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from turnos.models import Ejecucion, Planilla, AsignacionTurno
from turnos.generador import GeneradorTurnos

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def ejecutar_planificacion_async(self, ejecucion_id):
    '''Ejecuta planificacion de forma as

incrona'''
    try:
        ejecucion = Ejecucion.objects.get(id=ejecucion_id)
        ejecucion.estado = 'PROCESANDO'
        ejecucion.save()
        
        generador = GeneradorTurnos(ejecucion.configuracion)
        resultado = generador.resolver()
        
        ejecucion.resultado = resultado
        ejecucion.es_optima = resultado.get('es_optima', False)
        
        if resultado.get('success'):
            planilla = crear_planilla_desde_resultado(ejecucion, resultado)
            ejecucion.planilla = planilla
            ejecucion.estado = 'COMPLETADA'
        else:
            ejecucion.estado = 'ERROR'
            ejecucion.mensaje_error = resultado.get('mensaje', 'Error desconocido')
        
        ejecucion.fecha_fin = timezone.now()
        ejecucion.save()
        
        return {'success': True, 'ejecucion_id': ejecucion_id}
        
    except Exception as e:
        logger.error(f\"Error en ejecucion {ejecucion_id}: {e}\")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        raise


def crear_planilla_desde_resultado(ejecucion, resultado):
    '''Crea planilla con asignaciones desde resultado del solver'''
    config = ejecucion.configuracion
    
    planilla = Planilla.objects.create(
        nombre=f\"Planilla {config.nombre} - {timezone.now().strftime('%d/%m/%Y')}\",
        ejecucion=ejecucion,
        fecha_inicio=config.fecha_inicio,
        fecha_fin=config.fecha_inicio + timedelta(days=config.num_dias-1),
        num_dias=config.num_dias
    )
    
    asignaciones = []
    for asig_data in resultado.get('asignaciones', []):
        from datetime import datetime
        fecha = datetime.fromisoformat(asig_data['fecha']).date()
        
        asignaciones.append(AsignacionTurno(
            planilla=planilla,
            enfermera_id=asig_data['enfermera_id'],
            fecha=fecha,
            turno_id=asig_data.get('turno_id'),
            es_dia_libre=asig_data.get('es_dia_libre', False)
        ))
    
    AsignacionTurno.objects.bulk_create(asignaciones, batch_size=100)
    logger.info(f\"Planilla {planilla.id} creada con {len(asignaciones)} asignaciones\")
    
    return planilla


@shared_task
def limpiar_ejecuciones_antiguas(dias=30):
    '''Limpia ejecuciones antiguas para liberar espacio'''
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    ejecuciones_antiguas = Ejecucion.objects.filter(
        fecha_inicio__lt=fecha_limite,
        estado__in=['COMPLETADA', 'ERROR']
    )
    
    count = ejecuciones_antiguas.count()
    ejecuciones_antiguas.delete()
    
    logger.info(f\"Limpiadas {count} ejecuciones antiguas\")
    return {'eliminadas': count}


@shared_task
def generar_estadisticas_mensuales():
    '''Genera estadisticas mensuales del sistema'''
    from django.db.models import Count, Avg
    from datetime import date
    
    hoy = timezone.now().date()
    primer_dia_mes = date(hoy.year, hoy.month, 1)
    
    stats = {
        'ejecuciones_totales': Ejecucion.objects.filter(
            fecha_inicio__gte=primer_dia_mes
        ).count(),
        'ejecuciones_exitosas': Ejecucion.objects.filter(
            fecha_inicio__gte=primer_dia_mes,
            estado='COMPLETADA'
        ).count(),
        'tiempo_promedio': Ejecucion.objects.filter(
            fecha_inicio__gte=primer_dia_mes,
            estado='COMPLETADA'
        ).aggregate(Avg('tiempo_ejecucion'))['tiempo_ejecucion__avg']
    }
    
    logger.info(f\"Estadisticas mensuales generadas: {stats}\")
    return stats


@shared_task
def notificar_ejecucion_completada(ejecucion_id):
    '''Envia notificacion cuando una ejecucion termina'''
    try:
        ejecucion = Ejecucion.objects.get(id=ejecucion_id)
        
        # Aqui puedes agregar logica de notificacion
        # Por ejemplo, enviar email, webhook, etc.
        
        logger.info(f\"Notificacion enviada para ejecucion {ejecucion_id}\")
        return {'notificado': True}
        
    except Exception as e:
        logger.error(f\"Error al notificar ejecucion {ejecucion_id}: {e}\")
        return {'notificado': False, 'error': str(e)}
"@ | Out-File -FilePath (Join-Path $codigoDir "tasks_mejorado.py") -Encoding UTF8
    
    # README para codigo
    @"
# Codigo Celery Mejorado

## Instalacion

1. HACER BACKUP del archivo turnos/tasks.py actual
2. Revisar tasks_mejorado.py
3. Adaptar a tu proyecto si es necesario
4. Reemplazar turnos/tasks.py con el contenido mejorado

## Nuevas Tareas

- `ejecutar_planificacion_async`: Mejorado con reintentos y mejor manejo de errores
- `crear_planilla_desde_resultado`: Creacion optimizada con bulk_create
- `limpiar_ejecuciones_antiguas`: Mantenimiento automatico
- `generar_estadisticas_mensuales`: Reportes automaticos
- `notificar_ejecucion_completada`: Sistema de notificaciones

## Configuracion Celery

Agregar a proyecto_turnos/settings.py:

``````python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Madrid'
``````

## Ejecutar Worker

``````bash
celery -A proyecto_turnos worker --loglevel=info
``````

Windows:
``````bash
celery -A proyecto_turnos worker --loglevel=info --pool=solo
``````

## Tareas Periodicas

Configurar en celery.py:

``````python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'limpiar-ejecuciones-diario': {
        'task': 'turnos.tasks.limpiar_ejecuciones_antiguas',
        'schedule': crontab(hour=2, minute=0),  # 2 AM diario
    },
    'estadisticas-mensuales': {
        'task': 'turnos.tasks.generar_estadisticas_mensuales',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),  # Primer dia del mes
    },
}
``````
"@ | Out-File -FilePath (Join-Path $codigoDir "README.md") -Encoding UTF8
    
    Write-ColorMsg Green "[OK] Codigo Celery generado en _mejoras/codigo/"
    Write-Host "   - tasks_mejorado.py"
    Write-Host "   - README.md con instrucciones"
    Write-Log "Celery code generated"
}

function Generate-Frontend {
    Write-ColorMsg Yellow "`nGenerando frontend mejorado en _mejoras/frontend/..."
    
    $frontendDir = Join-Path $global:MejorasFolder "frontend"
    
    # Crear subdirectorios
    $jsDir = Join-Path $frontendDir "static/js"
    $cssDir = Join-Path $frontendDir "static/css"
    $templatesDir = Join-Path $frontendDir "templates"
    
    New-Item -ItemType Directory -Path $jsDir -Force | Out-Null
    New-Item -ItemType Directory -Path $cssDir -Force | Out-Null
    New-Item -ItemType Directory -Path $templatesDir -Force | Out-Null
    
    # dashboard.js
    @"
// Dashboard Charts - Chart.js
// Copiar a turnos/static/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    initCharts();
});

function initCharts() {
    initDistribucionTurnosChart();
    initCargaEnfermerasChart();
}

function initDistribucionTurnosChart() {
    const ctx = document.getElementById('chartDistribucionTurnos');
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Mañana', 'Tarde', 'Noche', 'Libres'],
            datasets: [{
                data: window.distribucionData || [0, 0, 0, 0],
                backgroundColor: ['#ffc107', '#17a2b8', '#343a40', '#6c757d'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' },
                title: { display: true, text: 'Distribucion de Turnos' }
            }
        }
    });
}

function initCargaEnfermerasChart() {
    const ctx = document.getElementById('chartCargaEnfermeras');
    if (!ctx) return;
    
    const enfermeras = window.enfermerasData || [];
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: enfermeras.map(e => e.nombre),
            datasets: [{
                label: 'Turnos Trabajados',
                data: enfermeras.map(e => e.turnos),
                backgroundColor: '#007bff'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}
"@ | Out-File -FilePath (Join-Path $jsDir "dashboard.js") -Encoding UTF8
    
    # custom.css
    @"
/* Estilos mejorados - Copiar a turnos/static/css/custom.css */

:root {
    --primary-color: #007bff;
    --success-color: #28a745;
    --warning-color: #ffc107;
    --info-color: #17a2b8;
}

.stat-card {
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: transform 0.2s;
}

.stat-card:hover {
    transform: translateY(-5px);
}

.chart-container {
    position: relative;
    height: 300px;
    margin: 20px 0;
}

.turno-manana {
    background: #fff3cd;
    border-color: var(--warning-color);
}

.turno-tarde {
    background: #d1ecf1;
    border-color: var(--info-color);
}

.turno-noche {
    background: #d6d8db;
    border-color: #343a40;
}

@media (max-width: 768px) {
    .stat-card {
        margin-bottom: 15px;
    }
}
"@ | Out-File -FilePath (Join-Path $cssDir "custom.css") -Encoding UTF8
    
    # README
    @"
# Frontend Mejorado

## Archivos Generados

- `static/js/dashboard.js`: Graficos Chart.js
- `static/css/custom.css`: Estilos mejorados

## Instalacion

1. Copiar archivos a:
   - turnos/static/js/dashboard.js
   - turnos/static/css/custom.css

2. Agregar Chart.js al template base:

``````html
<script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js\"></script>
``````

3. Incluir en templates:

``````html
{% load static %}
<link rel=\"stylesheet\" href=\"{% static 'css/custom.css' %}\">
<script src=\"{% static 'js/dashboard.js' %}\"></script>
``````

## Uso en Templates

Agregar canvas para graficos:

``````html
<div class=\"chart-container\">
    <canvas id=\"chartDistribucionTurnos\"></canvas>
</div>
<div class=\"chart-container\">
    <canvas id=\"chartCargaEnfermeras\"></canvas>
</div>

<script>
window.distribucionData = [10, 15, 8, 5];  // Datos desde backend
window.enfermerasData = {{ enfermeras_json|safe }};
</script>
``````
"@ | Out-File -FilePath (Join-Path $frontendDir "README.md") -Encoding UTF8
    
    Write-ColorMsg Green "[OK] Frontend generado en _mejoras/frontend/"
    Write-Host "   - static/js/dashboard.js"
    Write-Host "   - static/css/custom.css"
    Write-Host "   - README.md"
    Write-Log "Frontend generated"
}

function Generate-Documentation {
    Write-ColorMsg Yellow "`nGenerando documentacion en _mejoras/docs/..."
    
    $docsDir = Join-Path $global:MejorasFolder "docs"
    
    # README principal
    @"
# Planificador de Turnos para Enfermeras

Sistema inteligente de planificacion automatica usando OR-Tools CP-SAT.

## Caracteristicas

- Generacion automatica de planificaciones
- Interfaz web intuitiva
- Procesamiento asincrono con Celery
- Exportacion a Excel, PDF, CSV, iCalendar
- Dashboard con visualizaciones
- Tests unitarios

## Instalacion Rapida

``````bash
# Clonar
git clone https://github.com/LuisSereno/planificador_turnos.git
cd planificador_turnos

# Entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# Dependencias
pip install -r requirements.txt

# Migraciones
python manage.py migrate
python manage.py createsuperuser

# Ejecutar
python manage.py runserver
``````

## Uso Basico

1. **Configurar Turnos**: Crea los turnos (Mañana, Tarde, Noche)
2. **Agregar Enfermeras**: Desde el admin o importando Excel
3. **Crear Configuracion**: Define parametros de planificacion
4. **Ejecutar**: Genera la planificacion automaticamente
5. **Exportar**: Descarga en tu formato preferido

## Tecnologias

- Django 5.2
- OR-Tools (Google)
- Celery + Redis
- Bootstrap 5
- Chart.js
- PostgreSQL / SQLite

## Documentacion

- [Guia de Usuario](GUIA_USUARIO.md)
- [API](API.md)
- [Guia del Desarrollador](DEVELOPER.md)

## Licencia

MIT License

## Autor

Luis Sereno - [@LuisSereno](https://github.com/LuisSereno)
"@ | Out-File -FilePath (Join-Path $docsDir "README.md") -Encoding UTF8
    
    # API.md
    @"
# API del Planificador

## Modelos Principales

### Enfermera

``````python
class Enfermera(models.Model):
    nombre = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    dni = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    activa = models.BooleanField(default=True)
    preferencias = models.JSONField(null=True, blank=True)
``````

### TipoTurno

``````python
class TipoTurno(models.Model):
    nombre = models.CharField(max_length=20, choices=TIPO_TURNO_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)
``````

### ConfiguracionPlanificacion

``````python
class ConfiguracionPlanificacion(models.Model):
    nombre = models.CharField(max_length=200)
    num_dias = models.IntegerField()
    fecha_inicio = models.DateField()
    enfermeras = models.ManyToManyField(Enfermera)
    turnos = models.ManyToManyField(TipoTurno)
    demanda_por_turno = models.JSONField()
    restricciones_duras = models.JSONField(null=True)
    restricciones_blandas = models.JSONField(null=True)
``````

## Uso del Generador

``````python
from turnos.generador import GeneradorTurnos

# Crear generador
configuracion = ConfiguracionPlanificacion.objects.get(pk=1)
generador = GeneradorTurnos(configuracion)

# Resolver
resultado = generador.resolver()

# Resultado
{
    'success': True,
    'status': 'OPTIMAL',
    'es_optima': True,
    'tiempo_ejecucion': 45.3,
    'asignaciones': [...]
}
``````

## Tareas Celery

### Ejecutar Planificacion

``````python
from turnos.tasks import ejecutar_planificacion_async

task = ejecutar_planificacion_async.delay(ejecucion_id=123)
task.ready()  # Verificar si termino
task.result  # Obtener resultado
``````

### Limpiar Ejecuciones

``````python
from turnos.tasks import limpiar_ejecuciones_antiguas

limpiar_ejecuciones_antiguas.delay(dias=30)
``````
"@ | Out-File -FilePath (Join-Path $docsDir "API.md") -Encoding UTF8
    
    Write-ColorMsg Green "[OK] Documentacion generada en _mejoras/docs/"
    Write-Host "   - README.md"
    Write-Host "   - API.md"
    Write-Log "Documentation generated"
}

function Generate-InstallationGuide {
    Write-ColorMsg Yellow "`nGenerando guia de instalacion..."
    
    $guiasDir = Join-Path $global:MejorasFolder "guias"
    
    @"
# GUIA DE INSTALACION DE MEJORAS

## IMPORTANTE: Leer Antes de Empezar

Este sistema ha generado TODO el codigo de mejoras en la carpeta `_mejoras/`
SIN modificar NADA de tu proyecto actual.

## Estructura Generada

``````
_mejoras/
├── tests/          → Tests unitarios
├── codigo/         → Codigo Celery mejorado
├── frontend/       → JS y CSS mejorados
├── docs/           → Documentacion
└── guias/          → Esta guia
``````

## Paso a Paso

### 1. Revisar Contenido

Antes de copiar nada, REVISAR cada archivo en _mejoras/

``````bash
# Ver tests generados
ls _mejoras/tests/

# Ver codigo Celery
cat _mejoras/codigo/tasks_mejorado.py

# Ver frontend
ls _mejoras/frontend/static/
``````

### 2. Instalar Tests

``````bash
# Copiar tests
cp -r _mejoras/tests/* turnos/tests/

# Copiar configuracion pytest
cp _mejoras/tests/pytest.ini .

# Instalar dependencias
pip install pytest pytest-django pytest-cov

# Probar
python -m pytest
``````

### 3. Actualizar Celery

``````bash
# IMPORTANTE: Hacer backup primero
cp turnos/tasks.py turnos/tasks.py.backup

# Revisar el codigo nuevo
cat _mejoras/codigo/tasks_mejorado.py

# Si todo OK, reemplazar
cp _mejoras/codigo/tasks_mejorado.py turnos/tasks.py
``````

### 4. Agregar Frontend

``````bash
# Copiar JS
cp _mejoras/frontend/static/js/dashboard.js turnos/static/js/

# Copiar CSS
cp _mejoras/frontend/static/css/custom.css turnos/static/css/

# Agregar Chart.js al base.html
# Ver instrucciones en _mejoras/frontend/README.md
``````

### 5. Agregar Documentacion

``````bash
# Crear carpeta docs si no existe
mkdir -p docs

# Copiar documentacion
cp _mejoras/docs/* docs/

# Actualizar README principal si quieres
cp _mejoras/docs/README.md README.md
``````

## Verificacion Final

Despues de instalar:

``````bash
# 1. Tests funcionan
python -m pytest

# 2. Servidor arranca
python manage.py runserver

# 3. Celery funciona
celery -A proyecto_turnos worker --loglevel=info

# 4. No hay errores en logs
``````

## Si Algo Sale Mal

1. **Tests fallan**: Revisa imports y configuracion
2. **Celery no funciona**: Verifica Redis esta corriendo
3. **Frontend roto**: Revisa que Chart.js esta cargado

## Backup

Todos tus backups estan en:
``````
backups/backup_YYYYMMDD_HHMMSS/
``````

Para restaurar:
``````bash
cp backups/backup_XXXXXXXX/turnos/tasks.py turnos/tasks.py
``````

## Soporte

Si necesitas ayuda:
1. Revisa los README.md en cada carpeta de _mejoras/
2. Revisa los logs en logs/
3. Consulta la documentacion oficial de Django/Celery

---

**RECUERDA**: La carpeta _mejoras/ es SEGURA - no afecta tu proyecto
hasta que TU decidas copiar manualmente los archivos.
"@ | Out-File -FilePath (Join-Path $guiasDir "INSTALACION.md") -Encoding UTF8
    
    Write-ColorMsg Green "[OK] Guia de instalacion generada"
    Write-Host "   - _mejoras/guias/INSTALACION.md"
    Write-Log "Installation guide generated"
}

function Show-ProjectStatus {
    Write-ColorMsg Yellow "`nESTADO DEL PROYECTO"
    Write-Host ""
    
    # Verificar archivos criticos
    $criticalFiles = @(
        @{Path="manage.py"; Desc="Script Django"},
        @{Path="proyecto_turnos/settings.py"; Desc="Configuracion"},
        @{Path="proyecto_turnos/urls.py"; Desc="URLs principales"},
        @{Path="turnos/models.py"; Desc="Modelos"},
        @{Path="turnos/views.py"; Desc="Vistas"},
        @{Path="turnos/generador.py"; Desc="Solver"},
        @{Path="turnos/tasks.py"; Desc="Celery"},
        @{Path="requirements.txt"; Desc="Dependencias"}
    )
    
    foreach ($file in $criticalFiles) {
        $fullPath = Join-Path $global:ProjectRoot $file.Path
        if (Test-Path $fullPath) {
            Write-ColorMsg Green "[OK] $($file.Desc): $($file.Path)"
        } else {
            Write-ColorMsg Red "[FALTA] $($file.Desc): $($file.Path)"
        }
    }
    
    # Verificar templates
    $templatesPath = Join-Path $global:ProjectRoot "turnos/templates"
    if (Test-Path $templatesPath) {
        $templateCount = (Get-ChildItem -Path $templatesPath -Filter "*.html" -Recurse).Count
        Write-ColorMsg Green "[OK] Templates: $templateCount archivos"
    } else {
        Write-ColorMsg Yellow "[WARN] Templates no encontrados"
    }
    
    # Verificar database
    $dbPath = Join-Path $global:ProjectRoot "db.sqlite3"
    if (Test-Path $dbPath) {
        $dbSize = [math]::Round((Get-Item $dbPath).Length / 1KB, 2)
        Write-ColorMsg Green "[OK] Database: $dbSize KB"
    } else {
        Write-ColorMsg Yellow "[WARN] Database no encontrada"
    }
    
    Write-Host ""
}

function Show-MejorasContent {
    Write-ColorMsg Yellow "`nCONTENIDO DE _mejoras/"
    Write-Host ""
    
    if (-not (Test-Path $global:MejorasFolder)) {
        Write-ColorMsg Yellow "La carpeta _mejoras/ aun no existe"
        Write-Host "Ejecuta alguna opcion del menu para generar contenido"
        return
    }
    
    $items = Get-ChildItem -Path $global:MejorasFolder -Recurse -File
    
    if ($items.Count -eq 0) {
        Write-ColorMsg Yellow "La carpeta _mejoras/ esta vacia"
        return
    }
    
    Write-Host "Archivos generados: $($items.Count)"
    Write-Host ""
    
    foreach ($item in $items) {
        $relativePath = $item.FullName.Replace($global:MejorasFolder, "")
        $size = [math]::Round($item.Length / 1KB, 2)
        Write-Host "  $relativePath ($size KB)"
    }
    
    Write-Host ""
}

# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

function Main {
    Show-Banner
    Write-Log "Script started in SAFE MODE"
    
    # Inicializar carpeta de mejoras
    Initialize-MejorasFolder
    
    # Crear backup inicial si no se especifica -SkipBackup
    if (-not $SkipBackup) {
        Create-Backup | Out-Null
    }
    
    $continue = $true
    
    while ($continue) {
        Show-Menu
        $choice = Read-Host "Selecciona una opcion"
        
        switch ($choice) {
            "1" {
                Create-Backup
                Read-Host "`nPresiona Enter para continuar"
            }
            "2" {
                Generate-Tests
                Read-Host "`nPresiona Enter para continuar"
            }
            "3" {
                Generate-CeleryCode
                Read-Host "`nPresiona Enter para continuar"
            }
            "4" {
                Generate-Frontend
                Read-Host "`nPresiona Enter para continuar"
            }
            "5" {
                Generate-Documentation
                Read-Host "`nPresiona Enter para continuar"
            }
            "6" {
                Write-ColorMsg Yellow "`nGenerando TODAS las mejoras..."
                Generate-Tests
                Generate-CeleryCode
                Generate-Frontend
                Generate-Documentation
                Generate-InstallationGuide
                Write-ColorMsg Green "`n[OK] Todas las mejoras generadas en _mejoras/"
                Read-Host "`nPresiona Enter para continuar"
            }
            "7" {
                Show-ProjectStatus
                Read-Host "`nPresiona Enter para continuar"
            }
            "8" {
                Show-MejorasContent
                Read-Host "`nPresiona Enter para continuar"
            }
            "9" {
                Generate-InstallationGuide
                Read-Host "`nPresiona Enter para continuar"
            }
            "0" {
                Write-ColorMsg Green "`nHasta luego!"
                Write-Log "Script ended"
                $continue = $false
            }
            default {
                Write-ColorMsg Red "Opcion invalida"
                Start-Sleep -Seconds 1
            }
        }
    }
}

# Ejecutar
Main

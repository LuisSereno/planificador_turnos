# DIAGNOSTICAR-Y-ARREGLAR-CELERY-DB.ps1
# Diagnostica y soluciona problemas de base de datos entre Django y Celery

$ErrorActionPreference = 'Stop'

Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " DIAGNÓSTICO CELERY + DJANGO DB" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar que estamos en el directorio correcto
if (-not (Test-Path "manage.py")) {
    Write-Host "[ERROR] No se encuentra manage.py. Ejecuta desde la raíz del proyecto." -ForegroundColor Red
    exit 1
}

# 2. Verificar configuración de Celery
Write-Host "[1] Verificando configuración de Celery..." -ForegroundColor Yellow
$celeryPath = "proyecto_turnos\celery.py"

if (Test-Path $celeryPath) {
    $celeryContent = Get-Content $celeryPath -Raw

    if ($celeryContent -match "DJANGO_SETTINGS_MODULE") {
        Write-Host "  ✓ DJANGO_SETTINGS_MODULE configurado" -ForegroundColor Green
    } else {
        Write-Host "  ✗ FALTA configuración de DJANGO_SETTINGS_MODULE" -ForegroundColor Red
    }

    if ($celeryContent -match "autodiscover_tasks") {
        Write-Host "  ✓ autodiscover_tasks presente" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Falta autodiscover_tasks" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ No existe $celeryPath" -ForegroundColor Red
}

# 3. Crear archivo de diagnóstico en tasks.py
Write-Host "`n[2] Creando tarea de diagnóstico..." -ForegroundColor Yellow

$diagnosticTask = @'

@shared_task
def diagnostico_db():
    """Tarea de diagnóstico para verificar acceso a DB"""
    from django.conf import settings
    from turnos.models import ConfiguracionPlanificacion
    import logging

    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("DIAGNÓSTICO DE BASE DE DATOS")
    logger.info("=" * 80)
    logger.info(f"Django Settings Module: {settings.SETTINGS_MODULE}")
    logger.info(f"Database Engine: {settings.DATABASES['default']['ENGINE']}")
    logger.info(f"Database Name: {settings.DATABASES['default']['NAME']}")

    try:
        total_configs = ConfiguracionPlanificacion.objects.count()
        logger.info(f"✓ Total ConfiguracionPlanificacion: {total_configs}")

        if total_configs > 0:
            ids = list(ConfiguracionPlanificacion.objects.values_list('id', 'nombre'))
            logger.info(f"✓ IDs disponibles:")
            for id, nombre in ids:
                logger.info(f"  - ID {id}: {nombre}")
        else:
            logger.warning("⚠ No hay configuraciones en la base de datos")

        return {
            'success': True,
            'total': total_configs,
            'ids': [id for id, _ in ids] if total_configs > 0 else []
        }
    except Exception as e:
        logger.error(f"✗ Error al acceder a DB: {e}")
        return {
            'success': False,
            'error': str(e)
        }
'@

Write-Host "  Agrega esta tarea al final de turnos/tasks.py:" -ForegroundColor Gray
Write-Host $diagnosticTask -ForegroundColor DarkGray

# 4. Crear celery.py correcto si no existe o está mal
Write-Host "`n[3] Verificando/Creando celery.py correcto..." -ForegroundColor Yellow

$correctCeleryPy = @'
# -*- coding: utf-8 -*-
"""
Configuración de Celery para proyecto_turnos
"""

import os
from celery import Celery

# ═══════════════════════════════════════════════════════════════
# IMPORTANTE: Usar el mismo settings que Django
# ═══════════════════════════════════════════════════════════════
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')

app = Celery('proyecto_turnos')

# Leer configuración desde Django settings con namespace CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en apps instaladas
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
'@

Write-Host "  Reemplazando $celeryPath..." -ForegroundColor Yellow
[IO.File]::WriteAllText($celeryPath, $correctCeleryPy, [Text.Encoding]::UTF8)
Write-Host "  ✓ celery.py actualizado" -ForegroundColor Green

# 5. Verificar __init__.py del proyecto
Write-Host "`n[4] Verificando __init__.py del proyecto..." -ForegroundColor Yellow
$initPath = "proyecto_turnos\__init__.py"

$correctInit = @'
# -*- coding: utf-8 -*-
"""
Inicialización de Celery para el proyecto
"""

# Esto asegura que Celery siempre se importe cuando Django arranca
from .celery import app as celery_app

__all__ = ('celery_app',)
'@

if (Test-Path $initPath) {
    $initContent = Get-Content $initPath -Raw
    if ($initContent -notmatch "celery_app") {
        Write-Host "  ⚠ Falta import de celery_app" -ForegroundColor Yellow
        [IO.File]::WriteAllText($initPath, $correctInit, [Text.Encoding]::UTF8)
        Write-Host "  ✓ __init__.py actualizado" -ForegroundColor Green
    } else {
        Write-Host "  ✓ __init__.py correcto" -ForegroundColor Green
    }
}

# 6. Verificar configuración en settings.py
Write-Host "`n[5] Verificando settings.py..." -ForegroundColor Yellow
$settingsPath = "proyecto_turnos\settings.py"

if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw

    if ($settings -notmatch "CELERY_BROKER_URL") {
        Write-Host "  ⚠ Falta configuración de Celery" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Agrega esto al final de settings.py:" -ForegroundColor Gray
        Write-Host @'

# ═══════════════════════════════════════════════════════════════
# CELERY CONFIGURATION
# ═══════════════════════════════════════════════════════════════
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Madrid'
CELERY_ENABLE_UTC = True
'@ -ForegroundColor DarkGray
    } else {
        Write-Host "  ✓ Configuración Celery presente" -ForegroundColor Green
    }
}

# 7. Instrucciones finales
Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host " PASOS SIGUIENTES" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

Write-Host "1. REINICIAR CELERY:" -ForegroundColor Cyan
Write-Host "   - Detén Celery (Ctrl+C)" -ForegroundColor White
Write-Host "   - Ejecuta: celery -A proyecto_turnos worker --loglevel=debug --pool=solo" -ForegroundColor Yellow
Write-Host ""

Write-Host "2. PROBAR DIAGNÓSTICO:" -ForegroundColor Cyan
Write-Host "   - Abre Django shell: python manage.py shell" -ForegroundColor Yellow
Write-Host "   - Ejecuta:" -ForegroundColor White
Write-Host "     from turnos.tasks import diagnostico_db" -ForegroundColor Gray
Write-Host "     result = diagnostico_db.delay()" -ForegroundColor Gray
Write-Host "     print(result.get())" -ForegroundColor Gray
Write-Host ""

Write-Host "3. SI EL DIAGNÓSTICO FALLA:" -ForegroundColor Cyan
Write-Host "   - Verifica que Django y Celery usan la misma BD" -ForegroundColor White
Write-Host "   - Ejecuta: python manage.py dbshell" -ForegroundColor Yellow
Write-Host "   - Y verifica: SELECT id, nombre FROM turnos_configuracionplanificacion;" -ForegroundColor Gray
Write-Host ""

Write-Host "4. VERIFICAR RUTA DE BD (si usas SQLite):" -ForegroundColor Cyan
Write-Host "   - Abre settings.py y busca DATABASES['default']['NAME']" -ForegroundColor White
Write-Host "   - Debe ser una ruta ABSOLUTA, no relativa" -ForegroundColor Yellow
Write-Host ""

Write-Host "EJEMPLO de configuración correcta para SQLite:" -ForegroundColor Cyan
Write-Host @'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': r'C:\Users\luiss\OneDrive\Documents\planificador_turnos\db.sqlite3',
    }
}
'@ -ForegroundColor Gray

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green

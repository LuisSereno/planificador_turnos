# VERIFICAR-DB-DIRECTAMENTE.ps1
# Verifica la base de datos sin necesidad de sqlite3 command line

Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " VERIFICACIÓN DIRECTA DE BASE DE DATOS" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar configuraciones en la BD usando Python
Write-Host "[1] Consultando base de datos..." -ForegroundColor Yellow

$pythonScript = @'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')
django.setup()

from django.conf import settings
from turnos.models import ConfiguracionPlanificacion

print("=" * 80)
print("INFORMACIÓN DE BASE DE DATOS")
print("=" * 80)
print(f"Database Engine: {settings.DATABASES['default']['ENGINE']}")
print(f"Database Path: {settings.DATABASES['default']['NAME']}")
print("")

# Verificar que el archivo existe
import os
db_path = settings.DATABASES['default']['NAME']
if os.path.exists(db_path):
    print(f"✓ Archivo de BD existe: {db_path}")
    print(f"  Tamaño: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
else:
    print(f"✗ Archivo de BD NO existe: {db_path}")
    print("  Ejecuta: python manage.py migrate")
    exit(1)

print("")
print("=" * 80)
print("CONFIGURACIONES EN LA BASE DE DATOS")
print("=" * 80)

try:
    total = ConfiguracionPlanificacion.objects.count()
    print(f"Total de configuraciones: {total}")
    print("")

    if total > 0:
        configs = ConfiguracionPlanificacion.objects.all()
        print("Lista de configuraciones:")
        print("-" * 80)
        for config in configs:
            print(f"  ID: {config.id:3d} | Nombre: {config.nombre:40s} | Activa: {config.activa}")
            print(f"       Enfermeras: {config.enfermeras.count():2d} | Turnos: {config.turnos.count():2d} | Días: {config.num_dias:3d}")
            print("-" * 80)
    else:
        print("⚠ No hay configuraciones en la base de datos")
        print("  Crea una configuración desde el admin de Django")

    print("")
    print("=" * 80)
    print("✓ VERIFICACIÓN COMPLETADA")
    print("=" * 80)

except Exception as e:
    print(f"✗ ERROR al consultar: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
'@

# Guardar script temporal
$tempScript = "temp_verify_db.py"
[IO.File]::WriteAllText($tempScript, $pythonScript, [Text.Encoding]::UTF8)

# Ejecutar
Write-Host "  Ejecutando consulta..." -ForegroundColor Gray
python $tempScript

# Limpiar
Remove-Item $tempScript -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host " RESULTADO" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

Write-Host "Si ves configuraciones arriba pero Celery no las encuentra:" -ForegroundColor Yellow
Write-Host ""
Write-Host "SOLUCIÓN:" -ForegroundColor Cyan
Write-Host "  1. Copia la ruta EXACTA de 'Database Path' de arriba" -ForegroundColor White
Write-Host "  2. Ábrela en settings.py -> DATABASES['default']['NAME']" -ForegroundColor White
Write-Host "  3. Asegúrate que sea RUTA ABSOLUTA (no relativa)" -ForegroundColor White
Write-Host "  4. Reinicia Celery completamente" -ForegroundColor White
Write-Host ""

Write-Host "Comando para reiniciar Celery:" -ForegroundColor Cyan
Write-Host "  celery -A proyecto_turnos worker --loglevel=info --pool=solo" -ForegroundColor Yellow
Write-Host ""

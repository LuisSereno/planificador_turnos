# AGREGAR-WORKSPACES-SEGURO.ps1
# Versión mejorada y robusta

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$BackupDir = Join-Path $ProjectRoot "backups\workspace_$Timestamp"

function Write-Info($m) { Write-Host $m -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn($m) { Write-Host "  [WARN] $m" -ForegroundColor Yellow }
function Write-Err($m)  { Write-Host "  [ERROR] $m" -ForegroundColor Red }

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  AGREGAR WORKSPACE - VERSION SEGURA" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""

# 1. Verificar que estamos en el directorio correcto
if (-not (Test-Path "manage.py")) {
    Write-Err "No se encontró manage.py. Ejecuta el script desde la raíz del proyecto Django."
    exit 1
}

$modelsFile = "turnos\models.py"

if (-not (Test-Path $modelsFile)) {
    Write-Err "No se encontró $modelsFile"
    exit 1
}

# 2. Backup
Write-Info "[1] Creando backup..."
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}
Copy-Item $modelsFile -Destination (Join-Path $BackupDir "models.py.backup") -Force
Write-Ok "Backup: $BackupDir\models.py.backup"

# 3. Leer archivo
Write-Info "`n[2] Leyendo models.py..."
$content = [IO.File]::ReadAllText($modelsFile, [System.Text.Encoding]::UTF8)

# 4. Verificar Workspace existe
if ($content -notmatch 'class Workspace\(models\.Model\)') {
    Write-Err "Modelo Workspace no existe. Agrégalo primero."
    exit 1
}
Write-Ok "Modelo Workspace encontrado"

# 5. Función para agregar workspace de forma segura
function Add-WorkspaceField {
    param(
        [string]$Content,
        [string]$ModelName
    )

    Write-Info "`n[3] Procesando modelo: $ModelName"

    # Buscar la definición de la clase
    $classPattern = "class\s+$ModelName\s*\(models\.Model\)\s*:"

    if ($Content -notmatch $classPattern) {
        Write-Warn "Modelo $ModelName no encontrado"
        return $Content
    }

    # Verificar si ya tiene workspace
    $modelBlockPattern = "(?s)class\s+$ModelName\s*\(models\.Model\)\s*:(.*?)(?=\nclass\s+\w+|\Z)"
    if ($Content -match $modelBlockPattern) {
        $modelBlock = $matches[1]
        if ($modelBlock -match 'workspace\s*=') {
            Write-Warn "$ModelName ya tiene campo workspace"
            return $Content
        }
    }

    # Encontrar dónde insertar (después de "class ModelName(models.Model):")
    $lines = $Content -split "`n"
    $newLines = @()
    $inserted = $false

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        $newLines += $line

        # Si encontramos la clase y no hemos insertado aún
        if (-not $inserted -and $line -match "class\s+$ModelName\s*\(models\.Model\)\s*:") {
            # Insertar el campo workspace en la siguiente línea con indentación correcta
            $wsField = "    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='${ModelName.ToLower()}s', null=True, blank=True)"
            $newLines += $wsField
            $inserted = $true
            Write-Ok "Campo workspace agregado a $ModelName"
        }
    }

    return ($newLines -join "`n")
}

# 6. Agregar workspace a cada modelo
$modelos = @('Enfermera', 'TipoTurno', 'ConfiguracionPlanificacion', 'Ejecucion', 'Planilla')

foreach ($modelo in $modelos) {
    $content = Add-WorkspaceField -Content $content -ModelName $modelo
}

# 7. Guardar archivo
Write-Info "`n[4] Guardando models.py..."
[IO.File]::WriteAllText($modelsFile, $content, [System.Text.Encoding]::UTF8)
Write-Ok "Archivo guardado"

if ($LASTEXITCODE -eq 0 -and $checkResult -match 'OK') {
    Write-Ok "Sintaxis correcta - Django puede importar models.py"
} else {
    Write-Err "Error al importar models.py"
    Write-Host $checkResult -ForegroundColor Red
    Write-Host ""
    Write-Warn "Restaurando backup..."
    Copy-Item (Join-Path $BackupDir "models.py.backup") -Destination $modelsFile -Force
    Write-Ok "Backup restaurado"
    Write-Host ""
    Write-Host "El error fue:" -ForegroundColor Yellow
    Write-Host $checkResult -ForegroundColor Red
    exit 1
}

# 9. Mostrar cambios
Write-Info "`n[6] Revisando cambios..."
Write-Host ""
foreach ($modelo in $modelos) {
    if ($content -match "class\s+$modelo.*?workspace\s*=") {
        Write-Ok "$modelo ahora tiene campo workspace"
    } else {
        Write-Warn "$modelo NO tiene campo workspace (revisar manualmente)"
    }
}

# 10. Preguntar por migraciones
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  SIGUIENTE PASO: MIGRACIONES" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$makeMigrations = Read-Host "¿Ejecutar 'python manage.py makemigrations' ahora? (s/n)"

if ($makeMigrations -eq 's') {
    Write-Info "`nEjecutando makemigrations..."
    python manage.py makemigrations

    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Migraciones creadas exitosamente"
        Write-Host ""

        $migrate = Read-Host "¿Ejecutar 'python manage.py migrate' ahora? (s/n)"

        if ($migrate -eq 's') {
            Write-Info "`nEjecutando migrate..."
            python manage.py migrate

            if ($LASTEXITCODE -eq 0) {
                Write-Ok "Migraciones aplicadas exitosamente"
            } else {
                Write-Err "Error al aplicar migraciones"
            }
        }
    } else {
        Write-Err "Error al crear migraciones"
    }
}

# 11. Instrucciones finales
Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  SIGUIENTE: CONFIGURACION INICIAL" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Copia y pega estos comandos en tu terminal:" -ForegroundColor Cyan
Write-Host ""
Write-Host "python manage.py shell" -ForegroundColor Yellow
Write-Host ""
Write-Host "Luego en el shell de Python:" -ForegroundColor Cyan
Write-Host @'
from turnos.models import Workspace
from django.contrib.auth.models import User

# Crear workspace principal
user = User.objects.first()
ws = Workspace.objects.create(
    nombre='Workspace Principal',
    creado_por=user,
    activo=True
)
ws.usuarios.add(user)

# Asignar workspace a registros existentes
from turnos.models import Enfermera, TipoTurno, ConfiguracionPlanificacion
Enfermera.objects.filter(workspace__isnull=True).update(workspace=ws)
TipoTurno.objects.filter(workspace__isnull=True).update(workspace=ws)
ConfiguracionPlanificacion.objects.filter(workspace__isnull=True).update(workspace=ws)

print(f"Workspace creado: {ws}")
print(f"Enfermeras actualizadas: {Enfermera.objects.filter(workspace=ws).count()}")
'@ -ForegroundColor Yellow
Write-Host ""

Write-Host "=========================================" -ForegroundColor Green
Write-Host "  COMPLETADO" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backup guardado en: $BackupDir" -ForegroundColor White
Write-Host ""

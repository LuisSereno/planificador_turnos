# FIX-ADMIN-WORKSPACE.ps1
Write-Host "Arreglando referencias a workspace en admin.py..." -ForegroundColor Yellow

$adminFile = "turnos\admin.py"
$content = Get-Content $adminFile -Raw -Encoding UTF8

# Comentar referencias a workspace temporalmente
$content = $content -replace "list_display = \['nombre', 'workspace',", "list_display = ['nombre', # 'workspace',"
$content = $content -replace "list_filter = \['workspace',", "list_filter = [# 'workspace',"

[IO.File]::WriteAllText($adminFile, $content, [System.Text.Encoding]::UTF8)

Write-Host "[OK] Referencias a workspace comentadas temporalmente" -ForegroundColor Green
Write-Host ""
Write-Host "Ahora ejecuta:" -ForegroundColor Cyan
Write-Host "  1. python manage.py makemigrations" -ForegroundColor Yellow
Write-Host "  2. python manage.py migrate" -ForegroundColor Yellow
Write-Host ""
Write-Host "Despues, descomenta las lineas en admin.py" -ForegroundColor Cyan

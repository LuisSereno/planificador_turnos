# FIX-IMPORT-URLS.ps1
# Corrige el import de ConfiguracionRestriccionesView en urls.py

$ErrorActionPreference = 'Stop'
$urlsPath = "turnos\urls.py"

if(-not (Test-Path $urlsPath)){
  Write-Host "[ERROR] No existe turnos\urls.py" -ForegroundColor Red
  exit 1
}

Write-Host "[INFO] Corrigiendo imports en urls.py..." -ForegroundColor Cyan

$content = [IO.File]::ReadAllText($urlsPath, [Text.Encoding]::UTF8)

# Verificar si ConfiguracionRestriccionesView está en las rutas
if($content -match 'ConfiguracionRestriccionesView'){
  Write-Host "  [DETECTADO] ConfiguracionRestriccionesView está en urls" -ForegroundColor Yellow

  # Verificar si está importado
  if($content -notmatch 'from\s+\.views\s+import.*ConfiguracionRestriccionesView'){
    Write-Host "  [CORRIGIENDO] Agregando import..." -ForegroundColor Yellow

    # Buscar la línea de import de views y agregar ConfiguracionRestriccionesView
    if($content -match 'from\s+\.views\s+import\s+(.+)'){
      $imports = $matches[1].Trim()

      # Si ya tiene paréntesis multilínea
      if($imports -match '^\('){
        $content = $content -replace '(from\s+\.views\s+import\s+\([^)]+)', '$1,`r`n    ConfiguracionRestriccionesView'
      }
      # Si es una línea simple
      else {
        $content = $content -replace '(from\s+\.views\s+import\s+)(.+)', '$1$2, ConfiguracionRestriccionesView'
      }

      Write-Host "  [OK] Import agregado" -ForegroundColor Green
    }
    # Si no hay import de views, agregarlo completo
    else {
      $importLine = "from .views import ConfiguracionRestriccionesView`r`n"
      $content = $importLine + $content
      Write-Host "  [OK] Import creado desde cero" -ForegroundColor Green
    }

    # Guardar
    [IO.File]::WriteAllText($urlsPath, $content, [Text.Encoding]::UTF8)
    Write-Host "  [OK] urls.py actualizado" -ForegroundColor Green
  }
  else {
    Write-Host "  [OK] Import ya existe" -ForegroundColor Green
  }
}
else {
  Write-Host "  [INFO] ConfiguracionRestriccionesView no está en urls (OK)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Ahora ejecuta: python manage.py runserver" -ForegroundColor Yellow

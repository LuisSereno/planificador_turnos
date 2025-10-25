# ══════════════════════════════════════════════════════════════
# GUIA COMPLETA DE INSTALACION MANUAL
# Copia paso a paso las mejoras de _mejoras/ a tu proyecto
# ══════════════════════════════════════════════════════════════

# IMPORTANTE: Ejecuta cada sección UNA POR UNA y verifica que funcione

Write-Host "================================================" -ForegroundColor Green
Write-Host "  GUIA DE INSTALACION MANUAL - PASO A PASO" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Sigue cada paso cuidadosamente" -ForegroundColor Yellow
Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 1: TESTS UNITARIOS
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "PASO 1: INSTALAR TESTS UNITARIOS" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 1.1 Crear directorio tests
Write-Host "[1.1] Crear directorio turnos/tests/" -ForegroundColor Yellow
if (-not (Test-Path "turnos/tests")) {
    New-Item -ItemType Directory -Path "turnos/tests" -Force
    Write-Host "  [OK] Directorio creado" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Ya existe" -ForegroundColor Yellow
}

# 1.2 Copiar archivos de tests
Write-Host "`n[1.2] Copiar archivos de tests" -ForegroundColor Yellow
if (Test-Path "_mejoras/tests") {
    Copy-Item "_mejoras/tests/__init__.py" -Destination "turnos/tests/" -Force
    Write-Host "  [OK] Copiado: __init__.py" -ForegroundColor Green
    
    Copy-Item "_mejoras/tests/conftest.py" -Destination "turnos/tests/" -Force
    Write-Host "  [OK] Copiado: conftest.py" -ForegroundColor Green
    
    Copy-Item "_mejoras/tests/test_models.py" -Destination "turnos/tests/" -Force
    Write-Host "  [OK] Copiado: test_models.py" -ForegroundColor Green
    
    Copy-Item "_mejoras/tests/test_generador.py" -Destination "turnos/tests/" -Force
    Write-Host "  [OK] Copiado: test_generador.py" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] No existe _mejoras/tests/" -ForegroundColor Red
}

# 1.3 Copiar pytest.ini
Write-Host "`n[1.3] Copiar pytest.ini a raiz" -ForegroundColor Yellow
if (Test-Path "_mejoras/tests/pytest.ini") {
    Copy-Item "_mejoras/tests/pytest.ini" -Destination "." -Force
    Write-Host "  [OK] pytest.ini copiado" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] No existe pytest.ini en _mejoras/tests/" -ForegroundColor Yellow
}

# 1.4 Instalar dependencias de tests
Write-Host "`n[1.4] Instalar dependencias" -ForegroundColor Yellow
Write-Host "  Ejecuta: pip install pytest pytest-django pytest-cov factory-boy" -ForegroundColor Yellow
Read-Host "`nPresiona Enter cuando hayas instalado las dependencias"

# 1.5 Verificar tests
Write-Host "`n[1.5] Verificar que funcionan los tests" -ForegroundColor Yellow
Write-Host "  Ejecuta: python -m pytest" -ForegroundColor Yellow
Write-Host "  Si hay errores, revisa los imports" -ForegroundColor Yellow
Read-Host "`nPresiona Enter para continuar al siguiente paso"

# ══════════════════════════════════════════════════════════════
# PASO 2: CODIGO CELERY
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "PASO 2: ACTUALIZAR CODIGO CELERY" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 2.1 Hacer backup del tasks.py actual
Write-Host "[2.1] Hacer backup de turnos/tasks.py" -ForegroundColor Yellow
if (Test-Path "turnos/tasks.py") {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item "turnos/tasks.py" -Destination "turnos/tasks.py.backup_$timestamp"
    Write-Host "  [OK] Backup creado: tasks.py.backup_$timestamp" -ForegroundColor Green
} else {
    Write-Host "  [WARN] No existe tasks.py actual" -ForegroundColor Yellow
}

# 2.2 Revisar el código nuevo
Write-Host "`n[2.2] REVISAR el codigo nuevo" -ForegroundColor Yellow
Write-Host "  Abre: _mejoras/codigo/tasks_mejorado.py" -ForegroundColor Yellow
Write-Host "  Y verifica que es compatible con tu proyecto" -ForegroundColor Yellow
$continuar = Read-Host "`n¿Has revisado el codigo y quieres continuar? (s/n)"

if ($continuar -eq 's') {
    # 2.3 Copiar nuevo tasks.py
    Write-Host "`n[2.3] Copiar tasks_mejorado.py" -ForegroundColor Yellow
    if (Test-Path "_mejoras/codigo/tasks_mejorado.py") {
        Copy-Item "_mejoras/codigo/tasks_mejorado.py" -Destination "turnos/tasks.py" -Force
        Write-Host "  [OK] tasks.py actualizado" -ForegroundColor Green
        Write-Host "  [INFO] Si algo falla, restaura: turnos/tasks.py.backup_$timestamp" -ForegroundColor Yellow
    } else {
        Write-Host "  [ERROR] No existe _mejoras/codigo/tasks_mejorado.py" -ForegroundColor Red
    }
    
    # 2.4 Verificar servidor
    Write-Host "`n[2.4] Verificar que el servidor arranca" -ForegroundColor Yellow
    Write-Host "  Ejecuta: python manage.py runserver" -ForegroundColor Yellow
    Write-Host "  Verifica que no hay errores de import" -ForegroundColor Yellow
    Read-Host "`nPresiona Enter para continuar"
} else {
    Write-Host "  [SKIP] No se copio tasks.py" -ForegroundColor Yellow
}

# ══════════════════════════════════════════════════════════════
# PASO 3: FRONTEND MEJORADO
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "PASO 3: FRONTEND MEJORADO" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 3.1 Crear directorios static
Write-Host "[3.1] Crear directorios static" -ForegroundColor Yellow
if (-not (Test-Path "turnos/static/js")) {
    New-Item -ItemType Directory -Path "turnos/static/js" -Force
    Write-Host "  [OK] Creado: turnos/static/js/" -ForegroundColor Green
}
if (-not (Test-Path "turnos/static/css")) {
    New-Item -ItemType Directory -Path "turnos/static/css" -Force
    Write-Host "  [OK] Creado: turnos/static/css/" -ForegroundColor Green
}

# 3.2 Copiar JavaScript
Write-Host "`n[3.2] Copiar dashboard.js" -ForegroundColor Yellow
if (Test-Path "_mejoras/frontend/static/js/dashboard.js") {
    Copy-Item "_mejoras/frontend/static/js/dashboard.js" -Destination "turnos/static/js/" -Force
    Write-Host "  [OK] Copiado: dashboard.js" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] No existe dashboard.js en _mejoras" -ForegroundColor Red
}

# 3.3 Copiar CSS
Write-Host "`n[3.3] Copiar custom.css" -ForegroundColor Yellow
if (Test-Path "_mejoras/frontend/static/css/custom.css") {
    Copy-Item "_mejoras/frontend/static/css/custom.css" -Destination "turnos/static/css/" -Force
    Write-Host "  [OK] Copiado: custom.css" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] No existe custom.css en _mejoras" -ForegroundColor Red
}

# 3.4 Instrucciones para templates
Write-Host "`n[3.4] IMPORTANTE: Actualizar templates" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Debes agregar estas lineas a tu base.html o dashboard template:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  En el <head>:" -ForegroundColor White
Write-Host '  <link rel="stylesheet" href="{% static ''css/custom.css'' %}">' -ForegroundColor Gray
Write-Host ""
Write-Host "  Antes de </body>:" -ForegroundColor White
Write-Host '  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>' -ForegroundColor Gray
Write-Host '  <script src="{% static ''js/dashboard.js'' %}"></script>' -ForegroundColor Gray
Write-Host ""
Write-Host "  Y agrega estos canvas donde quieras los graficos:" -ForegroundColor White
Write-Host '  <canvas id="chartDistribucionTurnos"></canvas>' -ForegroundColor Gray
Write-Host '  <canvas id="chartCargaEnfermeras"></canvas>' -ForegroundColor Gray
Write-Host ""
Read-Host "Presiona Enter cuando hayas actualizado los templates"

# 3.5 Collectstatic
Write-Host "`n[3.5] Ejecutar collectstatic" -ForegroundColor Yellow
Write-Host "  Ejecuta: python manage.py collectstatic --noinput" -ForegroundColor Yellow
Read-Host "Presiona Enter para continuar"

# ══════════════════════════════════════════════════════════════
# PASO 4: DOCUMENTACION
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "PASO 4: DOCUMENTACION" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 4.1 Crear directorio docs
Write-Host "[4.1] Crear directorio docs/" -ForegroundColor Yellow
if (-not (Test-Path "docs")) {
    New-Item -ItemType Directory -Path "docs" -Force
    Write-Host "  [OK] Directorio creado" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Ya existe" -ForegroundColor Yellow
}

# 4.2 Copiar documentacion
Write-Host "`n[4.2] Copiar archivos de documentacion" -ForegroundColor Yellow
if (Test-Path "_mejoras/docs") {
    if (Test-Path "_mejoras/docs/README.md") {
        Copy-Item "_mejoras/docs/README.md" -Destination "docs/" -Force
        Write-Host "  [OK] Copiado: docs/README.md" -ForegroundColor Green
    }
    
    if (Test-Path "_mejoras/docs/API.md") {
        Copy-Item "_mejoras/docs/API.md" -Destination "docs/" -Force
        Write-Host "  [OK] Copiado: docs/API.md" -ForegroundColor Green
    }
} else {
    Write-Host "  [ERROR] No existe _mejoras/docs/" -ForegroundColor Red
}

# 4.3 Actualizar README principal (opcional)
Write-Host "`n[4.3] Actualizar README.md principal (opcional)" -ForegroundColor Yellow
$actualizarReadme = Read-Host "¿Quieres reemplazar el README.md principal? (s/n)"
if ($actualizarReadme -eq 's' -and (Test-Path "_mejoras/docs/README.md")) {
    if (Test-Path "README.md") {
        Copy-Item "README.md" -Destination "README.md.backup" -Force
        Write-Host "  [OK] Backup: README.md.backup" -ForegroundColor Green
    }
    Copy-Item "_mejoras/docs/README.md" -Destination "README.md" -Force
    Write-Host "  [OK] README.md actualizado" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════
# PASO 5: REQUIREMENTS.TXT
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "PASO 5: ACTUALIZAR REQUIREMENTS" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[5.1] Agregar nuevas dependencias" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Agrega estas lineas a requirements.txt:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Tests" -ForegroundColor Gray
Write-Host "  pytest==7.4.3" -ForegroundColor Gray
Write-Host "  pytest-django==4.7.0" -ForegroundColor Gray
Write-Host "  pytest-cov==4.1.0" -ForegroundColor Gray
Write-Host "  factory-boy==3.3.0" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Celery (si no las tienes)" -ForegroundColor Gray
Write-Host "  celery==5.3.4" -ForegroundColor Gray
Write-Host "  redis==5.0.1" -ForegroundColor Gray
Write-Host ""

$agregarDeps = Read-Host "¿Quieres que las agregue automaticamente? (s/n)"

if ($agregarDeps -eq 's') {
    $newDeps = @(
        "pytest==7.4.3",
        "pytest-django==4.7.0",
        "pytest-cov==4.1.0",
        "factory-boy==3.3.0"
    )
    
    foreach ($dep in $newDeps) {
        $depName = $dep.Split("==")[0]
        $exists = Get-Content "requirements.txt" | Select-String -Pattern "^$depName"
        if (-not $exists) {
            Add-Content "requirements.txt" -Value $dep
            Write-Host "  [OK] Agregado: $dep" -ForegroundColor Green
        } else {
            Write-Host "  [SKIP] Ya existe: $depName" -ForegroundColor Yellow
        }
    }
    
    Write-Host "`n  Ejecuta: pip install -r requirements.txt" -ForegroundColor Yellow
}

# ══════════════════════════════════════════════════════════════
# PASO 6: VERIFICACION FINAL
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "PASO 6: VERIFICACION FINAL" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[6.1] Verificar instalacion" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Ejecuta estos comandos para verificar:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Tests:" -ForegroundColor White
Write-Host "     python -m pytest" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Servidor:" -ForegroundColor White
Write-Host "     python manage.py runserver" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Celery (en otra terminal):" -ForegroundColor White
Write-Host "     celery -A proyecto_turnos worker --loglevel=info --pool=solo" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Collectstatic:" -ForegroundColor White
Write-Host "     python manage.py collectstatic --noinput" -ForegroundColor Gray
Write-Host ""

# ══════════════════════════════════════════════════════════════
# RESUMEN
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  INSTALACION COMPLETADA" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Archivos copiados:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Tests:" -ForegroundColor White
Write-Host "    - turnos/tests/*.py" -ForegroundColor Gray
Write-Host "    - pytest.ini" -ForegroundColor Gray
Write-Host ""
Write-Host "  Codigo:" -ForegroundColor White
Write-Host "    - turnos/tasks.py (actualizado)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Frontend:" -ForegroundColor White
Write-Host "    - turnos/static/js/dashboard.js" -ForegroundColor Gray
Write-Host "    - turnos/static/css/custom.css" -ForegroundColor Gray
Write-Host ""
Write-Host "  Docs:" -ForegroundColor White
Write-Host "    - docs/README.md" -ForegroundColor Gray
Write-Host "    - docs/API.md" -ForegroundColor Gray
Write-Host ""

Write-Host "Backups creados en:" -ForegroundColor Cyan
if (Test-Path "backups") {
    Get-ChildItem "backups" -Directory | Sort-Object Name -Descending | Select-Object -First 3 | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor Gray
    }
}
Write-Host ""

Write-Host "Proximos pasos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Actualizar templates con los nuevos CSS/JS" -ForegroundColor White
Write-Host "  2. Ejecutar: python -m pytest" -ForegroundColor White
Write-Host "  3. Ejecutar: python manage.py runserver" -ForegroundColor White
Write-Host "  4. Probar el dashboard con graficos" -ForegroundColor White
Write-Host ""

Write-Host "Si algo falla:" -ForegroundColor Yellow
Write-Host "  - Revisa los backups en: backups/" -ForegroundColor White
Write-Host "  - Revisa los logs en: logs/" -ForegroundColor White
Write-Host "  - Restaura desde backup si es necesario" -ForegroundColor White
Write-Host ""

Write-Host "================================================" -ForegroundColor Green
Write-Host "  LISTO!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

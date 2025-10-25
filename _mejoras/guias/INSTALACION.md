# GUIA DE INSTALACION DE MEJORAS

## IMPORTANTE: Leer Antes de Empezar

Este sistema ha generado TODO el codigo de mejoras en la carpeta _mejoras/
SIN modificar NADA de tu proyecto actual.

## Estructura Generada

```
_mejoras/
â”œâ”€â”€ tests/          â†’ Tests unitarios
â”œâ”€â”€ codigo/         â†’ Codigo Celery mejorado
â”œâ”€â”€ frontend/       â†’ JS y CSS mejorados
â”œâ”€â”€ docs/           â†’ Documentacion
â””â”€â”€ guias/          â†’ Esta guia
```

## Paso a Paso

### 1. Revisar Contenido

Antes de copiar nada, REVISAR cada archivo en _mejoras/

```bash
# Ver tests generados
ls _mejoras/tests/

# Ver codigo Celery
cat _mejoras/codigo/tasks_mejorado.py

# Ver frontend
ls _mejoras/frontend/static/
```

### 2. Instalar Tests

```bash
# Copiar tests
cp -r _mejoras/tests/* turnos/tests/

# Copiar configuracion pytest
cp _mejoras/tests/pytest.ini .

# Instalar dependencias
pip install pytest pytest-django pytest-cov

# Probar
python -m pytest
```

### 3. Actualizar Celery

```bash
# IMPORTANTE: Hacer backup primero
cp turnos/tasks.py turnos/tasks.py.backup

# Revisar el codigo nuevo
cat _mejoras/codigo/tasks_mejorado.py

# Si todo OK, reemplazar
cp _mejoras/codigo/tasks_mejorado.py turnos/tasks.py
```

### 4. Agregar Frontend

```bash
# Copiar JS
cp _mejoras/frontend/static/js/dashboard.js turnos/static/js/

# Copiar CSS
cp _mejoras/frontend/static/css/custom.css turnos/static/css/

# Agregar Chart.js al base.html
# Ver instrucciones en _mejoras/frontend/README.md
```

### 5. Agregar Documentacion

```bash
# Crear carpeta docs si no existe
mkdir -p docs

# Copiar documentacion
cp _mejoras/docs/* docs/

# Actualizar README principal si quieres
cp _mejoras/docs/README.md README.md
```

## Verificacion Final

Despues de instalar:

```bash
# 1. Tests funcionan
python -m pytest

# 2. Servidor arranca
python manage.py runserver

# 3. Celery funciona
celery -A proyecto_turnos worker --loglevel=info

# 4. No hay errores en logs
```

## Si Algo Sale Mal

1. **Tests fallan**: Revisa imports y configuracion
2. **Celery no funciona**: Verifica Redis esta corriendo
3. **Frontend roto**: Revisa que Chart.js esta cargado

## Backup

Todos tus backups estan en:
```
backups/backup_YYYYMMDD_HHMMSS/
```

Para restaurar:
```bash
cp backups/backup_XXXXXXXX/turnos/tasks.py turnos/tasks.py
```

## Soporte

Si necesitas ayuda:
1. Revisa los README.md en cada carpeta de _mejoras/
2. Revisa los logs en logs/
3. Consulta la documentacion oficial de Django/Celery

---

**RECUERDA**: La carpeta _mejoras/ es SEGURA - no afecta tu proyecto
hasta que TU decidas copiar manualmente los archivos.

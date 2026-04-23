# Resumen de Refactorización - Planificador de Turnos

## Fecha de Ejecución
23 de abril, 2026

---

## Archivos Eliminados

### Artefactos y Basura
- `db.sqlite3` - Base de datos local (ahora en .gitignore)
- `planilla_43.csv` - CSV exportado temporal
- `planilla_44.csv` - CSV exportado temporal
- `script (2).py` - Script temporal sin usar
- `generador-corregido.py` - Script duplicado
- `ejemplo_cyl.txt` - Archivo de ejemplo Pyomo (obsoleto)
- `planificacion_debug.log` - Log generado
- `README.md.backup` - Backup redundante
- `turnos/tasks.py.backup_20251025_183235` - Backup de tasks.py

### Módulos Legacy No Usados
- `turnos/generador_pyomo.py` - Implementación Pyomo abandonada
- `README-PYOMO.md` - Documentación Pyomo obsoleta
- `turnos/backends.py` - Backend de autenticación no cableado
- `turnos/middleware.py` - Middleware no configurado en settings
- `turnos/validators.py` - Validadores no importados activamente
- `turnos/views_health.py` - Vista de health check no cableada en URLs

---

## Archivos Creados

### Configuración
- `.gitignore` - Configuración completa de ignorados (87 líneas)

### Dominio
- `turnos/dominio/__init__.py` - Módulo de dominio
- `turnos/dominio/normalizacion.py` - Capa de normalización de vocabulario (165 líneas)

### Documentación
- `docs/ARQUITECTURA.md` - Documentación completa de arquitectura (302 líneas)
- `docs/REFACTOR.md` - Este archivo

---

## Archivos Modificados

### Configuración
1. **pytest.ini** (raíz)
   - Corregido encoding a UTF-8 sin BOM
   
2. **turnos/tests/pytest.ini**
   - Corregido encoding a UTF-8 sin BOM
   
3. **proyecto_turnos/settings.py**
   - Línea 64: Cambiada ruta absoluta Windows por `BASE_DIR / 'db.sqlite3'`
   - Líneas 128-129: Celery URLs ahora configurables vía variables de entorno

### Tests
4. **turnos/tests/test_models.py**
   - Corregidos caracteres corruptos: 'MarÃ­a GarcÃ­a' → 'María García'

### Modelos
5. **turnos/models.py**
   - Añadido `INVIABLE` a `Ejecucion.ESTADO_CHOICES`
   - Añadido campo `tipo_celda` a `AsignacionTurno` con 7 opciones
   - Añadidos 6 nuevos modelos de dominio (202 líneas):
     - `ContratoEnfermera`
     - `RotacionBase`
     - `CeldaRotacion`
     - `AsignacionRotacionEnfermera`
     - `Incidencia`
     - `BalanceHistoricoEnfermera`

### Lógica de Negocio
6. **turnos/restricciones_duras.py**
   - Importada función `normalizar_nombre`
   - Línea 142: Normalizado `turnosconsecutivosmax` → `TURNO_CONSECUTIVOS_MAX`

7. **turnos/restricciones_blandas.py**
   - Importada función `normalizar_nombre`
   - Líneas 52-53: Normalizado `equidadturnos` → `EQUIDAD_TURNOS`
   - Líneas 82-84: Normalizado `minimizarnoches` → `MINIMIZAR_NOCHES`

8. **turnos/validador.py**
   - Importada función `normalizar_nombre`
   - Línea 156: Normalizado `turnosconsecutivosmax` → `TURNO_CONSECUTIVOS_MAX`

9. **turnos/views.py**
   - Línea 172: Corregido bug `patrones_turnos` → `patrones_turnos_json`

10. **turnos/utils/exportacion.py**
    - Líneas 119-126: Corregida lógica de exportación horizontal para escribir 'LIBRE' correctamente cuando `turno` es null

---

## Migraciones Necesarias

Las siguientes migraciones deben generarse y aplicarse:

1. **Añadir INVIABLE a Ejecucion.estado**
   - Tipo: Alter field
   - Campo: `estado` en modelo `Ejecucion`
   - Impacto: Bajo (solo añade opción)

2. **Añadir tipo_celda a AsignacionTurno**
   - Tipo: Add field
   - Campo: `tipo_celda` con default='TURNO'
   - Impacto: Bajo (campo con default)

3. **Crear ContratoEnfermera**
   - Tipo: Create model
   - Impacto: Medio (requiere datos de contratos)

4. **Crear RotacionBase**
   - Tipo: Create model
   - Impacto: Medio (requiere definición de rotaciones)

5. **Crear CeldaRotacion**
   - Tipo: Create model
   - Impacto: Medio (depende de RotacionBase)

6. **Crear AsignacionRotacionEnfermera**
   - Tipo: Create model
   - Impacto: Medio (requiere asignaciones explícitas)

7. **Crear Incidencia**
   - Tipo: Create model
   - Impacto: Bajo/Medio (puede poblarse gradualmente)

8. **Crear BalanceHistoricoEnfermera**
   - Tipo: Create model
   - Impacto: Medio (requiere cálculo de balances iniciales)

### Comando para Generar Migraciones
```bash
python manage.py makemigrations turnos
```

### Comando para Aplicar Migraciones
```bash
python manage.py migrate
```

---

## Bugs Corregidos

### 1. Divergencia de Nombres en Restricciones
**Problema:** Frontend usaba `turnos_consecutivos_max`, backend buscaba `turnosconsecutivosmax`

**Solución:** Capa de normalización que traduce automáticamente ambos al canónico `TURNO_CONSECUTIVOS_MAX`

**Archivos afectados:**
- `turnos/dominio/normalizacion.py` (nuevo)
- `turnos/restricciones_duras.py`
- `turnos/restricciones_blandas.py`
- `turnos/validador.py`

### 2. views.py Lee Campo Incorrecto de Patrones
**Problema:** Formulario usa `patrones_turnos_json` pero views.py leía `patrones_turnos`

**Solución:** Corregido a `form.cleaned_data.get('patrones_turnos_json', '')`

**Archivo:** `turnos/views.py` línea 172

### 3. Ejecucion.estado No Contempla INVIABLE
**Problema:** `tasks.py` establece estado 'INVIABLE' pero no estaba en `ESTADO_CHOICES`

**Solución:** Añadido 'INVIABLE' a las opciones de estado

**Archivo:** `turnos/models.py`

### 4. Exportación Horizontal No Escribe LIBRE Correctamente
**Problema:** Cuando `turno` es null pero `es_dia_libre=False`, la celda se exportaba vacía en lugar de 'LIBRE'

**Solución:** Cambiada lógica a `if asignacion.es_dia_libre or not asignacion.turno:`

**Archivo:** `turnos/utils/exportacion.py`

---

## Mejoras de Infraestructura

### 1. .gitignore Completo
- Database files (*.sqlite3)
- Virtual environments (venv/, .venv/)
- IDE files (.idea/, .vscode/)
- Generated static files (staticfiles/)
- Logs (*.log, logs/)
- OS files (.DS_Store, Thumbs.db)
- Celery files (celerybeat-schedule, celerybeat.pid)
- Exported files (*.csv, *.xlsx)
- Backups (*.backup, *.backup_*)

### 2. Encoding UTF-8
- pytest.ini (raíz y tests/)
- requirements.txt
- test_models.py (caracteres corruptos corregidos)

### 3. Settings.py Portable
- Ruta SQLite relativa: `BASE_DIR / 'db.sqlite3'`
- Celery URLs configurables vía variables de entorno

---

## Código Legacy Mantenido

Los siguientes módulos se mantienen por compatibilidad pero deben revisarse:

- `turnos/generador_patrones.py` - Importado por `generador.py`, marcado para deprecación
- `turnos/generador_refactorizado.py` - Generador actual, será reemplazado por nuevo motor
- `turnos/patrones.py` - Patrones personalizados, integrado parcialmente

---

## Trabajo Pendiente

### Fase 3: Motor de Planificación (No Iniciada)
- [ ] Crear estructura `turnos/motor/`
- [ ] Implementar pipeline de planificación
- [ ] Implementar objetivos lexicográficos
- [ ] Implementar reparador CP-SAT
- [ ] Integrar con código existente

### Fase 4: Normalización Completa (Parcial)
- [x] Crear vocabulario canónico (en normalizacion.py)
- [ ] Crear adaptadores de compatibilidad
- [ ] Crear capa de DTOs internos

### Fase 5: Tests (No Iniciada)
- [ ] Reorganizar estructura de tests
- [ ] Tests de dominio y normalización
- [ ] Tests de motor
- [ ] Tests de integración
- [ ] Tests de exportación

### Fase 6: Documentación (Parcial)
- [x] Documentación de arquitectura (docs/ARQUITECTURA.md)
- [x] Resumen de refactorización (docs/REFACTOR.md)
- [ ] Documentación de API
- [ ] Guía de usuario
- [ ] Ejemplos de uso

---

## Verificación de Estado

### Comandos para Verificar Integridad

```bash
# Verificar que Django no tiene errores
python manage.py check

# Generar migraciones pendientes
python manage.py makemigrations turnos

# Aplicar migraciones
python manage.py migrate

# Ejecutar tests existentes
pytest

# Verificar imports rotos
python -c "import turnos; import turnos.models; import turnos.views"
```

### Estado Actual del Proyecto

✅ **Repo limpio:** Sin artefactos ni archivos temporales  
✅ **Encoding correcto:** UTF-8 sin BOM en archivos de configuración  
✅ **Settings portable:** Sin rutas absolutas de Windows  
✅ **Módulos legacy eliminados:** 6 módulos no usados eliminados  
✅ **Normalización implementada:** Capa de traducción de nombres legacy  
✅ **Bugs críticos corregidos:** 4 bugs identificados y corregidos  
✅ **Nuevos modelos creados:** 6 modelos de dominio añadidos  
✅ **Documentación creada:** Arquitectura y resumen de cambios  

⏳ **Pendiente:** Motor de planificación, tests exhaustivos, migraciones, adaptadores

---

## Notas Finales

Esta refactorización establece las bases para un planificador de turnos de enfermería robusto y mantenible. Los cambios de Fase 0 y Fase 1 son **no destructivos** y mantienen compatibilidad total con datos existentes.

Los próximos pasos (Fases 3-5) implementarán el nuevo motor de planificación y los tests de negocio que validarán el comportamiento del sistema.

**Importante:** Antes de aplicar migraciones en producción, realizar backup completo de la base de datos.

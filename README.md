# Planificador de Turnos de Enfermería

Sistema inteligente de planificación automática de cuadrantes de enfermería usando OR-Tools CP-SAT.

## Características

- Generación de planillas mensuales tipo cuadrante real con rotaciones cíclicas
- Motor de reparación CP-SAT (Google OR-Tools) — no generador libre
- Equilibrio de horas, noches, fines de semana y festivos
- Planificación contextual dependiente del histórico mensual
- Wizard de configuración guiado en 4 pasos
- Procesamiento asíncrono con Celery + Redis
- Exportación a Excel, PDF, CSV e iCalendar
- Dashboard con visualizaciones y estadísticas
- Sistema multi-workspace para múltiples organizaciones

## Inicio Rápido

### Modo Desarrollo (recomendado para pruebas)

```bash
git clone https://github.com/LuisSereno/planificador_turnos.git
cd planificador_turnos

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py crear_tipos_turno
python manage.py generar_datos_prueba
python manage.py createsuperuser

python manage.py runserver
```

O usando el script automático (incluye Celery + Redis):

```bash
./start.sh --dev
```

Acceso: http://localhost:8001 | Admin: `admin` / `Admin123!@#`

### Modo Producción (Docker / Podman)

```bash
cp .env.example .env
# Editar .env con contraseñas seguras

./start.sh          # Con Podman
# o
docker-compose up -d --build
```

Acceso: http://localhost:8080

## Tecnologías

| Componente | Tecnología |
|------------|-----------|
| Backend | Django 5.1 |
| Solver | OR-Tools CP-SAT 9.14 (Google) |
| Tareas asíncronas | Celery 5.5 + Redis 7 |
| Base de datos | PostgreSQL 16 (prod) / SQLite (dev) |
| Frontend | Bootstrap 5 + Chart.js |
| Servidor | Gunicorn + Nginx |
| Contenedores | Docker / Podman (rootless) |

## Documentación

- [Wiki completa](docs/WIKI.md) — arquitectura, modelos, wizard, restricciones, troubleshooting
- [Arquitectura del sistema](docs/ARQUITECTURA.md)
- [API REST](docs/API.md)
- [Resumen de refactorización](docs/FINAL_SUMMARY.md)

## Tests

```bash
pytest                              # Todos los tests
pytest turnos/tests/test_dominio/   # Tests de dominio (sin BD)
pytest turnos/tests/test_motor/     # Tests del motor CP-SAT
pytest --cov=turnos                 # Con cobertura
```

Estado: **36 tests pasando (100%)**

## Comandos Útiles

```bash
# Crear tipos de turno estándar (M, T, N, L, D)
python manage.py crear_tipos_turno

# Importar enfermeras desde Excel
python manage.py importar_enfermeras --file enfermeras.xlsx

# Ejecutar planificación desde CLI
python manage.py run_planificacion --config-id 1

# Ver estadísticas del sistema
python manage.py estadisticas_sistema
```

## Licencia

MIT License

## Autor

Luis Sereno — [@LuisSereno](https://github.com/LuisSereno)

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

```bash
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
```

## Uso Basico

1. **Configurar Turnos**: Crea los turnos (MaÃ±ana, Tarde, Noche)
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

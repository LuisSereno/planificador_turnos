#!/bin/bash
set -e

echo "Esperando a PostgreSQL..."
/wait-for-it.sh db:5432 --timeout=60 --strict -- echo "PostgreSQL está listo"

echo "Esperando a Redis..."
/wait-for-it.sh redis:6379 --timeout=60 --strict -- echo "Redis está listo"

echo "Aplicando migraciones..."
python manage.py migrate --noinput

echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

echo "Creando superusuario si no existe..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@planificador.com', 'Admin123!@#');
    print('Superusuario admin creado');
else:
    print('Superusuario admin ya existe');
"

echo "Cargando datos iniciales..."
python manage.py loaddata turnos/fixtures/initial_data.json || echo "No hay fixtures para cargar"

echo "Iniciando aplicación..."
exec "$@"

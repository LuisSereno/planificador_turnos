#!/bin/bash
set -e

echo "Aplicando migraciones..."
python manage.py migrate --noinput

echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "Creando superusuario si no existe..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@planificador.com', 'Admin123!@#')
    print('Superusuario admin creado')
else:
    print('Superusuario admin ya existe')
"

echo "Cargando datos iniciales..."
python manage.py loaddata turnos/fixtures/initial_data.json || echo "No hay fixtures para cargar"

echo "Iniciando gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 2 --timeout 120 proyecto_turnos.wsgi:application

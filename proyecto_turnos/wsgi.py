"""
WSGI proyecto_turnos for planificador turnos project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Establecer el módulo de configuración Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')

# Obtener la aplicación WSGI
application = get_wsgi_application()

# Configuración adicional para producción (opcional)
# Para WhiteNoise (servir archivos estáticos)
try:
    from whitenoise import WhiteNoise
    application = WhiteNoise(application)
    application.add_files('/app/staticfiles/', prefix='static/')
except ImportError:
    pass

"""
ASGI proyecto_turnos for planificador turnos project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Establecer el módulo de configuración Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')

# Inicializar Django ASGI application primero
django_asgi_app = get_asgi_application()

# Si vas a usar Channels para WebSockets, descomentar esto:
"""
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
import turnos.routing

application = ProtocolTypeRouter({
    # Django's ASGI application para manejar solicitudes HTTP tradicionales
    "http": django_asgi_app,

    # WebSocket chat handler
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                turnos.routing.websocket_urlpatterns
            )
        )
    ),
})
"""

# Por ahora, sin WebSockets (configuración simple)
application = django_asgi_app

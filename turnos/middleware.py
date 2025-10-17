"""
Custom middleware for turnos app
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

logger = logging.getLogger(__name__)


class RequestTimingMiddleware(MiddlewareMixin):
    """
    Middleware para medir el tiempo de respuesta de las peticiones
    """

    def process_request(self, request):
        """Guarda el tiempo de inicio de la petición"""
        request.start_time = time.time()

    def process_response(self, request, response):
        """Calcula y registra el tiempo de respuesta"""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            response['X-Request-Duration'] = str(duration)

            # Registrar peticiones lentas (> 2 segundos)
            if duration > 2.0:
                logger.warning(
                    f'Slow request: {request.path} took {duration:.2f}s '
                    f'[User: {request.user.username if request.user.is_authenticated else "Anonymous"}]'
                )

        return response


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Middleware para modo de mantenimiento
    """

    def process_request(self, request):
        """Redirige al modo mantenimiento si está activado"""
        from django.conf import settings

        # Verificar si el modo mantenimiento está activado
        maintenance_mode = getattr(settings, 'MAINTENANCE_MODE', False)

        if maintenance_mode:
            # Permitir acceso a superusuarios
            if request.user.is_authenticated and request.user.is_superuser:
                return None

            # Permitir acceso a la página de mantenimiento
            if request.path == reverse('turnos:maintenance'):
                return None

            # Redirigir al resto de usuarios
            return redirect('turnos:maintenance')

        return None


class UserActivityMiddleware(MiddlewareMixin):
    """
    Middleware para registrar la actividad del usuario
    """

    def process_request(self, request):
        """Registra la actividad del usuario"""
        if request.user.is_authenticated:
            # Actualizar última actividad
            from django.utils import timezone
            request.user.last_activity = timezone.now()
            request.user.save(update_fields=['last_activity'])

        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware para añadir headers de seguridad
    """

    def process_response(self, request, response):
        """Añade headers de seguridad"""
        # Prevenir clickjacking
        response['X-Frame-Options'] = 'DENY'

        # Prevenir MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'

        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response


class APIRateLimitMiddleware(MiddlewareMixin):
    """
    Middleware simple para limitar la tasa de peticiones a la API
    """

    def process_request(self, request):
        """Verifica el rate limit"""
        if request.path.startswith('/api/'):
            from django.core.cache import cache

            # Obtener IP del cliente
            ip = self._get_client_ip(request)
            cache_key = f'rate_limit_{ip}'

            # Obtener contador de peticiones
            requests_count = cache.get(cache_key, 0)

            # Límite: 100 peticiones por minuto
            if requests_count >= 100:
                from django.http import JsonResponse
                return JsonResponse({
                    'error': 'Rate limit exceeded. Try again later.'
                }, status=429)

            # Incrementar contador
            cache.set(cache_key, requests_count + 1, 60)

        return None

    def _get_client_ip(self, request):
        """Obtiene la IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware para manejo centralizado de errores
    """

    def process_exception(self, request, exception):
        """Maneja excepciones no capturadas"""
        logger.error(
            f'Unhandled exception: {str(exception)}',
            exc_info=True,
            extra={
                'request': request,
                'user': request.user.username if request.user.is_authenticated else 'Anonymous'
            }
        )

        # No interceptar en modo debug
        from django.conf import settings
        if settings.DEBUG:
            return None

        # Mostrar mensaje amigable al usuario
        messages.error(
            request,
            'Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo más tarde.'
        )

        return None

"""
Health check views for monitoring
"""
from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class HealthCheckView(View):
    """
    Vista para health check básico
    Retorna 200 si la aplicación está funcionando
    """

    def get(self, request):
        return JsonResponse({
            'status': 'ok',
            'timestamp': timezone.now().isoformat()
        })


class DetailedHealthCheckView(View):
    """
    Vista para health check detallado
    Verifica base de datos, cache, etc.
    """

    def get(self, request):
        health_status = {
            'status': 'ok',
            'timestamp': timezone.now().isoformat(),
            'checks': {}
        }

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_status['checks']['database'] = {
                    'status': 'ok',
                    'message': 'Database connection successful'
                }
        except Exception as e:
            health_status['status'] = 'error'
            health_status['checks']['database'] = {
                'status': 'error',
                'message': str(e)
            }
            logger.error(f'Database health check failed: {str(e)}')

        # Check cache
        try:
            cache_key = 'health_check_test'
            cache.set(cache_key, 'test', 10)
            cache_value = cache.get(cache_key)

            if cache_value == 'test':
                health_status['checks']['cache'] = {
                    'status': 'ok',
                    'message': 'Cache working correctly'
                }
            else:
                raise Exception('Cache value mismatch')

        except Exception as e:
            health_status['status'] = 'error'
            health_status['checks']['cache'] = {
                'status': 'error',
                'message': str(e)
            }
            logger.error(f'Cache health check failed: {str(e)}')

        # Check models
        try:
            from .models import ConfiguracionPlanificacion
            count = ConfiguracionPlanificacion.objects.count()
            health_status['checks']['models'] = {
                'status': 'ok',
                'message': f'Models accessible. Found {count} configurations'
            }
        except Exception as e:
            health_status['status'] = 'error'
            health_status['checks']['models'] = {
                'status': 'error',
                'message': str(e)
            }
            logger.error(f'Models health check failed: {str(e)}')

        # Status code
        status_code = 200 if health_status['status'] == 'ok' else 503

        return JsonResponse(health_status, status=status_code)


class ReadinessCheckView(View):
    """
    Vista para readiness check (Kubernetes)
    Verifica si la aplicación está lista para recibir tráfico
    """

    def get(self, request):
        try:
            # Verificar que se puede hacer una query a la BD
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            return JsonResponse({
                'status': 'ready',
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            logger.error(f'Readiness check failed: {str(e)}')
            return JsonResponse({
                'status': 'not_ready',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=503)


class LivenessCheckView(View):
    """
    Vista para liveness check (Kubernetes)
    Verifica si la aplicación está viva (no colgada)
    """

    def get(self, request):
        return JsonResponse({
            'status': 'alive',
            'timestamp': timezone.now().isoformat()
        })

"""
Custom decorators for turnos app
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden


def superuser_required(view_func):
    """
    Decorator que requiere que el usuario sea superusuario
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if not request.user.is_superuser:
            messages.error(request, 'No tienes permisos para acceder a esta página.')
            return redirect('turnos:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper


def staff_required(view_func):
    """
    Decorator que requiere que el usuario sea staff
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if not request.user.is_staff:
            messages.error(request, 'No tienes permisos para acceder a esta página.')
            return redirect('turnos:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper


def permission_required_custom(permission):
    """
    Decorator personalizado para verificar permisos específicos
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            if not request.user.has_perm(permission):
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def ajax_required(view_func):
    """
    Decorator que requiere que la petición sea AJAX
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden('Esta vista solo acepta peticiones AJAX')

        return view_func(request, *args, **kwargs)

    return wrapper


def owner_required(model_field='creado_por'):
    """
    Decorator que verifica que el usuario sea el propietario del objeto
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Obtener el objeto (asume que la vista es una CBV con get_object)
            obj = view_func.__self__.get_object() if hasattr(view_func, '__self__') else None

            if obj and hasattr(obj, model_field):
                owner = getattr(obj, model_field)
                if owner != request.user and not request.user.is_superuser:
                    messages.error(request, 'No tienes permisos para modificar este objeto.')
                    return redirect('turnos:dashboard')

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def throttle(rate_limit=10, period=60):
    """
    Decorator simple para limitar la tasa de peticiones
    rate_limit: número máximo de peticiones
    period: período en segundos
    """
    from django.core.cache import cache

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Crear clave única para el usuario
            cache_key = f'throttle_{request.user.id}_{view_func.__name__}'

            # Obtener contador actual
            count = cache.get(cache_key, 0)

            if count >= rate_limit:
                messages.error(
                    request,
                    f'Has excedido el límite de peticiones. Espera {period} segundos.'
                )
                return redirect('turnos:dashboard')

            # Incrementar contador
            cache.set(cache_key, count + 1, period)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def log_action(action_name):
    """
    Decorator para registrar acciones del usuario
    """
    import logging
    logger = logging.getLogger(__name__)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user.username if request.user.is_authenticated else 'Anonymous'
            logger.info(f'User {user} performed action: {action_name}')

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator

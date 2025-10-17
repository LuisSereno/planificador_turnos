"""
Custom authentication backends for turnos app
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    """
    Permite autenticación usando email en lugar de username
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Intenta autenticar con email o username
        """
        try:
            # Intentar buscar por email
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # Si no existe, intentar con username
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None

        # Verificar password
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None


class PermissionBackend(ModelBackend):
    """
    Backend personalizado para verificar permisos específicos de turnos
    """

    def has_perm(self, user_obj, perm, obj=None):
        """
        Verifica si el usuario tiene un permiso específico
        """
        if not user_obj.is_active:
            return False

        # Superusuarios tienen todos los permisos
        if user_obj.is_superuser:
            return True

        # Verificar permisos específicos de turnos
        if perm.startswith('turnos.'):
            # Staff puede ver pero no necesariamente editar
            if user_obj.is_staff and 'view' in perm:
                return True

            # Verificar permisos del modelo
            return super().has_perm(user_obj, perm, obj)

        return super().has_perm(user_obj, perm, obj)

    def has_module_perms(self, user_obj, app_label):
        """
        Verifica si el usuario tiene permisos para el módulo
        """
        if not user_obj.is_active:
            return False

        if user_obj.is_superuser:
            return True

        if app_label == 'turnos':
            return user_obj.is_staff or user_obj.has_perm('turnos.view_configuracionplanificacion')

        return super().has_module_perms(user_obj, app_label)

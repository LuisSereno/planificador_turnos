"""
Authentication views for turnos app
"""
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.views import (
    PasswordResetView as DjangoPasswordResetView,
    PasswordResetDoneView as DjangoPasswordResetDoneView,
    PasswordResetConfirmView as DjangoPasswordResetConfirmView,
    PasswordResetCompleteView as DjangoPasswordResetCompleteView,
    PasswordChangeView as DjangoPasswordChangeView,
    PasswordChangeDoneView as DjangoPasswordChangeDoneView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.views.generic import FormView, View, UpdateView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginView(FormView):
    """Vista de login personalizada"""
    template_name = 'accounts/login.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('turnos:dashboard')

    def form_valid(self, form):
        """Procesa el login"""
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')

        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            login(self.request, user)
            messages.success(self.request, f'¡Bienvenido, {user.get_full_name() or user.username}!')

            # Redirigir a la página solicitada o al dashboard
            next_url = self.request.GET.get('next')
            if next_url:
                return redirect(next_url)

            return redirect(self.success_url)
        else:
            messages.error(self.request, 'Usuario o contraseña incorrectos.')
            return self.form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        """Redirige al dashboard si ya está autenticado"""
        if request.user.is_authenticated:
            return redirect('turnos:dashboard')
        return super().dispatch(request, *args, **kwargs)


class LogoutView(View):
    """Vista de logout"""

    def get(self, request):
        logout(request)
        messages.info(request, 'Has cerrado sesión correctamente.')
        return redirect('accounts:login')

    def post(self, request):
        return self.get(request)


class RegistroView(FormView):
    """Vista de registro de nuevos usuarios"""
    template_name = 'accounts/registro.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        """Crea el usuario"""
        user = form.save()
        messages.success(
            self.request,
            'Usuario creado con éxito. Ya puedes iniciar sesión.'
        )
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        """Redirige al dashboard si ya está autenticado"""
        if request.user.is_authenticated:
            return redirect('turnos:dashboard')
        return super().dispatch(request, *args, **kwargs)


class EditarPerfilView(LoginRequiredMixin, UpdateView):
    """Vista para editar el perfil del usuario"""
    model = User
    fields = ['first_name', 'last_name', 'email']
    template_name = 'accounts/editar_perfil.html'
    success_url = reverse_lazy('turnos:perfil')

    def get_object(self, queryset=None):
        """Retorna el usuario actual"""
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Perfil actualizado con éxito.')
        return super().form_valid(form)


# ========== Vistas de Recuperación de Contraseña ==========

class PasswordResetView(DjangoPasswordResetView):
    """Vista para solicitar reset de contraseña"""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class PasswordResetDoneView(DjangoPasswordResetDoneView):
    """Vista que confirma el envío del email"""
    template_name = 'accounts/password_reset_done.html'


class PasswordResetConfirmView(DjangoPasswordResetConfirmView):
    """Vista para confirmar el reset de contraseña"""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class PasswordResetCompleteView(DjangoPasswordResetCompleteView):
    """Vista que confirma el reset completado"""
    template_name = 'accounts/password_reset_complete.html'


# ========== Vistas de Cambio de Contraseña ==========

class PasswordChangeView(LoginRequiredMixin, DjangoPasswordChangeView):
    """Vista para cambiar contraseña"""
    template_name = 'accounts/cambiar_password.html'
    success_url = reverse_lazy('accounts:cambiar_password_done')

    def form_valid(self, form):
        messages.success(self.request, 'Contraseña cambiada con éxito.')
        return super().form_valid(form)


class PasswordChangeDoneView(LoginRequiredMixin, DjangoPasswordChangeDoneView):
    """Vista que confirma el cambio de contraseña"""
    template_name = 'accounts/cambiar_password_done.html'

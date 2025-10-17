"""
URL configuration for authentication
"""
from django.urls import path
from . import views_auth

app_name = 'accounts'

urlpatterns = [
    path('login/', views_auth.LoginView.as_view(), name='login'),
    path('logout/', views_auth.LogoutView.as_view(), name='logout'),
    path('registro/', views_auth.RegistroView.as_view(), name='registro'),
    path('password/reset/', views_auth.PasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', views_auth.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password/reset/confirm/<uidb64>/<token>/', views_auth.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/complete/', views_auth.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('password/change/', views_auth.PasswordChangeView.as_view(), name='cambiar_password'),
    path('password/change/done/', views_auth.PasswordChangeDoneView.as_view(), name='cambiar_password_done'),
    path('editar-perfil/', views_auth.EditarPerfilView.as_view(), name='editar_perfil'),
]

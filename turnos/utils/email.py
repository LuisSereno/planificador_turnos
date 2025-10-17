"""
EMAIL.PY - Utilidades para envío de emails
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


def enviar_email_con_template(
        destinatario,
        asunto,
        template_html,
        template_txt=None,
        contexto=None,
        adjuntos=None,
        reply_to=None
):
    """
    Función genérica para enviar emails con templates HTML y texto plano

    Args:
        destinatario: Email del destinatario (str) o lista de emails
        asunto: Asunto del email
        template_html: Ruta al template HTML
        template_txt: Ruta al template de texto plano (opcional)
        contexto: Diccionario con variables para los templates
        adjuntos: Lista de tuplas (nombre_archivo, contenido, mimetype)
        reply_to: Email para responder

    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    try:
        if contexto is None:
            contexto = {}

        # Añadir configuración base al contexto
        contexto.update({
            'site_name': getattr(settings, 'SITE_NAME', 'Planificador de Turnos'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@planificador.com'),
        })

        # Renderizar contenido HTML
        html_content = render_to_string(template_html, contexto)

        # Renderizar contenido de texto plano
        if template_txt:
            text_content = render_to_string(template_txt, contexto)
        else:
            # Si no hay template de texto, extraer texto del HTML
            text_content = strip_tags(html_content)

        # Convertir destinatario a lista si es string
        if isinstance(destinatario, str):
            destinatarios = [destinatario]
        else:
            destinatarios = destinatario

        # Crear el email
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
            reply_to=[reply_to] if reply_to else None
        )

        # Adjuntar versión HTML
        email.attach_alternative(html_content, "text/html")

        # Añadir adjuntos si existen
        if adjuntos:
            for nombre, contenido, mimetype in adjuntos:
                email.attach(nombre, contenido, mimetype)

        # Enviar
        email.send(fail_silently=False)

        logger.info(f"Email enviado correctamente a {', '.join(destinatarios)}: {asunto}")
        return True

    except Exception as e:
        logger.error(f"Error al enviar email a {destinatario}: {str(e)}")
        return False


def enviar_email_verificacion(usuario, request=None):
    """
    Envía email de verificación de cuenta

    Args:
        usuario: Instancia del modelo Usuario
        request: HttpRequest object (opcional, para obtener dominio)

    Returns:
        bool: True si se envió correctamente
    """
    try:
        # Generar token de verificación (debe existir)
        from turnos.models import VerificacionEmail
        verificacion = VerificacionEmail.objects.create(usuario=usuario)

        # Construir URL de verificación
        if request:
            dominio = get_current_site(request).domain
            protocolo = 'https' if request.is_secure() else 'http'
        else:
            dominio = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
            protocolo = 'https' if not settings.DEBUG else 'http'

        url_verificacion = f"{protocolo}://{dominio}{reverse('accounts:verificar_email', kwargs={'token': verificacion.token})}"

        contexto = {
            'usuario': usuario,
            'url_verificacion': url_verificacion,
            'nombre_completo': usuario.get_full_name() or usuario.username,
            'expiracion_horas': 24,
        }

        return enviar_email_con_template(
            destinatario=usuario.email,
            asunto='Verifica tu cuenta - Planificador de Turnos',
            template_html='emails/verificacion_email.html',
            template_txt='emails/verificacion_email.txt',
            contexto=contexto
        )

    except Exception as e:
        logger.error(f"Error al enviar email de verificación a {usuario.email}: {str(e)}")
        return False


def enviar_email_recuperacion_password(usuario, request=None):
    """
    Envía email de recuperación de contraseña

    Args:
        usuario: Instancia del modelo Usuario
        request: HttpRequest object (opcional)

    Returns:
        bool: True si se envió correctamente
    """
    try:
        # Generar token de recuperación
        from turnos.models import SolicitudRecuperacionPassword
        solicitud = SolicitudRecuperacionPassword.objects.create(usuario=usuario)

        # Construir URL de reset
        if request:
            dominio = get_current_site(request).domain
            protocolo = 'https' if request.is_secure() else 'http'
        else:
            dominio = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
            protocolo = 'https' if not settings.DEBUG else 'http'

        url_reset = f"{protocolo}://{dominio}{reverse('accounts:reset_password', kwargs={'token': solicitud.token})}"

        contexto = {
            'usuario': usuario,
            'url_reset': url_reset,
            'nombre_completo': usuario.get_full_name() or usuario.username,
            'expiracion_horas': 1,
        }

        return enviar_email_con_template(
            destinatario=usuario.email,
            asunto='Recuperación de contraseña - Planificador de Turnos',
            template_html='emails/recuperacion_password.html',
            template_txt='emails/recuperacion_password.txt',
            contexto=contexto
        )

    except Exception as e:
        logger.error(f"Error al enviar email de recuperación a {usuario.email}: {str(e)}")
        return False


def enviar_email_bienvenida(usuario):
    """
    Envía email de bienvenida tras registro exitoso

    Args:
        usuario: Instancia del modelo Usuario

    Returns:
        bool: True si se envió correctamente
    """
    try:
        contexto = {
            'usuario': usuario,
            'nombre_completo': usuario.get_full_name() or usuario.username,
            'url_dashboard': f"{settings.SITE_URL}/turnos/dashboard/",
        }

        return enviar_email_con_template(
            destinatario=usuario.email,
            asunto='¡Bienvenido a Planificador de Turnos!',
            template_html='emails/bienvenida.html',
            template_txt='emails/bienvenida.txt',
            contexto=contexto
        )

    except Exception as e:
        logger.error(f"Error al enviar email de bienvenida a {usuario.email}: {str(e)}")
        return False


def enviar_email_cambio_password_exitoso(usuario):
    """
    Envía confirmación de cambio de contraseña

    Args:
        usuario: Instancia del modelo Usuario

    Returns:
        bool: True si se envió correctamente
    """
    try:
        contexto = {
            'usuario': usuario,
            'nombre_completo': usuario.get_full_name() or usuario.username,
            'fecha_cambio': usuario.last_login,
        }

        return enviar_email_con_template(
            destinatario=usuario.email,
            asunto='Contraseña cambiada correctamente',
            template_html='emails/password_cambiado.html',
            template_txt='emails/password_cambiado.txt',
            contexto=contexto
        )

    except Exception as e:
        logger.error(f"Error al enviar confirmación de cambio de password a {usuario.email}: {str(e)}")
        return False


def enviar_email_reenvio_verificacion(usuario, request=None):
    """
    Reenvía email de verificación (usa el mismo template que verificación)

    Args:
        usuario: Instancia del modelo Usuario
        request: HttpRequest object (opcional)

    Returns:
        bool: True si se envió correctamente
    """
    return enviar_email_verificacion(usuario, request)


def enviar_email_ejecucion_completada(ejecucion, usuario):
    """
    Envía notificación de que una ejecución ha sido completada

    Args:
        ejecucion: Instancia de EjecucionPlanificacion
        usuario: Instancia del modelo Usuario

    Returns:
        bool: True si se envió correctamente
    """
    try:
        contexto = {
            'usuario': usuario,
            'ejecucion': ejecucion,
            'configuracion': ejecucion.configuracion,
            'url_resultado': f"{settings.SITE_URL}/turnos/ejecuciones/{ejecucion.id}/",
            'nombre_completo': usuario.get_full_name() or usuario.username,
            'es_optima': ejecucion.es_optima,
            'penalizacion': ejecucion.penalizacion_total,
            'duracion': ejecucion.duracion,
        }

        return enviar_email_con_template(
            destinatario=usuario.email,
            asunto=f'Planificación completada: {ejecucion.configuracion.nombre}',
            template_html='emails/ejecucion_completada.html',
            template_txt='emails/ejecucion_completada.txt',
            contexto=contexto
        )

    except Exception as e:
        logger.error(f"Error al enviar notificación de ejecución completada: {str(e)}")
        return False


def enviar_email_ejecucion_error(ejecucion, usuario):
    """
    Envía notificación de que una ejecución ha fallado

    Args:
        ejecucion: Instancia de EjecucionPlanificacion
        usuario: Instancia del modelo Usuario

    Returns:
        bool: True si se envió correctamente
    """
    try:
        contexto = {
            'usuario': usuario,
            'ejecucion': ejecucion,
            'configuracion': ejecucion.configuracion,
            'nombre_completo': usuario.get_full_name() or usuario.username,
            'mensajes_error': ejecucion.mensajes.get('errores', []) if ejecucion.mensajes else [],
        }

        return enviar_email_con_template(
            destinatario=usuario.email,
            asunto=f'Error en planificación: {ejecucion.configuracion.nombre}',
            template_html='emails/ejecucion_error.html',
            template_txt='emails/ejecucion_error.txt',
            contexto=contexto
        )

    except Exception as e:
        logger.error(f"Error al enviar notificación de ejecución fallida: {str(e)}")
        return False


def enviar_email_recordatorio_turno(enfermera, turno_fecha, turno_tipo):
    """
    Envía recordatorio de turno próximo

    Args:
        enfermera: Instancia de Enfermera
        turno_fecha: Fecha del turno
        turno_tipo: Tipo de turno (MAÑANA, TARDE, NOCHE)

    Returns:
        bool: True si se envió correctamente
    """
    try:
        contexto = {
            'enfermera': enfermera,
            'turno_fecha': turno_fecha,
            'turno_tipo': turno_tipo,
        }

        return enviar_email_con_template(
            destinatario=enfermera.email,
            asunto=f'Recordatorio: Turno {turno_tipo} el {turno_fecha.strftime("%d/%m/%Y")}',
            template_html='emails/recordatorio_turno.html',
            template_txt='emails/recordatorio_turno.txt',
            contexto=contexto
        )

    except Exception as e:
        logger.error(f"Error al enviar recordatorio de turno a {enfermera.email}: {str(e)}")
        return False


def enviar_email_masivo(destinatarios, asunto, mensaje_html, mensaje_txt=None):
    """
    Envía email masivo a múltiples destinatarios

    Args:
        destinatarios: Lista de emails
        asunto: Asunto del email
        mensaje_html: Contenido HTML
        mensaje_txt: Contenido texto plano (opcional)

    Returns:
        dict: {'exitosos': int, 'fallidos': int, 'errores': list}
    """
    exitosos = 0
    fallidos = 0
    errores = []

    for destinatario in destinatarios:
        try:
            email = EmailMultiAlternatives(
                subject=asunto,
                body=mensaje_txt or strip_tags(mensaje_html),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[destinatario]
            )
            email.attach_alternative(mensaje_html, "text/html")
            email.send(fail_silently=False)
            exitosos += 1

        except Exception as e:
            fallidos += 1
            errores.append(f"{destinatario}: {str(e)}")
            logger.error(f"Error al enviar email masivo a {destinatario}: {str(e)}")

    return {
        'exitosos': exitosos,
        'fallidos': fallidos,
        'errores': errores
    }

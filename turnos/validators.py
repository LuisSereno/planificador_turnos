"""
Custom validators for turnos app
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime, time
import re


def validar_dni_espanol(value):
    """
    Valida que el DNI tenga formato español válido

    Args:
        value: String con el DNI

    Raises:
        ValidationError: Si el formato no es válido
    """
    if not value:
        return

    value = value.upper().strip()

    # Formato: 8 dígitos + 1 letra
    pattern = r'^\d{8}[A-Z]$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('El DNI debe tener 8 dígitos seguidos de una letra (ej: 12345678A)')
        )

    # Validar letra
    letras = 'TRWAGMYFPDXBNJZSQVHLCKE'
    numero = int(value[:8])
    letra = value[8]
    letra_correcta = letras[numero % 23]

    if letra != letra_correcta:
        raise ValidationError(
            _('La letra del DNI no es correcta. Debería ser %(letra)s'),
            params={'letra': letra_correcta}
        )


def validar_email_corporativo(value):
    """
    Valida que el email sea corporativo (dominio específico)

    Args:
        value: String con el email
    """
    dominios_permitidos = ['hospital.com', 'salud.es', 'clinica.com']

    if '@' in value:
        dominio = value.split('@')[1]
        if dominio not in dominios_permitidos:
            raise ValidationError(
                _('El email debe pertenecer a uno de los dominios corporativos: %(dominios)s'),
                params={'dominios': ', '.join(dominios_permitidos)}
            )


def validar_horario_turno(hora_inicio, hora_fin):
    """
    Valida que el horario del turno sea coherente

    Args:
        hora_inicio: time object
        hora_fin: time object
    """
    if not isinstance(hora_inicio, time) or not isinstance(hora_fin, time):
        raise ValidationError(_('Las horas deben ser objetos time válidos'))

    # Calcular duración
    inicio = datetime.combine(datetime.today(), hora_inicio)
    fin = datetime.combine(datetime.today(), hora_fin)

    if fin < inicio:
        from datetime import timedelta
        fin += timedelta(days=1)

    duracion_horas = (fin - inicio).total_seconds() / 3600

    if duracion_horas < 4:
        raise ValidationError(_('La duración del turno debe ser de al menos 4 horas'))

    if duracion_horas > 12:
        raise ValidationError(_('La duración del turno no puede exceder 12 horas'))


def validar_numero_dias_planificacion(value):
    """
    Valida el número de días de una planificación

    Args:
        value: int con el número de días
    """
    if value < 7:
        raise ValidationError(_('La planificación debe ser de al menos 7 días'))

    if value > 90:
        raise ValidationError(_('La planificación no puede exceder 90 días'))

    # Recomendar múltiplos de 7
    if value % 7 != 0:
        from django.core.exceptions import ValidationWarning
        raise ValidationWarning(
            _('Se recomienda que el número de días sea múltiplo de 7 (semanas completas)')
        )


def validar_json_restricciones(value):
    """
    Valida que las restricciones JSON tengan el formato correcto

    Args:
        value: dict o list con las restricciones
    """
    import json

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            raise ValidationError(_('El JSON de restricciones no es válido'))

    if not isinstance(value, (list, dict)):
        raise ValidationError(_('Las restricciones deben ser una lista o diccionario'))

    if isinstance(value, list):
        for restriccion in value:
            if not isinstance(restriccion, dict):
                raise ValidationError(_('Cada restricción debe ser un diccionario'))

            if 'nombre' not in restriccion:
                raise ValidationError(_('Cada restricción debe tener un campo "nombre"'))


def validar_demanda_turno(value):
    """
    Valida que la demanda por turno tenga el formato correcto

    Args:
        value: dict con la demanda por turno
    """
    import json

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            raise ValidationError(_('El JSON de demanda no es válido'))

    if not isinstance(value, dict):
        raise ValidationError(_('La demanda debe ser un diccionario'))

    turnos_validos = ['MANANA', 'TARDE', 'NOCHE']

    for turno, demanda in value.items():
        if turno not in turnos_validos:
            raise ValidationError(
                _('Turno no válido: %(turno)s. Debe ser uno de: %(validos)s'),
                params={'turno': turno, 'validos': ', '.join(turnos_validos)}
            )

        if not isinstance(demanda, dict):
            raise ValidationError(_('La demanda de cada turno debe ser un diccionario'))

        campos_requeridos = ['min', 'optimo', 'max']
        for campo in campos_requeridos:
            if campo not in demanda:
                raise ValidationError(
                    _('La demanda debe incluir los campos: %(campos)s'),
                    params={'campos': ', '.join(campos_requeridos)}
                )

            if not isinstance(demanda[campo], (int, float)) or demanda[campo] < 0:
                raise ValidationError(
                    _('El campo %(campo)s debe ser un número positivo'),
                    params={'campo': campo}
                )

        # Validar coherencia
        if not (demanda['min'] <= demanda['optimo'] <= demanda['max']):
            raise ValidationError(
                _('Debe cumplirse: mínimo ≤ óptimo ≤ máximo para el turno %(turno)s'),
                params={'turno': turno}
            )


def validar_preferencias_enfermera(value):
    """
    Valida que las preferencias de enfermera tengan el formato correcto

    Args:
        value: dict con las preferencias
    """
    import json

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            raise ValidationError(_('El JSON de preferencias no es válido'))

    if not isinstance(value, dict):
        raise ValidationError(_('Las preferencias deben ser un diccionario'))

    # Validar turnos preferidos
    if 'turnos_preferidos' in value:
        turnos = value['turnos_preferidos']
        if not isinstance(turnos, list):
            raise ValidationError(_('turnos_preferidos debe ser una lista'))

        turnos_validos = ['MANANA', 'TARDE', 'NOCHE']
        for turno in turnos:
            if turno not in turnos_validos:
                raise ValidationError(
                    _('Turno preferido no válido: %(turno)s'),
                    params={'turno': turno}
                )

    # Validar días libres preferidos
    if 'dias_libres_preferidos' in value:
        dias = value['dias_libres_preferidos']
        if not isinstance(dias, list):
            raise ValidationError(_('dias_libres_preferidos debe ser una lista'))

        dias_validos = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES', 'SABADO', 'DOMINGO']
        for dia in dias:
            if dia not in dias_validos:
                raise ValidationError(
                    _('Día no válido: %(dia)s'),
                    params={'dia': dia}
                )


def validar_telefono(value):
    """
    Valida formato de teléfono español

    Args:
        value: String con el teléfono
    """
    if not value:
        return

    # Limpiar espacios y caracteres especiales
    value_clean = re.sub(r'[\s\-\(\)]', '', value)

    # Patrones válidos
    patterns = [
        r'^\+34\d{9}$',  # +34 seguido de 9 dígitos
        r'^34\d{9}$',  # 34 seguido de 9 dígitos
        r'^\d{9}$',  # 9 dígitos
    ]

    if not any(re.match(pattern, value_clean) for pattern in patterns):
        raise ValidationError(
            _('El teléfono debe tener formato español válido (ej: +34 600 000 000 o 600000000)')
        )


def validar_seed(value):
    """
    Valida que la semilla aleatoria esté en el rango correcto

    Args:
        value: int con la semilla
    """
    if value is not None:
        if not isinstance(value, int):
            raise ValidationError(_('La semilla debe ser un número entero'))

        if value < 0 or value > 2 ** 31 - 1:
            raise ValidationError(_('La semilla debe estar entre 0 y 2147483647'))


def validar_tiempo_maximo(value):
    """
    Valida el tiempo máximo de ejecución

    Args:
        value: int con los segundos
    """
    if value < 10:
        raise ValidationError(_('El tiempo mínimo de ejecución es 10 segundos'))

    if value > 600:
        raise ValidationError(_('El tiempo máximo de ejecución es 600 segundos (10 minutos)'))


def validar_num_trabajadores(value):
    """
    Valida el número de trabajadores paralelos

    Args:
        value: int con el número de trabajadores
    """
    if value < 1:
        raise ValidationError(_('Debe haber al menos 1 trabajador'))

    if value > 8:
        raise ValidationError(_('El número máximo de trabajadores es 8'))

    # Advertir si es mayor que el número de CPUs
    import multiprocessing
    num_cpus = multiprocessing.cpu_count()

    if value > num_cpus:
        from django.core.exceptions import ValidationWarning
        raise ValidationWarning(
            _('El número de trabajadores (%(value)s) es mayor que el número de CPUs disponibles (%(cpus)s)'),
            params={'value': value, 'cpus': num_cpus}
        )

"""
TURNOS_EXTRAS.PY - Filtros y Tags Personalizados para Templates
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
from datetime import datetime
import json

register = template.Library()


# ============================================
# FILTROS DE DICCIONARIOS Y LISTAS
# ============================================

@register.filter
def get_item(dictionary, key):
    """
    Obtiene un item de un diccionario
    Uso: {{ mi_dict|get_item:"clave" }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def get_attr(obj, attr_name):
    """
    Obtiene un atributo de un objeto dinámicamente
    Uso: {{ objeto|get_attr:"nombre_atributo" }}
    """
    try:
        return getattr(obj, attr_name)
    except (AttributeError, TypeError):
        return None


@register.filter
def dict_key(dictionary, key):
    """
    Acceso a diccionario por clave (alternativa a get_item)
    """
    return dictionary.get(key) if isinstance(dictionary, dict) else None


@register.filter
def in_list(value, list_items):
    """
    Verifica si un valor está en una lista
    Uso: {% if enfermera.id|in_list:enfermeras_activas %}
    """
    if isinstance(list_items, str):
        list_items = list_items.split(',')
    return value in list_items


@register.filter
def make_list(value):
    """
    Convierte un número en un rango iterable
    Uso: {% for i in 10|make_list %}
    """
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return []


@register.filter
def split(value, separator=','):
    """
    Divide una cadena en lista
    Uso: {{ "a,b,c"|split:"," }}
    """
    if not value:
        return []
    return value.split(separator)


# ============================================
# FILTROS DE FORMATO
# ============================================

@register.filter
def format_number(value, decimals=0):
    """
    Formatea un número con separadores y decimales
    Uso: {{ 1234567.89|format_number:2 }} → 1.234.567,89
    """
    try:
        value = float(value)
        if decimals == 0:
            return f"{int(value):,}".replace(',', '.')
        else:
            formatted = f"{value:,.{decimals}f}"
            return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return value


@register.filter
def replace_underscores(value):
    """
    Reemplaza guiones bajos por espacios
    Uso: {{ "un_turno_por_dia"|replace_underscores }} → un turno por dia
    """
    if value:
        return str(value).replace('_', ' ')
    return value


@register.filter
def format_percentage(value, decimals=1):
    """
    Formatea un número como porcentaje
    Uso: {{ 0.567|format_percentage:1 }} → 56.7%
    """
    try:
        value = float(value) * 100
        return f"{value:.{decimals}f}%"
    except (ValueError, TypeError):
        return value


@register.filter
def format_duration(seconds):
    """
    Formatea duración en segundos a formato legible
    Uso: {{ 3665|format_duration }} → 1h 1m 5s
    """
    try:
        seconds = int(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return ' '.join(parts)
    except (ValueError, TypeError):
        return seconds


@register.filter
def format_time(value):
    """
    Formatea un objeto time a string
    Uso: {{ turno.hora_inicio|format_time }} → 07:00
    """
    try:
        if hasattr(value, 'strftime'):
            return value.strftime('%H:%M')
        return str(value)
    except:
        return value


@register.filter
def format_date_es(value, format_type='short'):
    """
    Formatea fecha en español
    Uso: {{ fecha|format_date_es:"long" }}
    """
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)

        if format_type == 'short':
            return value.strftime('%d/%m/%Y')
        elif format_type == 'long':
            meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
            return f"{value.day} de {meses[value.month - 1]} de {value.year}"
        elif format_type == 'full':
            dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
            meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
            dia_semana = dias[value.weekday()]
            return f"{dia_semana}, {value.day} de {meses[value.month - 1]} de {value.year}"
        else:
            return value.strftime('%d/%m/%Y')
    except:
        return value


@register.filter
def time_ago(value):
    """
    Muestra tiempo transcurrido (ej: hace 2 horas)
    Uso: {{ fecha|time_ago }}
    """
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)

        now = timezone.now()
        diff = now - value

        seconds = diff.total_seconds()

        if seconds < 60:
            return "hace un momento"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"hace {minutes} minuto{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"hace {hours} hora{'s' if hours != 1 else ''}"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"hace {days} día{'s' if days != 1 else ''}"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f"hace {weeks} semana{'s' if weeks != 1 else ''}"
        elif seconds < 31536000:
            months = int(seconds / 2592000)
            return f"hace {months} mes{'es' if months != 1 else ''}"
        else:
            years = int(seconds / 31536000)
            return f"hace {years} año{'s' if years != 1 else ''}"
    except:
        return value


# ============================================
# FILTROS DE CADENAS
# ============================================

@register.filter
def replace(value, arg):
    """
    Reemplaza un substring en una cadena.
    Uso: {{ "hola_mundo"|replace:"_, " }}
    """
    if isinstance(arg, str):
        old, new = arg.split(',')
        return value.replace(old, new)
    return value

@register.filter
def truncate_chars_middle(value, length):
    """
    Trunca texto por el medio con ...
    Uso: {{ "texto muy largo"|truncate_chars_middle:15 }} → texto...largo
    """
    try:
        length = int(length)
        if len(value) <= length:
            return value
        half = (length - 3) // 2
        return f"{value[:half]}...{value[-half:]}"
    except:
        return value


@register.filter
def initials(value):
    """
    Obtiene las iniciales de un nombre
    Uso: {{ "Juan Pérez López"|initials }} → JPL
    """
    try:
        words = value.strip().split()
        return ''.join(word[0].upper() for word in words if word)
    except:
        return value


@register.filter
def capitalize_first(value):
    """
    Capitaliza solo la primera letra
    """
    if not value:
        return value
    return value[0].upper() + value[1:].lower()


@register.filter
def remove_spaces(value):
    """
    Elimina todos los espacios
    """
    return value.replace(' ', '') if value else value


@register.filter
def slugify_custom(value):
    """
    Convierte texto a slug personalizado
    """
    import re
    value = str(value).lower()
    value = re.sub(r'[àáâãäå]', 'a', value)
    value = re.sub(r'[èéêë]', 'e', value)
    value = re.sub(r'[ìíîï]', 'i', value)
    value = re.sub(r'[òóôõö]', 'o', value)
    value = re.sub(r'[ùúûü]', 'u', value)
    value = re.sub(r'[ñ]', 'n', value)
    value = re.sub(r'[^a-z0-9\s-]', '', value)
    value = re.sub(r'[\s-]+', '-', value)
    return value.strip('-')


# ============================================
# FILTROS MATEMÁTICOS
# ============================================

@register.filter
def multiply(value, arg):
    """
    Multiplica dos valores
    Uso: {{ 5|multiply:3 }} → 15
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """
    Divide dos valores
    Uso: {{ 10|divide:2 }} → 5
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def percentage_of(value, total):
    """
    Calcula porcentaje de un valor respecto al total
    Uso: {{ 25|percentage_of:100 }} → 25
    """
    try:
        return (float(value) / float(total)) * 100 if total != 0 else 0
    except (ValueError, TypeError):
        return 0


@register.filter
def abs_value(value):
    """
    Valor absoluto
    """
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value


@register.filter
def round_number(value, decimals=0):
    """
    Redondea un número
    """
    try:
        return round(float(value), int(decimals))
    except (ValueError, TypeError):
        return value


# ============================================
# FILTROS DE ESTADOS Y BADGES
# ============================================

@register.filter
def estado_badge(estado):
    """
    Genera un badge HTML para estados
    Uso: {{ ejecucion.estado|estado_badge }}
    """
    badges = {
        'PENDIENTE': 'warning',
        'PROCESANDO': 'info',
        'COMPLETADA': 'success',
        'ERROR': 'danger',
        'CANCELADA': 'secondary'
    }

    iconos = {
        'PENDIENTE': 'clock',
        'PROCESANDO': 'spinner fa-spin',
        'COMPLETADA': 'check-circle',
        'ERROR': 'times-circle',
        'CANCELADA': 'ban'
    }

    badge_class = badges.get(estado, 'secondary')
    icono = iconos.get(estado, 'question')

    html = f'''
        <span class="badge bg-{badge_class}">
            <i class="fas fa-{icono}"></i> {estado}
        </span>
    '''
    return mark_safe(html)


@register.filter
def turno_badge(turno):
    """
    Genera un badge para tipos de turno
    """
    colores = {
        'MAÑANA': 'warning',
        'TARDE': 'info',
        'NOCHE': 'dark'
    }

    iconos = {
        'MAÑANA': 'sun',
        'TARDE': 'cloud-sun',
        'NOCHE': 'moon'
    }

    color = colores.get(turno, 'secondary')
    icono = iconos.get(turno, 'clock')

    html = f'''
        <span class="badge bg-{color}">
            <i class="fas fa-{icono}"></i> {turno}
        </span>
    '''
    return mark_safe(html)


@register.filter
def activo_badge(activo):
    """
    Genera badge para estado activo/inactivo
    """
    if activo:
        html = '<span class="badge bg-success"><i class="fas fa-check"></i> Activo</span>'
    else:
        html = '<span class="badge bg-secondary"><i class="fas fa-times"></i> Inactivo</span>'
    return mark_safe(html)


# ============================================
# FILTROS DE COLORES Y ESTILOS
# ============================================

@register.filter
def color_from_string(value):
    """
    Genera un color consistente desde un string
    """
    hash_value = sum(ord(c) for c in str(value))
    colors = [
        '#667eea', '#764ba2', '#f093fb', '#4facfe',
        '#43e97b', '#fa709a', '#fee140', '#30cfd0'
    ]
    return colors[hash_value % len(colors)]


@register.filter
def progress_color(percentage):
    """
    Determina color según porcentaje
    """
    try:
        pct = float(percentage)
        if pct < 25:
            return 'danger'
        elif pct < 50:
            return 'warning'
        elif pct < 75:
            return 'info'
        else:
            return 'success'
    except:
        return 'secondary'


# ============================================
# FILTROS DE JSON
# ============================================

@register.filter
def jsonify(value):
    """
    Convierte un objeto Python a JSON
    Uso: {{ mi_dict|jsonify }}
    """
    try:
        return mark_safe(json.dumps(value))
    except:
        return '{}'


@register.filter
def parse_json(value):
    """
    Parsea un string JSON a objeto Python
    """
    try:
        return json.loads(value)
    except:
        return None


# ============================================
# FILTROS BOOLEANOS
# ============================================

@register.filter
def is_weekend(date):
    """
    Verifica si una fecha es fin de semana
    """
    try:
        if isinstance(date, str):
            date = datetime.fromisoformat(date)
        return date.weekday() in [5, 6]  # Sábado y Domingo
    except:
        return False


@register.filter
def is_today(date):
    """
    Verifica si una fecha es hoy
    """
    try:
        if isinstance(date, str):
            date = datetime.fromisoformat(date).date()
        elif hasattr(date, 'date'):
            date = date.date()
        return date == timezone.now().date()
    except:
        return False


@register.filter
def is_past(date):
    """
    Verifica si una fecha es pasada
    """
    try:
        if isinstance(date, str):
            date = datetime.fromisoformat(date)
        return date < timezone.now()
    except:
        return False


# ============================================
# FILTROS DE VALIDACIÓN
# ============================================

@register.filter
def is_empty(value):
    """
    Verifica si un valor está vacío
    """
    if value is None:
        return True
    if isinstance(value, (list, dict, str)):
        return len(value) == 0
    return False


@register.filter
def is_number(value):
    """
    Verifica si un valor es numérico
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


# ============================================
# TAGS PERSONALIZADOS
# ============================================

@register.simple_tag
def get_verbose_name(instance, field_name):
    """
    Obtiene el verbose_name de un campo del modelo
    Uso: {% get_verbose_name objeto "campo" %}
    """
    try:
        return instance._meta.get_field(field_name).verbose_name
    except:
        return field_name


@register.simple_tag
def query_string(request, **kwargs):
    """
    Genera query string preservando parámetros existentes
    Uso: {% query_string request page=2 %}
    """
    query_dict = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            query_dict.pop(key, None)
        else:
            query_dict[key] = value
    return query_dict.urlencode()


@register.simple_tag
def settings_value(name):
    """
    Obtiene un valor de settings
    Uso: {% settings_value "DEBUG" %}
    """
    from django.conf import settings
    return getattr(settings, name, None)


@register.simple_tag(takes_context=True)
def active_nav(context, url_name):
    """
    Añade clase 'active' si la URL coincide
    Uso: <li class="{% active_nav 'dashboard' %}">
    """
    request = context.get('request')
    if request and request.resolver_match:
        if request.resolver_match.url_name == url_name:
            return 'active'
    return ''


@register.simple_tag
def icon_for_file(filename):
    """
    Devuelve icono según extensión de archivo
    """
    extension = filename.split('.')[-1].lower()
    icons = {
        'pdf': 'fa-file-pdf text-danger',
        'doc': 'fa-file-word text-primary',
        'docx': 'fa-file-word text-primary',
        'xls': 'fa-file-excel text-success',
        'xlsx': 'fa-file-excel text-success',
        'csv': 'fa-file-csv text-success',
        'zip': 'fa-file-archive text-warning',
        'jpg': 'fa-file-image text-info',
        'jpeg': 'fa-file-image text-info',
        'png': 'fa-file-image text-info',
        'gif': 'fa-file-image text-info',
    }
    return icons.get(extension, 'fa-file text-secondary')


# ============================================
# INCLUSION TAGS
# ============================================

@register.inclusion_tag('turnos/components/alert.html')
def alert(message, type='info', dismissible=True):
    """
    Renderiza un componente de alerta
    Uso: {% alert "Mensaje" type="success" %}
    """
    return {
        'message': message,
        'type': type,
        'dismissible': dismissible
    }


@register.inclusion_tag('turnos/components/loading.html')
def loading_spinner(text='Cargando...'):
    """
    Renderiza un spinner de carga
    Uso: {% loading_spinner "Procesando..." %}
    """
    return {
        'text': text
    }


# ============================================
# FILTROS DE RESTRICCIONES
# ============================================

@register.filter
def restriccion_icon(restriccion_nombre):
    """
    Devuelve icono para tipo de restricción
    """
    iconos = {
        'cobertura_minima': 'fa-users',
        'cobertura_maxima': 'fa-user-minus',
        'un_turno_por_dia': 'fa-clock',
        'descanso_minimo': 'fa-bed',
        'horas_semanales_max': 'fa-calendar-week',
        'horas_semanales_min': 'fa-calendar-check',
        'turnos_consecutivos_max': 'fa-calendar-days',
        'incompatibilidades': 'fa-user-slash',
        'disponibilidad_parcial': 'fa-user-clock',
        'dias_libres_obligatorios': 'fa-calendar-xmark',
        'dias_libres_minimos_semana': 'fa-umbrella-beach',
        'turnos_nocturnos_consecutivos_max': 'fa-moon',
        'fines_semana_max': 'fa-calendar-plus',
    }
    return iconos.get(restriccion_nombre, 'fa-cog')


@register.filter
def peso_label(peso):
    """
    Genera label descriptivo para peso de restricción
    """
    try:
        peso = float(peso)
        if peso < 2:
            return 'Baja'
        elif peso < 5:
            return 'Media'
        elif peso < 8:
            return 'Alta'
        else:
            return 'Crítica'
    except:
        return 'Media'


# ============================================
# FILTROS DE OPTIMIZACIÓN
# ============================================

@register.filter
def cache_buster(value):
    """
    Añade timestamp para evitar caché
    Uso: {{ "/static/css/style.css"|cache_buster }}
    """
    import time
    return f"{value}?v={int(time.time())}"


@register.filter
def activo_badge(value):
    if value:
        return mark_safe('<span class="badge bg-success">Activa</span>')
    return mark_safe('<span class="badge bg-secondary">Inactiva</span>')


@register.filter
def estado_badge(value):
    colors = {
        'PENDIENTE': 'secondary',
        'PROCESANDO': 'warning',
        'COMPLETADA': 'success',
        'ERROR': 'danger'
    }
    color = colors.get(value, 'secondary')
    return mark_safe(f'<span class="badge bg-{color}">{value}</span>')


@register.filter
def format_duration(seconds):
    if seconds is None:
        return '-'
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f'{minutes}m {secs}s'


@register.filter
def format_json_params(params):
    """Formatea parámetros JSON para visualización"""
    if not params:
        return '-'

    if isinstance(params, dict):
        # Formatear diccionario como "key: value, key2: value2"
        items = []
        for key, value in params.items():
            items.append(f'{key}: {value}')
        return ', '.join(items)

    return str(params)


@register.filter
def jsonify(value):
    """Convierte a JSON formateado"""
    if not value:
        return '-'
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except:
        return str(value)


@register.filter
def get_item(dictionary, key):
    """Obtiene un item del diccionario"""
    if not dictionary:
        return None
    return dictionary.get(key)


@register.filter
def multiply(value, arg):
    """Multiplica dos valores"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


# ============================================
# FILTRO PARA PATRONES DE TURNOS (JSON)
# ============================================

@register.filter(name='to_json')
def to_json(value):
    """
    Convierte un valor Python a JSON válido para JavaScript.
    Maneja listas, dicts, strings y None.
    Uso: {{ form.patrones_turnos_json.value|to_json }}
    """
    if value is None or value == '':
        return '[]'

    # Si ya es un string, intentar parsearlo para validar
    if isinstance(value, str):
        try:
            # Validar que sea JSON válido
            parsed = json.loads(value)
            # Devolver el string tal cual (ya es JSON válido)
            return value
        except json.JSONDecodeError:
            # Si no es JSON válido, devolver lista vacía
            return '[]'

    # Si es lista o dict, convertir a JSON
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)

    # Fallback
    return '[]'

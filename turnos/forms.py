"""
Forms for turnos app
"""
import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import (
    Enfermera, TipoTurno, ConfiguracionPlanificacion, PatronTurnos
)


class EnfermeraForm(forms.ModelForm):
    """Form para crear/editar enfermeras"""

    class Meta:
        model = Enfermera
        fields = ['nombre', 'email', 'telefono', 'dni', 'activa', 'preferencias', 'notas']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+34 600 000 000'
            }),
            'dni': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '12345678A'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'preferencias': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Preferencias de turnos, días libres, etc.'
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales'
            }),
        }

    def clean_email(self):
        """Valida que el email sea único"""
        email = self.cleaned_data.get('email')
        if email:
            qs = Enfermera.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_('Ya existe una enfermera con este email.'))
        return email

    def clean_dni(self):
        """Valida formato de DNI español"""
        dni = self.cleaned_data.get('dni')
        if dni:
            dni = dni.upper().strip()
            if len(dni) != 9:
                raise ValidationError(_('El DNI debe tener 9 caracteres.'))
            if not dni[:-1].isdigit() or not dni[-1].isalpha():
                raise ValidationError(_('Formato de DNI inválido (8 dígitos + 1 letra).'))
        return dni


class TipoTurnoForm(forms.ModelForm):
    """Form para crear/editar tipos de turno"""

    class Meta:
        model = TipoTurno
        fields = ['nombre', 'codigo_corto', 'hora_inicio', 'hora_fin', 'descripcion', 'es_incidencia', 'es_sustituto_libre', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Mañana, Tarde, Noche, Libre, Descanso'
            }),
            'codigo_corto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: M, T, N, L, D',
                'maxlength': '5'
            }),
            'hora_inicio': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'hora_fin': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'es_incidencia': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'es_sustituto_libre': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean(self):
        """Valida que no haya solapamiento de horas"""
        cleaned_data = super().clean()
        es_incidencia = cleaned_data.get('es_incidencia', False)
        es_sustituto_libre = cleaned_data.get('es_sustituto_libre', False)
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fin = cleaned_data.get('hora_fin')
        codigo_corto = cleaned_data.get('codigo_corto')

        # Los sustitutos de libre no deben tener horario
        if es_sustituto_libre:
            if hora_inicio or hora_fin:
                raise ValidationError(
                    _('Los sustitutos de Libre no deben tener horario específico.')
                )
            if es_incidencia:
                raise ValidationError(
                    _('Los sustitutos de Libre deben ser turnos regulares, no incidencias.')
                )

        # Los turnos regulares (no incidencia, no sustituto) deben tener horario
        if not es_incidencia and not es_sustituto_libre:
            if not hora_inicio or not hora_fin:
                raise ValidationError(
                    _('Los turnos regulares deben tener hora de inicio y fin definidas.')
                )

            # Calcular duración
            from datetime import datetime, timedelta
            inicio = datetime.combine(datetime.today(), hora_inicio)
            fin = datetime.combine(datetime.today(), hora_fin)

            if fin < inicio:
                # El turno cruza medianoche
                fin += timedelta(days=1)

            duracion = (fin - inicio).total_seconds() / 3600

            if duracion < 4:
                raise ValidationError(_('La duración del turno debe ser de al menos 4 horas.'))
            if duracion > 12:
                raise ValidationError(_('La duración del turno no puede exceder 12 horas.'))

        # El código corto es obligatorio
        if not codigo_corto:
            raise ValidationError(_('El código corto es obligatorio.'))

        return cleaned_data


class ConfiguracionPlanificacionForm(forms.ModelForm):
    """Form para crear/editar configuraciones de planificación"""

    # ✅ CAMPO PATRONES_TURNOS_JSON
    patrones_turnos_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="JSON con patrones de turnos (opcional)"
    )

    class Meta:
        model = ConfiguracionPlanificacion
        fields = [
            'nombre', 'descripcion', 'activa', 'num_dias', 'fecha_inicio',
            'horas_semanales', 'horas_mensuales', 'horas_anuales',
            'horas_semanales_globales',
            'enfermeras', 'turnos', 'demanda_por_turno',
            'restricciones_duras', 'restricciones_blandas', 'patrones_turnos_json',
            'num_trabajadores', 'tiempo_maximo_segundos', 'seed'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la configuración'}),
            'descripcion': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción de la configuración'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'num_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': 7, 'max': 365}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horas_semanales': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 80}),
            'horas_mensuales': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 300}),
            'horas_anuales': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 2500}),
            'horas_semanales_globales': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5000, 'placeholder': 'Opcional'}),
            'enfermeras': forms.CheckboxSelectMultiple(),
            'turnos': forms.CheckboxSelectMultiple(),
            'demanda_por_turno': forms.HiddenInput(),
            'restricciones_duras': forms.HiddenInput(),
            'restricciones_blandas': forms.HiddenInput(),
            'patrones_turnos_json': forms.HiddenInput(),
            'num_trabajadores': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
            'tiempo_maximo_segundos': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 600}),
            'seed': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Excluir de la selección tipos que no son asignables como turnos de trabajo
        from turnos.models import TipoTurno
        self.fields['turnos'].queryset = TipoTurno.objects.filter(
            activo=True,
            es_sustituto_libre=False,
            es_incidencia=False,
        )

    def clean_num_dias(self):
        """Valida el número de días"""
        num_dias = self.cleaned_data.get('num_dias')
        if num_dias and (num_dias < 7 or num_dias > 365):
            raise ValidationError(_('El número de días debe estar entre 7 y 365.'))
        return num_dias

    def clean_enfermeras(self):
        """Valida que haya enfermeras seleccionadas"""
        enfermeras = self.cleaned_data.get('enfermeras')
        if not enfermeras or enfermeras.count() < 2:
            raise ValidationError(_('Debe seleccionar al menos 2 enfermeras.'))
        return enfermeras

    def clean_turnos(self):
        """Valida que haya turnos seleccionados"""
        turnos = self.cleaned_data.get('turnos')
        if not turnos or turnos.count() < 1:
            raise ValidationError(_('Debe seleccionar al menos 1 tipo de turno.'))
        return turnos

    def clean_demanda_por_turno(self):
        """Valida JSON de demanda - maneja tanto string como dict"""
        data = self.cleaned_data.get('demanda_por_turno', '{}')

        if isinstance(data, dict):
            return data

        if not data or (isinstance(data, str) and data.strip() == ''):
            return {}

        try:
            demanda = json.loads(data)
            if not isinstance(demanda, dict):
                raise ValidationError("demanda_por_turno debe ser un diccionario")
            return demanda
        except json.JSONDecodeError as e:
            raise ValidationError(f"JSON inválido en demanda_por_turno: {e}")

    def clean_restricciones_duras(self):
        """Valida JSON de restricciones duras - maneja tanto string como list"""
        data = self.cleaned_data.get('restricciones_duras', '[]')

        if isinstance(data, list):
            return data

        if not data or (isinstance(data, str) and data.strip() == ''):
            return []

        try:
            restricciones = json.loads(data)
            if not isinstance(restricciones, list):
                raise ValidationError("restricciones_duras debe ser una lista")
            return restricciones
        except json.JSONDecodeError as e:
            raise ValidationError(f"JSON inválido en restricciones_duras: {e}")

    def clean_restricciones_blandas(self):
        """Valida JSON de restricciones blandas - maneja tanto string como list"""
        data = self.cleaned_data.get('restricciones_blandas', '[]')

        if isinstance(data, list):
            return data

        if not data or (isinstance(data, str) and data.strip() == ''):
            return []

        try:
            restricciones = json.loads(data)
            if not isinstance(restricciones, list):
                raise ValidationError("restricciones_blandas debe ser una lista")
            return restricciones
        except json.JSONDecodeError as e:
            raise ValidationError(f"JSON inválido en restricciones_blandas: {e}")

    def clean_patrones_turnos_json(self):
        """Validar JSON de patrones de turnos (OPCIONAL) - maneja tanto string como list"""
        data = self.cleaned_data.get('patrones_turnos_json', '[]')

        if isinstance(data, list):
            for i, patron in enumerate(data):
                if not isinstance(patron, dict):
                    raise ValidationError(f"El patrón {i + 1} debe ser un diccionario")
                if 'tipo' not in patron:
                    raise ValidationError(f"El patrón {i + 1} debe tener el campo 'tipo'")
                if 'configuracion' not in patron:
                    raise ValidationError(f"El patrón {i + 1} debe tener el campo 'configuracion'")
                if not isinstance(patron.get('configuracion'), dict):
                    raise ValidationError(f"El patrón {i + 1}: 'configuracion' debe ser un diccionario")
            return data

        if not data or (isinstance(data, str) and (data.strip() == '' or data.strip() == '[]')):
            return []

        try:
            patrones = json.loads(data)

            if not isinstance(patrones, list):
                raise ValidationError("patrones_turnos_json debe ser una lista")

            for i, patron in enumerate(patrones):
                if not isinstance(patron, dict):
                    raise ValidationError(f"El patrón {i + 1} debe ser un diccionario")
                if 'tipo' not in patron:
                    raise ValidationError(f"El patrón {i + 1} debe tener el campo 'tipo'")
                if 'configuracion' not in patron:
                    raise ValidationError(f"El patrón {i + 1} debe tener el campo 'configuracion'")
                if not isinstance(patron.get('configuracion'), dict):
                    raise ValidationError(f"El patrón {i + 1}: 'configuracion' debe ser un diccionario")

            return patrones

        except json.JSONDecodeError as e:
            raise ValidationError(f"JSON inválido en patrones_turnos_json: {e}")
        except Exception as e:
            raise ValidationError(f"Error validando patrones_turnos_json: {e}")


class ConfiguracionWizardStep1Form(forms.Form):
    """Formulario para el paso 1 del wizard: Datos básicos"""

    nombre = forms.CharField(
        max_length=200,
        label=_('Nombre'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Planificación Enero 2025'
        })
    )

    descripcion = forms.CharField(
        required=False,
        label=_('Descripción'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        })
    )

    num_dias = forms.IntegerField(
        min_value=7,
        max_value=365,
        initial=14,
        label=_('Número de días'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )

    fecha_inicio = forms.DateField(
        label=_('Fecha de inicio'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    enfermeras = forms.ModelMultipleChoiceField(
        queryset=Enfermera.objects.filter(activa=True),
        label=_('Enfermeras'),
        widget=forms.CheckboxSelectMultiple()
    )

    turnos = forms.ModelMultipleChoiceField(
        queryset=TipoTurno.objects.filter(activo=True, es_sustituto_libre=False, es_incidencia=False),
        label=_('Tipos de turno'),
        widget=forms.CheckboxSelectMultiple()
    )

    def clean_enfermeras(self):
        """Valida que haya enfermeras seleccionadas"""
        enfermeras = self.cleaned_data.get('enfermeras')
        if not enfermeras or enfermeras.count() < 2:
            raise ValidationError(_('Debe seleccionar al menos 2 enfermeras.'))
        return enfermeras

    def clean_turnos(self):
        """Valida que haya turnos seleccionados"""
        turnos = self.cleaned_data.get('turnos')
        if not turnos or turnos.count() < 1:
            raise ValidationError(_('Debe seleccionar al menos 1 tipo de turno.'))
        return turnos


class ConfiguracionWizardStep2DemandaForm(forms.Form):
    """Formulario para el paso 2 del wizard: Demanda por turno"""

    demanda_por_turno = forms.CharField(
        required=False,
        label=_('Demanda por turno (JSON)'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Ej: {\"MANANA\": {\"min\": 2, \"optimo\": 3, \"max\": 5}}'
        }),
        help_text=_('Opcional. Introduce la demanda esperada por tipo de turno en formato JSON.')
    )

    def clean_demanda_por_turno(self):
        data = self.cleaned_data.get('demanda_por_turno', '').strip()
        if not data:
            return {}
        try:
            parsed_data = json.loads(data)
            if not isinstance(parsed_data, dict):
                raise ValidationError(_('El JSON de demanda debe ser un objeto (diccionario).'))
            return parsed_data
        except json.JSONDecodeError:
            raise ValidationError(_('Formato JSON inválido para la demanda por turno.'))


class ConfiguracionWizardStep3DurasForm(forms.Form):
    """Formulario para el paso 3 del wizard: Restricciones duras"""

    restricciones_duras = forms.CharField(
        required=False,
        label=_('Restricciones duras (JSON)'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Ej: [{\"nombre\": \"un_turno_por_dia\"}]'
        }),
        help_text=_('Opcional. Introduce las restricciones duras en formato JSON.')
    )

    def clean_restricciones_duras(self):
        data = self.cleaned_data.get('restricciones_duras', '').strip()
        if not data:
            return []
        try:
            parsed_data = json.loads(data)
            if not isinstance(parsed_data, list):
                raise ValidationError(_('El JSON de restricciones duras debe ser una lista (array).'))
            return parsed_data
        except json.JSONDecodeError:
            raise ValidationError(_('Formato JSON inválido para las restricciones duras.'))


class ConfiguracionWizardStep4BlandasForm(forms.Form):
    """Formulario para el paso 4 del wizard: Restricciones blandas y Solver"""

    restricciones_blandas = forms.CharField(
        required=False,
        label=_('Restricciones blandas (JSON)'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Ej: [{\"nombre\": \"equidad_turnos\", \"peso\": 10.0}]'
        }),
        help_text=_('Opcional. Introduce las restricciones blandas en formato JSON.')
    )

    patrones_turnos = forms.ModelMultipleChoiceField(
        queryset=PatronTurnos.objects.filter(activo=True),
        required=False,
        label=_('Patrones de Turnos'),
        widget=forms.CheckboxSelectMultiple(),
        help_text=_('Selecciona los patrones de turnos a aplicar (ej. descansos, secuencias, etc.)')
    )

    num_trabajadores = forms.IntegerField(
        min_value=1,
        max_value=8,
        initial=4,
        label=_('Número de trabajadores paralelos'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        }),
        help_text=_('Número de procesos o hilos a usar para resolver la planificación.')
    )

    tiempo_maximo_segundos = forms.IntegerField(
        min_value=10,
        max_value=600,
        initial=60,
        label=_('Tiempo máximo de resolución (segundos)'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        }),
        help_text=_('Tiempo máximo que el solver intentará encontrar una solución.')
    )

    seed = forms.IntegerField(
        required=False,
        label=_('Semilla aleatoria'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        }),
        help_text=_('Opcional. Un número para inicializar el generador de números aleatorios del solver. Útil para reproducibilidad.')
    )

    def clean_restricciones_blandas(self):
        data = self.cleaned_data.get('restricciones_blandas', '').strip()
        if not data:
            return []
        try:
            parsed_data = json.loads(data)
            if not isinstance(parsed_data, list):
                raise ValidationError(_('El JSON de restricciones blandas debe ser una lista (array).'))
            return parsed_data
        except json.JSONDecodeError:
            raise ValidationError(_('Formato JSON inválido para las restricciones blandas.'))


class EjecucionRapidaForm(forms.Form):
    """Formulario para ejecución rápida"""

    nombre = forms.CharField(
        max_length=200,
        label=_('Nombre'),
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )

    num_dias = forms.IntegerField(
        min_value=7,
        max_value=30,
        initial=14,
        label=_('Días a planificar'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )

    fecha_inicio = forms.DateField(
        label=_('Fecha de inicio'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    enfermeras = forms.ModelMultipleChoiceField(
        queryset=Enfermera.objects.filter(activa=True),
        label=_('Enfermeras'),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': 5
        })
    )


class FiltroEjecucionesForm(forms.Form):
    """Formulario para filtrar ejecuciones"""

    ESTADO_CHOICES = [
        ('', _('Todos')),
        ('PENDIENTE', _('Pendiente')),
        ('PROCESANDO', _('Procesando')),
        ('COMPLETADA', _('Completada')),
        ('ERROR', _('Error')),
    ]

    q = forms.CharField(
        required=False,
        label=_('Buscar'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar...'
        })
    )

    estado = forms.ChoiceField(
        required=False,
        choices=ESTADO_CHOICES,
        label=_('Estado'),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    fecha_desde = forms.DateField(
        required=False,
        label=_('Desde'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    fecha_hasta = forms.DateField(
        required=False,
        label=_('Hasta'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class ImportarEnfermerasForm(forms.Form):
    """Formulario para importar enfermeras desde Excel"""

    archivo = forms.FileField(
        label=_('Archivo Excel'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        })
    )

    sobrescribir = forms.BooleanField(
        required=False,
        initial=False,
        label=_('Sobrescribir registros existentes'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    def clean_archivo(self):
        """Valida que el archivo sea Excel"""
        archivo = self.cleaned_data.get('archivo')
        if archivo:
            if not archivo.name.endswith(('.xlsx', '.xls')):
                raise ValidationError(_('El archivo debe ser un archivo Excel (.xlsx o .xls).'))

            # Verificar tamaño (max 5MB)
            if archivo.size > 5 * 1024 * 1024:
                raise ValidationError(_('El archivo no puede superar 5MB.'))

        return archivo


# ════════════════════════════════════════════════════════════════
# FORMULARIOS EXTENDIDOS PARA RESTRICCIONES SACYL
# ════════════════════════════════════════════════════════════════

class ConfiguracionPlanificacionFormExtendida(forms.ModelForm):
    """Formulario extendido con soporte para restricciones JSON"""

    """Form para crear/editar configuraciones de planificación"""

    patrones_turnos_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="JSON con patrones de turnos (opcional)"
    )

    restricciones_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 10,
            'placeholder': '{\"restricciones_duras\": [...], \"restricciones_blandas\": [...]}'
        }),
        help_text='JSON completo con restricciones_duras y restricciones_blandas'
    )

    usar_builder = forms.BooleanField(
        required=False,
        initial=True,
        label='Usar constructor visual de restricciones',
        help_text='Marca para usar el constructor en vez de JSON raw'
    )

    class Meta:
        model = ConfiguracionPlanificacion
        fields = [
            'nombre', 'descripcion', 'activa',
            'num_dias', 'fecha_inicio',
            'horas_semanales', 'horas_mensuales', 'horas_anuales',
            'horas_semanales_globales',
            'enfermeras', 'turnos',
            'demanda_por_turno',
            'num_trabajadores', 'tiempo_maximo_segundos', 'seed'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'num_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': 7, 'max': 365}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horas_semanales': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 80}),
            'horas_mensuales': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 300}),
            'horas_anuales': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 2500}),
            'horas_semanales_globales': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5000, 'placeholder': 'Opcional'}),
            'enfermeras': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'turnos': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 3}),
            'demanda_por_turno': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 3}),
            'num_trabajadores': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
            'tiempo_maximo_segundos': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 600}),
            'seed': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Excluir de la selección tipos que no son asignables como turnos de trabajo
        from turnos.models import TipoTurno
        self.fields['turnos'].queryset = TipoTurno.objects.filter(
            activo=True,
            es_sustituto_libre=False,
            es_incidencia=False,
        )

        if self.instance and self.instance.pk:
            # ✅ Manejar restricciones_json (existente)
            rd = self.instance.restricciones_duras
            rb = self.instance.restricciones_blandas
            if rd or rb:
                data = {}
                if rd: data['restricciones_duras'] = rd if isinstance(rd, list) else []
                if rb: data['restricciones_blandas'] = rb if isinstance(rb, list) else []
                self.initial['restricciones_json'] = json.dumps(data, indent=2, ensure_ascii=False)

            # ✅ NUEVO: Manejar patrones_turnos_json
            if hasattr(self.instance, 'patrones_turnos_json'):
                patrones = self.instance.patrones_turnos_json

                # Convertir a JSON string válido para JavaScript
                if isinstance(patrones, list):
                    self.initial['patrones_turnos_json'] = json.dumps(patrones, ensure_ascii=False)
                elif isinstance(patrones, str):
                    # Si ya es string, validar que sea JSON válido
                    try:
                        json.loads(patrones)
                        self.initial['patrones_turnos_json'] = patrones
                    except json.JSONDecodeError:
                        self.initial['patrones_turnos_json'] = '[]'
                else:
                    self.initial['patrones_turnos_json'] = '[]'

        self.fields['demanda_por_turno'].help_text = 'Ejemplo: {\"MANANA\": 2, \"TARDE\": 2, \"NOCHE\": 1}'

    def clean_restricciones_json(self):
        data = self.cleaned_data.get('restricciones_json', '').strip()
        if not data: return None
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f'JSON inválido: {e}')
        if not isinstance(parsed, dict):
            raise ValidationError('El JSON debe ser un objeto/diccionario')
        if 'restricciones_duras' in parsed:
            rd = parsed['restricciones_duras']
            if not isinstance(rd, list):
                raise ValidationError('restricciones_duras debe ser un array')
            for idx, r in enumerate(rd):
                if not isinstance(r, dict):
                    raise ValidationError(f'restricciones_duras[{idx}] debe ser un objeto')
                if 'id' not in r or 'nombre' not in r:
                    raise ValidationError(f'restricciones_duras[{idx}] debe tener \"id\" y \"nombre\"')
        if 'restricciones_blandas' in parsed:
            rb = parsed['restricciones_blandas']
            if not isinstance(rb, list):
                raise ValidationError('restricciones_blandas debe ser un array')
            for idx, r in enumerate(rb):
                if not isinstance(r, dict):
                    raise ValidationError(f'restricciones_blandas[{idx}] debe ser un objeto')
                if 'id' not in r or 'nombre' not in r or 'peso' not in r:
                    raise ValidationError(f'restricciones_blandas[{idx}] debe tener \"id\", \"nombre\" y \"peso\"')
        return parsed

    def clean_demanda_por_turno(self):
        data = self.cleaned_data.get('demanda_por_turno')
        if not data: return {}
        if isinstance(data, dict): return data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if not isinstance(parsed, dict):
                    raise ValidationError('Debe ser un objeto JSON: {\"MANANA\": 2, ...}')
                return parsed
            except json.JSONDecodeError as e:
                raise ValidationError(f'JSON inválido: {e}')
        return {}

    def save(self, commit=True):
        instance = super().save(commit=False)
        restr_json = self.cleaned_data.get('restricciones_json')
        if restr_json:
            instance.restricciones_duras = restr_json.get('restricciones_duras', [])
            instance.restricciones_blandas = restr_json.get('restricciones_blandas', [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class RestriccionDuraForm(forms.Form):
    """Formulario para añadir restricción dura individual"""
    id = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RD001'}))
    nombre = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    tipo = forms.ChoiceField(
        choices=[
            ('jornada_anual', 'Jornada Anual'),
            ('descanso', 'Descanso'),
            ('cobertura', 'Cobertura'),
            ('asignacion', 'Asignación'),
            ('horario', 'Horario'),
            ('jornada_maxima', 'Jornada Máxima'),
            ('vacaciones_permisos', 'Vacaciones/Permisos'),
            ('guardia', 'Guardia')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    obligatorio = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))
    parametros = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 3}),
        help_text='JSON de parámetros: {\"minimo_horas\": 12}'
    )

    def clean_parametros(self):
        data = self.cleaned_data.get('parametros', '').strip()
        if not data: return {}
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f'JSON inválido: {e}')

    def to_dict(self):
        return {
            'id': self.cleaned_data['id'],
            'nombre': self.cleaned_data['nombre'],
            'tipo': self.cleaned_data['tipo'],
            'obligatorio': self.cleaned_data['obligatorio'],
            'descripcion': self.cleaned_data['descripcion'],
            'parametros': self.cleaned_data.get('parametros', {})
        }


class RestriccionBlandaForm(forms.Form):
    """Formulario para añadir restricción blanda individual"""
    id = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RB001'}))
    nombre = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    tipo = forms.ChoiceField(
        choices=[
            ('equidad', 'Equidad'),
            ('conciliacion', 'Conciliación'),
            ('fatiga', 'Fatiga'),
            ('organizacion', 'Organización'),
            ('preferencias', 'Preferencias'),
            ('jornada_especial', 'Jornada Especial')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    peso = forms.IntegerField(min_value=1, max_value=1000, initial=100, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))
    parametros = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 3}),
        help_text='JSON de parámetros'
    )

    def clean_parametros(self):
        data = self.cleaned_data.get('parametros', '').strip()
        if not data: return {}
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f'JSON inválido: {e}')

    def to_dict(self):
        return {
            'id': self.cleaned_data['id'],
            'nombre': self.cleaned_data['nombre'],
            'tipo': self.cleaned_data['tipo'],
            'peso': self.cleaned_data['peso'],
            'descripcion': self.cleaned_data['descripcion'],
            'parametros': self.cleaned_data.get('parametros', {})
        }


class CargarRestriccionesSACYLForm(forms.Form):
    """Formulario para cargar restricciones desde presets SACYL"""
    preset = forms.ChoiceField(
        label='Preset SACYL',
        choices=[
            ('basico', 'Básico (RD006, RD019, RD020)'),
            ('completo', 'Completo (Normativa 2025 completa)'),
            ('custom', 'Personalizado (subir JSON)')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    archivo_json = forms.FileField(
        required=False,
        label='O sube tu propio JSON',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.json'}),
        help_text='Archivo JSON con estructura SACYL'
    )

    def clean(self):
        cleaned = super().clean()
        preset = cleaned.get('preset')
        archivo = cleaned.get('archivo_json')
        if preset == 'custom' and not archivo:
            raise ValidationError('Debes subir un archivo JSON si seleccionas \"Personalizado\"')
        if archivo:
            try:
                content = archivo.read().decode('utf-8')
                parsed = json.loads(content)
                cleaned['json_data'] = parsed
                if 'restricciones_duras' not in parsed and 'restricciones_blandas' not in parsed:
                    raise ValidationError('El JSON debe contener \"restricciones_duras\" o \"restricciones_blandas\"')
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise ValidationError(f'Archivo JSON inválido: {e}')
        return cleaned

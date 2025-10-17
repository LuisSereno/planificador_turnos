"""
Forms for turnos app
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import (
    Enfermera, TipoTurno, ConfiguracionPlanificacion,
    Ejecucion, Planilla
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
        fields = ['nombre', 'hora_inicio', 'hora_fin', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.Select(attrs={
                'class': 'form-select'
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
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean(self):
        """Valida que no haya solapamiento de horas"""
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fin = cleaned_data.get('hora_fin')

        if hora_inicio and hora_fin:
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

        return cleaned_data


class ConfiguracionPlanificacionForm(forms.ModelForm):
    """Form para crear/editar configuraciones de planificación"""

    class Meta:
        model = ConfiguracionPlanificacion
        fields = [
            'nombre', 'descripcion', 'activa', 'num_dias', 'fecha_inicio',
            'enfermeras', 'turnos', 'demanda_por_turno',
            'restricciones_duras', 'restricciones_blandas',
            'num_trabajadores', 'tiempo_maximo_segundos', 'seed'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la configuración'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la configuración'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'num_dias': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 7,
                'max': 90
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'enfermeras': forms.CheckboxSelectMultiple(),
            'turnos': forms.CheckboxSelectMultiple(),
            'demanda_por_turno': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Opcional: {"MANANA": {"min": 2, "optimo": 3, "max": 5}}'
            }),
            'restricciones_duras': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Opcional: [{"nombre": "un_turno_por_dia"}]'
            }),
            'restricciones_blandas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Opcional: [{"nombre": "equidad_turnos", "peso": 10.0}]'
            }),
            'num_trabajadores': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 8
            }),
            'tiempo_maximo_segundos': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 10,
                'max': 600
            }),
            'seed': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
        }

    def clean_num_dias(self):
        """Valida el número de días"""
        num_dias = self.cleaned_data.get('num_dias')
        if num_dias and (num_dias < 7 or num_dias > 90):
            raise ValidationError(_('El número de días debe estar entre 7 y 90.'))
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

    # ELIMINADAS las validaciones obligatorias de demanda_por_turno y restricciones


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
        max_value=90,
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
        queryset=TipoTurno.objects.filter(activo=True),
        label=_('Tipos de turno'),
        widget=forms.CheckboxSelectMultiple()
    )


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

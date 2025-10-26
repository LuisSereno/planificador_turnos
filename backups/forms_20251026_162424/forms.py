# -*- coding: utf-8 -*-
from django import forms
from django.core.exceptions import ValidationError
from .models import ConfiguracionPlanificacion, Enfermera, TipoTurno
import json

class ConfiguracionPlanificacionForm(forms.ModelForm):
    """Formulario para crear/editar configuraciones con restricciones JSON"""

    # Campo de texto para cargar JSON de restricciones completo
    restricciones_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 10,
            'placeholder': '{"restricciones_duras": [...], "restricciones_blandas": [...]}'
        }),
        help_text='JSON completo con restricciones_duras y restricciones_blandas'
    )

    # O usar el builder integrado
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
            'enfermeras': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'turnos': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 3}),
            'demanda_por_turno': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 3}),
            'num_trabajadores': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
            'tiempo_maximo_segundos': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 600}),
            'seed': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prellenar restricciones_json si existe
        if self.instance and self.instance.pk:
            rd = self.instance.restricciones_duras
            rb = self.instance.restricciones_blandas
            if rd or rb:
                data = {}
                if rd: data['restricciones_duras'] = rd if isinstance(rd, list) else []
                if rb: data['restricciones_blandas'] = rb if isinstance(rb, list) else []
                self.initial['restricciones_json'] = json.dumps(data, indent=2, ensure_ascii=False)

        # Ayudas visuales
        self.fields['demanda_por_turno'].help_text = 'Ejemplo: {"MANANA": 2, "TARDE": 2, "NOCHE": 1}'

    def clean_restricciones_json(self):
        """Valida que el JSON sea correcto"""
        data = self.cleaned_data.get('restricciones_json', '').strip()
        if not data:
            return None

        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f'JSON inválido: {e}')

        # Validar estructura básica
        if not isinstance(parsed, dict):
            raise ValidationError('El JSON debe ser un objeto/diccionario')

        # Validar restricciones_duras
        if 'restricciones_duras' in parsed:
            rd = parsed['restricciones_duras']
            if not isinstance(rd, list):
                raise ValidationError('restricciones_duras debe ser un array')
            for idx, r in enumerate(rd):
                if not isinstance(r, dict):
                    raise ValidationError(f'restricciones_duras[{idx}] debe ser un objeto')
                if 'id' not in r or 'nombre' not in r:
                    raise ValidationError(f'restricciones_duras[{idx}] debe tener "id" y "nombre"')

        # Validar restricciones_blandas
        if 'restricciones_blandas' in parsed:
            rb = parsed['restricciones_blandas']
            if not isinstance(rb, list):
                raise ValidationError('restricciones_blandas debe ser un array')
            for idx, r in enumerate(rb):
                if not isinstance(r, dict):
                    raise ValidationError(f'restricciones_blandas[{idx}] debe ser un objeto')
                if 'id' not in r or 'nombre' not in r or 'peso' not in r:
                    raise ValidationError(f'restricciones_blandas[{idx}] debe tener "id", "nombre" y "peso"')

        return parsed

    def clean_demanda_por_turno(self):
        """Valida demanda_por_turno"""
        data = self.cleaned_data.get('demanda_por_turno')
        if not data:
            return {}

        if isinstance(data, dict):
            return data

        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if not isinstance(parsed, dict):
                    raise ValidationError('Debe ser un objeto JSON: {"MANANA": 2, ...}')
                return parsed
            except json.JSONDecodeError as e:
                raise ValidationError(f'JSON inválido: {e}')

        return {}

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Si se proporcionó JSON de restricciones, aplicar
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
        help_text='JSON de parámetros: {"minimo_horas": 12}'
    )

    def clean_parametros(self):
        data = self.cleaned_data.get('parametros', '').strip()
        if not data:
            return {}
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f'JSON inválido: {e}')

    def to_dict(self):
        """Convierte a diccionario para guardar en JSON"""
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
        if not data:
            return {}
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
            raise ValidationError('Debes subir un archivo JSON si seleccionas "Personalizado"')

        if archivo:
            try:
                content = archivo.read().decode('utf-8')
                parsed = json.loads(content)
                cleaned['json_data'] = parsed

                # Validar estructura
                if 'restricciones_duras' not in parsed and 'restricciones_blandas' not in parsed:
                    raise ValidationError('El JSON debe contener "restricciones_duras" o "restricciones_blandas"')
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise ValidationError(f'Archivo JSON inválido: {e}')

        return cleaned
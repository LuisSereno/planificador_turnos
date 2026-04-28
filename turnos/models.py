from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError

User = get_user_model()


class Workspace(models.Model):
    """Espacio de trabajo para aislar datos entre usuarios"""
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspaces_creados')
    usuarios = models.ManyToManyField(User, related_name='workspaces', blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Espacio de Trabajo'
        verbose_name_plural = 'Espacios de Trabajo'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.nombre


class Enfermera(models.Model):
    """Modelo para representar una enfermera"""
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='enfermeras',
        null=True,
        blank=True
    )
    nombre = models.CharField(_('Nombre'), max_length=200)
    email = models.EmailField(_('Email'), unique=True)
    telefono = models.CharField(_('Teléfono'), max_length=20, blank=True)
    dni = models.CharField(_('DNI'), max_length=20, blank=True, unique=True, null=True)
    activa = models.BooleanField(_('Activa'), default=True)
    fecha_alta = models.DateField(_('Fecha de alta'), auto_now_add=True)
    preferencias = models.JSONField(_('Preferencias'), default=dict, blank=True)
    notas = models.TextField(_('Notas'), blank=True)

    class Meta:
        verbose_name = _('Enfermera')
        verbose_name_plural = _('Enfermeras')
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse('turnos:enfermera_detalle', kwargs={'pk': self.pk})


class TipoTurno(models.Model):
    """Modelo para representar tipos de turno"""
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='tipos_turno',
        null=True,
        blank=True
    )
    NOMBRE_CHOICES = [
        ('MANANA', _('Mañana')),
        ('TARDE', _('Tarde')),
        ('NOCHE', _('Noche')),
    ]

    nombre = models.CharField(_('Nombre'), max_length=50, choices=NOMBRE_CHOICES)
    hora_inicio = models.TimeField(_('Hora de inicio'))
    hora_fin = models.TimeField(_('Hora de fin'))
    descripcion = models.TextField(_('Descripción'), blank=True)
    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _('Tipo de Turno')
        verbose_name_plural = _('Tipos de Turno')
        ordering = ['nombre']

    def __str__(self):
        return f"{self.get_nombre_display()} ({self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')})"

    @property
    def duracion_horas(self):
        """Calcula la duración del turno en horas"""
        inicio = datetime.combine(datetime.today(), self.hora_inicio)
        fin = datetime.combine(datetime.today(), self.hora_fin)

        if fin < inicio:
            fin += timedelta(days=1)

        duracion = (fin - inicio).total_seconds() / 3600
        return round(duracion, 2)

    @property
    def es_nocturno(self):
        """Determina si el turno es nocturno basado en el nombre"""
        return self.nombre == 'NOCHE'


class TipoPatron(models.TextChoices):
    """Tipos de patrones de turnos soportados"""
    SECUENCIA_OBLIGATORIA = 'SEQ', 'Secuencia Obligatoria'  # A → B → C
    DESCANSO_POST_TURNO = 'REST', 'Descanso Post-Turno'  # 2N → 3 libres
    MAX_CONSECUTIVOS = 'MAX_CONS', 'Máximo Consecutivos'  # Max 5 seguidos
    ROTACION_CICLICA = 'ROT', 'Rotación Cíclica'  # M→T→N→M→T→N
    COBERTURA_MINIMA = 'COV_MIN', 'Cobertura Mínima'  # Min 2 enfermeras/turno
    BLOQUEO_TRANSICION = 'BLOCK', 'Transición Bloqueada'  # Noche → NO → Mañana
    DISTRIBUCION_EQUITATIVA = 'EQUI', 'Distribución Equitativa'  # Igualdad de turnos


class PatronTurnos(models.Model):
    """
    Patrón genérico de turnos configurable.
    Permite definir reglas de secuencias, descansos y restricciones.
    """

    # Identificación
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(
        max_length=20,
        choices=TipoPatron.choices,
        help_text="Tipo de patrón a aplicar"
    )

    # Estado
    activo = models.BooleanField(default=True)
    es_restriccion_dura = models.BooleanField(
        default=True,
        help_text="Si es False, se penaliza pero no se prohíbe"
    )
    peso_penalizacion = models.IntegerField(
        default=100,
        help_text="Peso de penalización si no es restricción dura"
    )

    # Configuración JSON genérica
    configuracion = models.JSONField(
        default=dict,
        help_text="""
        Configuración específica del patrón. Ejemplos:

        DESCANSO_POST_TURNO: {
            "turno_tipo": "NOCHE",
            "cantidad_consecutiva": 2,
            "dias_descanso_requeridos": 3
        }

        MAX_CONSECUTIVOS: {
            "turno_tipo": "CUALQUIERA",  # o "NOCHE", "MAÑANA"
            "cantidad_maxima": 5
        }

        SECUENCIA_OBLIGATORIA: {
            "secuencia": ["MAÑANA", "TARDE", "NOCHE"],
            "ciclica": true
        }

        BLOQUEO_TRANSICION: {
            "turno_origen": "NOCHE",
            "turno_destino": "MAÑANA",
            "dias_minimos_entre": 1
        }

        COBERTURA_MINIMA: {
            "turno_tipo": "NOCHE",
            "enfermeras_minimas": 2,
            "aplicar_dias": [5, 6, 0]  # Vie, Sab, Dom (0=Lunes)
        }
        """
    )

    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Patrón de Turnos"
        verbose_name_plural = "Patrones de Turnos"
        ordering = ['-activo', 'nombre']

    def __str__(self):
        estado = "✓" if self.activo else "✗"
        tipo_str = "DURA" if self.es_restriccion_dura else f"BLANDA({self.peso_penalizacion})"
        return f"{estado} {self.nombre} [{self.get_tipo_display()}] - {tipo_str}"

    def validar_configuracion(self):
        """Valida que la configuración sea correcta según el tipo"""
        if self.tipo == TipoPatron.DESCANSO_POST_TURNO:
            required = ['turno_tipo', 'cantidad_consecutiva', 'dias_descanso_requeridos']
            return all(k in self.configuracion for k in required)

        elif self.tipo == TipoPatron.MAX_CONSECUTIVOS:
            required = ['cantidad_maxima']
            return all(k in self.configuracion for k in required)

        elif self.tipo == TipoPatron.SECUENCIA_OBLIGATORIA:
            return 'secuencia' in self.configuracion and len(self.configuracion['secuencia']) > 0

        elif self.tipo == TipoPatron.BLOQUEO_TRANSICION:
            required = ['turno_origen', 'turno_destino']
            return all(k in self.configuracion for k in required)

        elif self.tipo == TipoPatron.COBERTURA_MINIMA:
            required = ['enfermeras_minimas']
            return all(k in self.configuracion for k in required)

        return True

    def clean(self):
        """Validación al guardar"""
        if not self.validar_configuracion():
            raise ValidationError(f"Configuración inválida para tipo {self.get_tipo_display()}")


class ConfiguracionPlanificacion(models.Model):
    """Modelo para configuración de planificación"""
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='configuraciones',
        null=True,
        blank=True
    )
    nombre = models.CharField(_('Nombre'), max_length=200)
    descripcion = models.TextField(_('Descripción'), blank=True)
    activa = models.BooleanField(_('Activa'), default=True)

    # Configuración temporal
    num_dias = models.IntegerField(
        _('Número de días'),
        validators=[MinValueValidator(7), MaxValueValidator(365)]
    )
    fecha_inicio = models.DateField(_('Fecha de inicio'))

    # Enfermeras y turnos
    enfermeras = models.ManyToManyField(Enfermera, verbose_name=_('Enfermeras'))
    turnos = models.ManyToManyField(TipoTurno, verbose_name=_('Turnos'))
    # Turnos que cuentan para la regla "uno por día" (si está vacío se utilizarán todos los turnos configurados)
    turnos_por_dia = models.ManyToManyField(TipoTurno, verbose_name=_('Turnos por día'),
                                            related_name='config_turnos_por_dia', blank=True)

    # Demanda
    demanda_por_turno = models.JSONField(
        _('Demanda por turno'),
        default=dict,
        blank=True
    )

    # Restricciones
    restricciones_duras = models.JSONField(
        _('Restricciones duras'),
        default=list,
        blank=True,
        null=True
    )
    restricciones_blandas = models.JSONField(
        _('Restricciones blandas'),
        default=list,
        blank=True,
        null=True
    )

    # ✅ NUEVO: Campo JSONField para patrones dinámicos del formulario
    patrones_turnos_json = models.JSONField(
        _('Patrones de turnos (JSON)'),
        default=list,
        blank=True,
        help_text="Patrones configurados dinámicamente desde el formulario"
    )

    # ✅ CONSERVADO: Relación ManyToMany con PatronTurnos (LEGACY)
    patrones_turnos = models.ManyToManyField(
        PatronTurnos,
        blank=True,
        related_name='configuraciones',
        help_text="Patrones predefinidos en la base de datos (legacy)"
    )

    # Configuración del solver
    num_trabajadores = models.IntegerField(
        _('Número de trabajadores paralelos'),
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    tiempo_maximo_segundos = models.IntegerField(
        _('Tiempo máximo en segundos'),
        default=60,
        validators=[MinValueValidator(10), MaxValueValidator(600)]
    )
    seed = models.IntegerField(_('Semilla aleatoria'), null=True, blank=True)

    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('Creado por'))
    fecha_creacion = models.DateTimeField(_('Fecha de creación'), auto_now_add=True, editable=False)
    fecha_modificacion = models.DateTimeField(_('Fecha de modificación'), auto_now=True, editable=False)

    class Meta:
        verbose_name = _('Configuración de Planificación')
        verbose_name_plural = _('Configuraciones de Planificación')
        ordering = ['-fecha_inicio']

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse('turnos:config_detalle', kwargs={'pk': self.pk})

    def _validar_mensualidad(self):
        """Valida que la configuración sea un mes natural completo."""
        import calendar
        from django.core.exceptions import ValidationError

        if self.fecha_inicio and self.fecha_inicio.day != 1:
            raise ValidationError(
                "La fecha de inicio debe ser el primer día del mes para garantizar "
                "consistencia con el histórico mensual."
            )
        if self.fecha_inicio and self.num_dias:
            dias_mes = calendar.monthrange(
                self.fecha_inicio.year, self.fecha_inicio.month
            )[1]
            if self.num_dias != dias_mes:
                raise ValidationError(
                    f"El número de días ({self.num_dias}) no coincide con los días "
                    f"reales del mes ({dias_mes}). Las planificaciones deben ser "
                    f"mensuales completas."
                )

    def clean(self):
        """Validación al guardar mediante formularios o admin."""
        self._validar_mensualidad()

    def save(self, *args, **kwargs):
        """Sobrescribe save para validar mensualidad en creación."""
        if self._state.adding:
            self._validar_mensualidad()
        super().save(*args, **kwargs)

    def get_patrones_combinados(self):
        """
        ✅ Método helper para obtener TODOS los patrones (JSON + ManyToMany)
        PRIORIDAD: patrones_turnos_json es la fuente activa principal
        patrones_turnos (ManyToMany) es legacy y solo para compatibilidad
        """
        patrones = []

        # 1. Patrones JSON del formulario (FUENTE ACTIVA PRINCIPAL)
        if self.patrones_turnos_json:
            patrones.extend(self.patrones_turnos_json)

        # 2. Patrones de la relación ManyToMany (LEGACY - solo compatibilidad)
        for patron_obj in self.patrones_turnos.filter(activo=True):
            patrones.append({
                'tipo': patron_obj.tipo,
                'nombre': patron_obj.nombre,
                'es_restriccion_dura': patron_obj.es_restriccion_dura,
                'peso_penalizacion': patron_obj.peso_penalizacion,
                'configuracion': patron_obj.configuracion
            })

        return patrones


class Ejecucion(models.Model):
    """Modelo para representar una ejecución de planificación"""
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='ejecuciones',
        null=True,
        blank=True
    )
    ESTADO_CHOICES = [
        ('PENDIENTE', _('Pendiente')),
        ('PROCESANDO', _('Procesando')),
        ('COMPLETADA', _('Completada')),
        ('INVIABLE', _('Inviable')),
        ('ERROR', _('Error')),
    ]

    configuracion = models.ForeignKey(
        ConfiguracionPlanificacion,
        on_delete=models.CASCADE,
        related_name='ejecuciones',
        verbose_name=_('Configuración')
    )
    estado = models.CharField(_('Estado'), max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    fecha_inicio = models.DateTimeField(_('Fecha de inicio'), auto_now_add=True)
    fecha_fin = models.DateTimeField(_('Fecha de fin'), null=True, blank=True)

    es_optima = models.BooleanField(_('Es óptima'), default=False)
    penalizacion_total = models.FloatField(_('Penalización total'), null=True, blank=True)
    resultado = models.JSONField(_('Resultado'), default=dict, blank=True)
    mensajes = models.JSONField(_('Mensajes'), default=dict, blank=True)

    class Meta:
        verbose_name = _('Ejecución')
        verbose_name_plural = _('Ejecuciones')
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.configuracion.nombre} - {self.fecha_inicio.strftime('%d/%m/%Y %H:%M')}"

    @property
    def duracion(self):
        """Calcula la duración de la ejecución"""
        if self.fecha_fin and self.fecha_inicio:
            delta = self.fecha_fin - self.fecha_inicio
            return delta.total_seconds()
        return None

    def get_absolute_url(self):
        return reverse('turnos:ejecucion_detalle', kwargs={'pk': self.pk})


class Planilla(models.Model):
    """Modelo para representar una planilla de turnos"""
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='planillas',
        null=True,
        blank=True
    )
    nombre = models.CharField(_('Nombre'), max_length=200)
    descripcion = models.TextField(_('Descripción'), blank=True)
    ejecucion = models.OneToOneField(
        Ejecucion,
        on_delete=models.CASCADE,
        related_name='planilla_generada',
        verbose_name=_('Ejecución')
    )

    fecha_inicio = models.DateField(_('Fecha de inicio'))
    fecha_fin = models.DateField(_('Fecha de fin'))
    num_dias = models.IntegerField(_('Número de días'))

    class Meta:
        verbose_name = _('Planilla')
        verbose_name_plural = _('Planillas')
        ordering = ['-fecha_inicio']

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse('turnos:planilla_detalle', kwargs={'pk': self.pk})


class AsignacionTurno(models.Model):
    """Modelo para representar una asignación de turno"""

    planilla = models.ForeignKey(
        Planilla,
        on_delete=models.CASCADE,
        related_name='asignaciones',
        verbose_name=_('Planilla')
    )
    enfermera = models.ForeignKey(
        Enfermera,
        on_delete=models.CASCADE,
        related_name='asignaciones',
        verbose_name=_('Enfermera')
    )
    fecha = models.DateField(_('Fecha'))
    turno = models.ForeignKey(
        TipoTurno,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Turno')
    )
    es_dia_libre = models.BooleanField(_('Es día libre'), default=False)
    observaciones = models.TextField(_('Observaciones'), blank=True)
    
    # Nuevo campo para tipo explícito de celda
    TIPO_CELDA_CHOICES = [
        ('TURNO', 'Turno normal'),
        ('LIBRE', 'Día libre'),
        ('VACACIONES', 'Vacaciones'),
        ('PERMISO', 'Permiso'),
        ('BAJA', 'Baja médica'),
        ('FORMACION', 'Formación'),
        ('ASIGNACION_FIJA', 'Asignación fija'),
    ]
    tipo_celda = models.CharField(_('Tipo de celda'), max_length=20, choices=TIPO_CELDA_CHOICES, default='TURNO')

    class Meta:
        verbose_name = _('Asignación de Turno')
        verbose_name_plural = _('Asignaciones de Turno')
        ordering = ['fecha', 'enfermera']
        unique_together = ['planilla', 'enfermera', 'fecha']

    def __str__(self):
        if self.es_dia_libre or self.tipo_celda == 'LIBRE':
            return f"{self.enfermera.nombre} - {self.fecha} - Libre"
        return f"{self.enfermera.nombre} - {self.fecha} - {self.turno}"


# ============================================================================
# NUEVOS MODELOS DE DOMINIO PARA PLANIFICACIÓN AVANZADA
# ============================================================================

class ContratoEnfermera(models.Model):
    """Define el régimen horario de una enfermera"""
    enfermera = models.OneToOneField(
        Enfermera, 
        on_delete=models.CASCADE, 
        related_name='contrato'
    )
    horas_semana_objetivo = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=40.0,
        verbose_name=_('Horas semana objetivo')
    )
    horas_anuales_objetivo = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=1800.0,
        verbose_name=_('Horas anuales objetivo')
    )
    porcentaje_jornada = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=100.0,
        help_text="100 = jornada completa, 50 = media jornada",
        verbose_name=_('Porcentaje jornada')
    )
    fecha_inicio_vigencia = models.DateField(_('Fecha inicio vigencia'))
    fecha_fin_vigencia = models.DateField(_('Fecha fin vigencia'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Contrato de Enfermera')
        verbose_name_plural = _('Contratos de Enfermera')
    
    def __str__(self):
        return f"Contrato de {self.enfermera.nombre} ({self.porcentaje_jornada}%)"


class RotacionBase(models.Model):
    """Ciclo explícito de turnos que se repite"""
    nombre = models.CharField(_('Nombre'), max_length=200)
    descripcion = models.TextField(_('Descripción'), blank=True)
    ciclo_dias = models.IntegerField(
        help_text="Duración del ciclo en días",
        verbose_name=_('Ciclo días')
    )
    workspace = models.ForeignKey(
        Workspace, 
        on_delete=models.CASCADE, 
        related_name='rotaciones',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Rotación Base')
        verbose_name_plural = _('Rotaciones Base')
    
    def __str__(self):
        return f"{self.nombre} ({self.ciclo_dias} días)"


class CeldaRotacion(models.Model):
    """Una celda dentro de un ciclo de rotación"""
    rotacion = models.ForeignKey(
        RotacionBase, 
        on_delete=models.CASCADE, 
        related_name='celdas'
    )
    orden = models.IntegerField(
        help_text="Posición dentro del ciclo (0-based)",
        verbose_name=_('Orden')
    )
    turno = models.ForeignKey(
        TipoTurno, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name=_('Turno')
    )
    # Si turno es null, representa día libre
    es_libre = models.BooleanField(_('Es libre'), default=False)
    
    class Meta:
        ordering = ['orden']
        unique_together = ['rotacion', 'orden']
        verbose_name = _('Celda de Rotación')
        verbose_name_plural = _('Celdas de Rotación')
    
    def __str__(self):
        turno_str = self.turno.nombre if self.turno else 'LIBRE'
        return f"{self.rotacion.nombre} - Día {self.orden}: {turno_str}"


class AsignacionRotacionEnfermera(models.Model):
    """Asigna una rotación a una enfermera con desfase"""
    enfermera = models.ForeignKey(
        Enfermera, 
        on_delete=models.CASCADE, 
        related_name='asignaciones_rotacion'
    )
    rotacion = models.ForeignKey(
        RotacionBase, 
        on_delete=models.CASCADE
    )
    desfase = models.IntegerField(
        default=0, 
        help_text="Desplazamiento en días dentro del ciclo",
        verbose_name=_('Desfase')
    )
    fecha_inicio = models.DateField(_('Fecha inicio'))
    fecha_fin = models.DateField(_('Fecha fin'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Asignación de Rotación')
        verbose_name_plural = _('Asignaciones de Rotación')
    
    def __str__(self):
        return f"{self.enfermera.nombre} → {self.rotacion.nombre} (desfase: {self.desfase})"


class Incidencia(models.Model):
    """Eventos que modifican la planificación normal"""
    TIPO_CHOICES = [
        ('VACACIONES', 'Vacaciones'),
        ('PERMISO', 'Permiso'),
        ('BAJA', 'Baja médica'),
        ('FORMACION', 'Formación'),
        ('LIBRANZA_BLOQUEADA', 'Libranza bloqueada'),
        ('ASIGNACION_FIJA', 'Asignación fija'),
    ]
    
    enfermera = models.ForeignKey(
        Enfermera, 
        on_delete=models.CASCADE, 
        related_name='incidencias'
    )
    tipo = models.CharField(_('Tipo'), max_length=30, choices=TIPO_CHOICES)
    fecha_inicio = models.DateField(_('Fecha inicio'))
    fecha_fin = models.DateField(_('Fecha fin'))
    turno_fijo = models.ForeignKey(
        TipoTurno, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Para ASIGNACION_FIJA, qué turno asignar",
        verbose_name=_('Turno fijo')
    )
    observaciones = models.TextField(_('Observaciones'), blank=True)
    
    class Meta:
        verbose_name = _('Incidencia')
        verbose_name_plural = _('Incidencias')
        ordering = ['fecha_inicio']
    
    def __str__(self):
        return f"{self.enfermera.nombre} - {self.get_tipo_display()} ({self.fecha_inicio} a {self.fecha_fin})"


class BalanceHistoricoEnfermera(models.Model):
    """Acumulados históricos de una enfermera para planificación contextual"""
    enfermera = models.ForeignKey(
        Enfermera, 
        on_delete=models.CASCADE, 
        related_name='balances_historicos'
    )
    periodo_referencia = models.CharField(
        max_length=20,
        help_text="Formato mensual YYYY-MM, ej. '2026-04'",
        verbose_name=_('Periodo referencia')
    )
    horas_acumuladas_previas = models.DecimalField(
        max_digits=7, 
        decimal_places=2, 
        default=0,
        verbose_name=_('Horas acumuladas previas')
    )
    noches_acumuladas = models.IntegerField(default=0, verbose_name=_('Noches acumuladas'))
    fines_semana_acumulados = models.IntegerField(default=0, verbose_name=_('Fines de semana acumulados'))
    festivos_acumulados = models.IntegerField(default=0, verbose_name=_('Festivos acumulados'))
    ultimo_turno_fecha = models.DateField(_('Último turno fecha'), null=True, blank=True)
    ultimo_turno_tipo = models.ForeignKey(
        TipoTurno, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_('Último turno tipo')
    )
    fecha_actualizacion = models.DateTimeField(_('Fecha actualización'), auto_now=True)
    
    class Meta:
        verbose_name = _('Balance Histórico')
        verbose_name_plural = _('Balances Históricos')
        unique_together = ['enfermera', 'periodo_referencia']
    
    def __str__(self):
        return f"Balance {self.enfermera.nombre} - {self.periodo_referencia}"

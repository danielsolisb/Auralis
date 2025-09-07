from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from CoreApps.users.models import Company
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError 


class Station(models.Model):
    name = models.CharField(
        _('nombre'),
        max_length=100
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    location = models.CharField(
        _('ubicación'),
        max_length=200
    )
    latitude = models.DecimalField(
        _('latitud'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        _('longitud'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        _('dirección IP'),
        protocol='both',
        blank=True,
        null=True,
        help_text=_('Dirección IP del servidor donde recibe los datos.')
    )
    port = models.PositiveIntegerField(
        _('puerto'),
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text=_('Puerto de comunicación (ej. 1883 para MQTT).')
    )
    mqtt_topic = models.CharField(
        _('topic MQTT de estado'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Topic para reportar el estado de la estación (ej. "station/123/status").')
    )
    # Asociación a la empresa, que nos permitirá filtrar los usuarios
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        verbose_name=_('empresa'), null=False
    )
    # Relación con usuarios: se permite asociar cualquier usuario
    related_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='stations',
        verbose_name=_('usuarios asociados'),
        blank=True
    )
    #owner = models.ForeignKey(
    #    settings.AUTH_USER_MODEL,
    #    on_delete=models.PROTECT,
    #    related_name='owned_stations',
    #    verbose_name=_('propietario'),
    #    limit_choices_to={'user_type': 'CL'}
    #)
    #supervisors = models.ManyToManyField(
    #    settings.AUTH_USER_MODEL,
    #    related_name='supervised_stations',
    #    verbose_name=_('supervisores'),
    #    limit_choices_to={'user_type': 'SV'},
    #    blank=True  # Hacemos el campo opcional
    #)
    is_active = models.BooleanField(
        _('activo'),
        default=True
    )
    created_at = models.DateTimeField(
        _('fecha de creación'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('última actualización'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('estación')
        verbose_name_plural = _('estaciones')
        ordering = ['name']

    #def __str__(self):
    #    return f"{self.name} - {self.owner}"
    def __str__(self):
        return f"{self.name} - {self.company}"

    def clean(self):
        super().clean()
        if not self.pk:
            # La instancia aún no se ha guardado, se omite la validación many-to-many.
            return
        for user in self.related_users.all():
            # Aquí realizas las validaciones correspondientes.
            if user.user_type in [user.UserType.CLIENT, user.UserType.SUPERVISOR]:
                if user.company != self.company:
                    raise ValidationError({
                        'related_users': _(
                            'Los usuarios de tipo Cliente y Supervisor deben pertenecer a la misma empresa que la estación.'
                        )
                    })
            elif user.user_type in [user.UserType.OPERATOR, user.UserType.INSTALLER, user.UserType.SUPERUSER]:
                if not user.company or not user.company.is_platform_owner:
                    raise ValidationError({
                        'related_users': _(
                            'Los usuarios de tipo Operador, Instalador y Superuser deben pertenecer a la empresa propietaria de la plataforma.'
                        )
                    })

    #def clean(self):
    #    super().clean()
    #    # Solo validar supervisores si la estación ya existe (tiene ID)
    #    if self.pk and self.supervisors.exists():
    #        for supervisor in self.supervisors.all():
    #            if supervisor.company != self.owner.company:
    #                raise ValidationError({
    #                    'supervisors': _('Los supervisores deben pertenecer a la misma empresa que el propietario')
    #                })

class SensorType(models.Model):
    name = models.CharField(
        _('nombre'),
        max_length=50,
        unique=True
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    unit = models.CharField(
        _('unidad de medida'),
        max_length=20
    )
    class Meta:
        verbose_name = _('tipo de sensor')
        verbose_name_plural = _('tipos de sensores')

    def __str__(self):
        return self.name

class SensorSystem(models.Model):
    name = models.CharField(_('nombre'), max_length=80, unique=True)
    slug = models.SlugField(_('slug'), max_length=80, unique=True)
    description = models.TextField(_('descripción'), blank=True)
    color = models.CharField(
        _('color'), max_length=20, blank=True, null=True,
        help_text=_('Color CSS/HEX para identificar el sistema (opc.)')
    )
    is_active = models.BooleanField(_('activo'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('sistema/origen')
        verbose_name_plural = _('sistemas/orígenes')
        ordering = ['name']

    def __str__(self):
        return self.name

# --- NUEVO: tabla de fuentes de datos ---
class DataSource(models.Model):
    name = models.CharField(_('nombre'), max_length=80, unique=True)   # p.ej. MQTT, Modbus, Derivado
    slug = models.SlugField(_('slug'), max_length=80, unique=True)
    description = models.TextField(_('descripción'), blank=True)
    is_active = models.BooleanField(_('activo'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('fuente de datos')
        verbose_name_plural = _('fuentes de datos')
        ordering = ['name']

    def __str__(self):
        return self.name

class Sensor(models.Model):
    name = models.CharField(
        _('nombre'),
        max_length=100
    )
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name='sensors',
        verbose_name=_('estación')
    )
    sensor_type = models.ForeignKey(
        SensorType,
        on_delete=models.PROTECT,
        related_name='sensors',
        verbose_name=_('tipo de sensor')
    )
    system = models.ForeignKey(
        SensorSystem,
        on_delete=models.PROTECT,
        related_name='sensors',
        null=True, blank=True,
        verbose_name=_('sistema/origen')
    )
    source = models.ForeignKey(
        DataSource,
        on_delete=models.PROTECT,
        related_name='sensors',
        null=True, blank=True,
        verbose_name=_('fuente de datos')
    )
    ip_address = models.GenericIPAddressField(
        _('dirección IP'),
        protocol='both',
        blank=True,
        null=True,
        help_text=_('IP del dispositivo, si es diferente a la de la estación.')
    )
    port = models.PositiveIntegerField(
        _('puerto'),
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text=_('Puerto de comunicación, si es diferente al de la estación.')
    )
    mqtt_topic = models.CharField(
        _('topic MQTT de datos'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Topic único donde el sensor publica sus mediciones.')
    )
    configuration = models.JSONField(
        _('configuración'),
        default=dict,
        blank=True
    )
    is_active = models.BooleanField(
        _('activo'),
        default=True
    )
    firmware_version = models.CharField(
        _('versión de firmware'),
        max_length=50,
        blank=True
    )
    installation_date = models.DateField(
        _('fecha de instalación'),
        null=True,
        blank=True
    )
    last_maintenance = models.DateField(
        _('último mantenimiento'),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    color = models.CharField(
        _('color'),
        max_length=20,
        blank=True,
        null=True,
        help_text=_('Color CSS o HEX, p. ej. #FF8800')
    )
    site = models.CharField(
        _('sitio'),
        max_length=100,
        blank=True,
        null=True
    )
    min_value = models.FloatField(
        _('valor mínimo'),
        null=True,
        blank=True,
        help_text=_('Valor mínimo aceptable para este sensor')
    )
    max_value = models.FloatField(
        _('valor máximo'),
        null=True,
        blank=True,
        help_text=_('Valor máximo aceptable para este sensor')
    )
    class Meta:
        verbose_name = _('sensor')
        verbose_name_plural = _('sensores')
        ordering = ['station', 'name']
        indexes = [
            models.Index(fields=['station', 'system']),
            models.Index(fields=['station', 'source']),
        ]

    def __str__(self):
        return f"{self.name} - {self.station}"

class SensorMaintenanceLog(models.Model):
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='maintenance_logs'
    )
    maintenance_date = models.DateField(
        _('fecha de mantenimiento')
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={
            'user_type': 'OP',
            'company__is_platform_owner': True
        },
        verbose_name=_('realizado por')
    )
    description = models.TextField(
        _('descripción del mantenimiento')
    )
    next_maintenance = models.DateField(
        _('próximo mantenimiento'),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('registro de mantenimiento')
        verbose_name_plural = _('registros de mantenimiento')
        ordering = ['-maintenance_date']

# =============================================================================
# ALERT POLICY (solo almacenamiento + helper REL→ABS)
# -----------------------------------------------------------------------------
# Esta política guarda umbrales para que TU SERVICIO EXTERNO (MQTT u otro)
# los consuma y aplique la lógica real (validación, precedencia, histéresis, etc.).
#
# Conceptos clave:
# - scope:     "GLOBAL" | "COMPANY" | "SENSOR_TYPE" | "STATION" | "SENSOR"
# - FKs:       company / sensor_type / station / sensor (todas opcionales aquí)
# - alert_mode:"ABS" (absoluto, misma unidad del sensor) | "REL" (fracción 0..1)
# - Umbrales:  warn_low, alert_low, warn_high, alert_high (todos opcionales)
# - Opcional:  enable_low_thresholds, hysteresis, persistence_seconds
# - Visual:    bands_active, color_warn, color_alert
#
# Nota importante:
#   - Aquí NO imponemos validación de rangos ni precedencias.
#   - El helper get_absolute_thresholds(sensor=...) te devuelve los valores
#     ABSOLUTOS listos para usar; si alert_mode=REL, convierte con el rango
#     [min_value, max_value] del sensor.
# =============================================================================

class AlertPolicy(models.Model):
    class Scope(models.TextChoices):
        GLOBAL = "GLOBAL", "Global"
        COMPANY = "COMPANY", "Company"
        SENSOR_TYPE = "SENSOR_TYPE", "Sensor Type"
        STATION = "STATION", "Station"
        SENSOR = "SENSOR", "Sensor"

    class Mode(models.TextChoices):
        ABS = "ABS", "Absoluto"
        REL = "REL", "Relativo al rango"

    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        default=Scope.SENSOR,
        db_index=True,
        help_text=_("Ámbito al que aplica esta política (la precedencia la decides en tu servicio externo)."),
    )

    # FKs opcionales: usa las que necesites según tu flujo
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, null=True, blank=True, related_name="alert_policies",
        help_text=_("Vincular a una compañía (opcional).")
    )
    sensor_type = models.ForeignKey(
        SensorType, on_delete=models.PROTECT, null=True, blank=True, related_name="alert_policies",
        help_text=_("Vincular a un tipo de sensor (opcional).")
    )
    station = models.ForeignKey(
        Station, on_delete=models.PROTECT, null=True, blank=True, related_name="alert_policies",
        help_text=_("Vincular a una estación (opcional).")
    )
    sensor = models.ForeignKey(
        Sensor, on_delete=models.PROTECT, null=True, blank=True, related_name="alert_policies",
        help_text=_("Vincular a un sensor específico (opcional).")
    )

    alert_mode = models.CharField(
        max_length=10,
        choices=Mode.choices,
        default=Mode.REL,
        help_text=_("ABS: umbrales en unidades del sensor. REL: fracción 0..1 del rango [min,max] del sensor."),
    )

    # Umbrales (todos opcionales; tu servicio decide cómo interpretarlos)
    warn_high  = models.FloatField(null=True, blank=True, help_text=_("Umbral de advertencia alto (amarillo)."))
    alert_high = models.FloatField(null=True, blank=True, help_text=_("Umbral de alerta alto (rojo)."))

    enable_low_thresholds = models.BooleanField(
        default=False, help_text=_("Activa bandas bajas (warning/alert) para este alcance.")
    )
    warn_low   = models.FloatField(null=True, blank=True, help_text=_("Umbral de advertencia bajo (amarillo)."))
    alert_low  = models.FloatField(null=True, blank=True, help_text=_("Umbral de alerta bajo (rojo)."))

    # Parámetros opcionales de estabilidad (serán usados por tu servicio)
    hysteresis = models.FloatField(null=True, blank=True, help_text=_("Margen para evitar parpadeo (opcional)."))
    persistence_seconds = models.PositiveIntegerField(
        null=True, blank=True, help_text=_("Segundos mínimos fuera de banda antes de notificar (opcional).")
    )

    # Visual y estado
    bands_active = models.BooleanField(default=True, help_text=_("Permite desactivar esta política sin eliminarla."))

    hex_validator = RegexValidator(
        regex=r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
        message=_("Use un color HEX válido, p. ej. #FFC107"),
    )
    color_warn  = models.CharField(max_length=9, null=True, blank=True, validators=[hex_validator],
                                   help_text=_("Color para WARNING (ej. #FFC107)."))
    color_alert = models.CharField(max_length=9, null=True, blank=True, validators=[hex_validator],
                                   help_text=_("Color para ALERT (ej. #DC3545)."))

    description = models.TextField(blank=True, help_text=_("Comentario opcional (quién/por qué)."))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("política de umbrales")
        verbose_name_plural = _("políticas de umbrales")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["scope"]),
            models.Index(fields=["company"]),
            models.Index(fields=["sensor_type"]),
            models.Index(fields=["station"]),
            models.Index(fields=["sensor"]),
        ]

    def __str__(self):
        tgt = (self.sensor or self.station or self.sensor_type or self.company or "GLOBAL")
        return f"{self.get_scope_display()} → {tgt}"

    # ----------------------------- Helper principal ---------------------------
    def get_absolute_thresholds(self, sensor=None):
        """
        Devuelve un dict con umbrales ABSOLUTOS (en unidades del sensor).
        - Si alert_mode=ABS: retorna los valores tal cual.
        - Si alert_mode=REL: convierte usando el rango [min_value, max_value].
        - Si no se pasa 'sensor' y scope=SENSOR, usa self.sensor.
        - Si no hay rango, usa [0, 1] para evitar errores.
        """
        s = sensor or self.sensor
        smin = float(getattr(s, "min_value", 0.0) or 0.0)
        smax = float(getattr(s, "max_value", 1.0) or 1.0)
        span = max(0.0, smax - smin)

        def conv(v):
            if v is None:
                return None
            return float(v) if self.alert_mode == self.Mode.ABS else (smin + float(v) * span)

        return {
            "warn_low":   conv(self.warn_low),
            "alert_low":  conv(self.alert_low),
            "warn_high":  conv(self.warn_high),
            "alert_high": conv(self.alert_high),
            "hysteresis": conv(self.hysteresis) if self.hysteresis is not None else None,
            "bands_active": self.bands_active,
            "color_warn":  self.color_warn or "#FFC107",
            "color_alert": self.color_alert or "#DC3545",
            "mode": self.alert_mode,
        }

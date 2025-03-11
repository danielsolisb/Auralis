from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

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
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_stations',
        verbose_name=_('propietario'),
        limit_choices_to={'user_type': 'CL'}
    )
    supervisors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='supervised_stations',
        verbose_name=_('supervisores'),
        limit_choices_to={'user_type': 'SV'},
        blank=True  # Hacemos el campo opcional
    )
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

    def __str__(self):
        return f"{self.name} - {self.owner}"

    def clean(self):
        super().clean()
        # Solo validar supervisores si la estación ya existe (tiene ID)
        if self.pk and self.supervisors.exists():
            for supervisor in self.supervisors.all():
                if supervisor.company != self.owner.company:
                    raise ValidationError({
                        'supervisors': _('Los supervisores deben pertenecer a la misma empresa que el propietario')
                    })

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

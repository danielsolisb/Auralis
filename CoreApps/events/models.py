from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from CoreApps.sensorhub.models import Sensor

User = get_user_model()

class BaseEvent(models.Model):
    """Modelo base para eventos (alarmas y advertencias)"""
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name=_('sensor')
    )
    timestamp = models.DateTimeField(
        _('fecha y hora'),
        auto_now_add=True
    )
    value = models.FloatField(
        _('valor registrado')
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    is_active = models.BooleanField(
        _('activo'),
        default=True
    )
    resolved_at = models.DateTimeField(
        _('fecha de resolución'),
        null=True,
        blank=True
    )
    resolution_notes = models.TextField(
        _('notas de resolución'),
        blank=True, null=True
    )

    class Meta:
        abstract = True
        ordering = ['-timestamp']

class Alarm(BaseEvent):
    """Modelo para alarmas críticas que requieren atención inmediata"""
    severity = models.CharField(
        _('severidad'),
        max_length=20,
        choices=[
            ('BAJA', _('Baja')),
            ('MEDIA', _('Media')),
            ('ALTA', _('Alta')),
            ('CRITICA', _('Crítica')),
        ],
        default='MEDIA'
    )
    notified = models.BooleanField(
        _('notificado'),
        default=False
    )

    class Meta:
        verbose_name = _('alarma')
        verbose_name_plural = _('alarmas')

    def __str__(self):
        return f"Alarma: {self.sensor} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"

class Warning(BaseEvent):
    """Modelo para advertencias que no son críticas pero requieren seguimiento"""
    acknowledged = models.BooleanField(
        _('reconocido'),
        default=False
    )
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_warnings',
        verbose_name=_('reconocido por')
    )
    acknowledged_at = models.DateTimeField(
        _('fecha de reconocimiento'),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('advertencia')
        verbose_name_plural = _('advertencias')

    def __str__(self):
        return f"Advertencia: {self.sensor} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"

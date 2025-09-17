# CoreApps/events/models.py - VERSIÓN CORRECTA Y FINAL

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from CoreApps.sensorhub.models import Sensor
from CoreApps.rulesengine.models import Rule 

User = get_user_model()

class BaseEvent(models.Model):
    """
    Modelo base para INCIDENTES (alarmas y advertencias). Cada registro representa
    un único incidente desde que comienza hasta que se resuelve.
    """
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name=_('sensor')
    )
    rule = models.ForeignKey(
        Rule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)ss',
        verbose_name=_('regla que lo originó')
    )
    started_at = models.DateTimeField(
        _('fecha de inicio'),
        auto_now_add=True,
        db_index=True
    )
    triggering_value = models.FloatField(
        _('valor de activación')
    )
    peak_value = models.FloatField(
        _('valor pico durante el incidente'),
        null=True,
        blank=True
    )
    last_value = models.FloatField(
        _('último valor registrado'),
        null=True,
        blank=True
    )
    update_count = models.PositiveIntegerField(
        _('conteo de actualizaciones'),
        default=1
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    is_active = models.BooleanField(
        _('incidente activo'),
        default=True,
        db_index=True
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
        ordering = ['-started_at']

class Alarm(BaseEvent):
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
        # Corregido para usar el nuevo nombre de campo
        return f"Alarma: {self.sensor} - {self.started_at.strftime('%d/%m/%Y %H:%M')}"

class Warning(BaseEvent):
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
        # Corregido para usar el nuevo nombre de campo
        return f"Advertencia: {self.sensor} - {self.started_at.strftime('%d/%m/%Y %H:%M')}"
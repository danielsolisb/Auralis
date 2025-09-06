from django.db import models
from django.utils.translation import gettext_lazy as _
from CoreApps.sensorhub.models import Sensor


class Measurement(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='measurements', db_index=True)
    measured_at = models.DateTimeField(_('fecha y hora'), db_index=True)   # nombre físico será measured_at
    value = models.FloatField(_('valor'))

    class Meta:
        verbose_name = _('medición')
        verbose_name_plural = _('mediciones')
        db_table = 'measurements_measurement'
        managed = True
        indexes = [
            models.Index(fields=['sensor', 'measured_at']),
            models.Index(fields=['measured_at']),
        ]

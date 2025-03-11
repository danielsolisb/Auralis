from django.db import models
from django.utils.translation import gettext_lazy as _
from CoreApps.sensorhub.models import Sensor

class Measurement(models.Model):
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='measurements',
        db_index=True
    )
    timestamp = models.DateTimeField(
        _('fecha y hora'),
        db_index=True
    )
    value = models.FloatField(
        _('valor')
    )
    is_valid = models.BooleanField(
        _('válido'),
        default=True,
        help_text=_('Indica si el valor está dentro del rango permitido')
    )

    class Meta:
        verbose_name = _('medición')
        verbose_name_plural = _('mediciones')
        indexes = [
            models.Index(fields=['sensor', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        # Comentamos o eliminamos estas líneas temporalmente
        # db_table = 'measurements_measurement'
        # managed = False

    def save(self, *args, **kwargs):
        # Validar el rango si está definido
        if self.sensor.min_value is not None and \
           self.sensor.max_value is not None:
            self.is_valid = (
                self.value >= self.sensor.min_value and 
                self.value <= self.sensor.max_value
            )
        super().save(*args, **kwargs)

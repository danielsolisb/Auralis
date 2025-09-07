from django.db import models
from django.conf import settings
from CoreApps.sensorhub.models import Station, Sensor
# Create your models here.
class SettingAuditLog(models.Model):
    ACTIONS = (('create','Create'), ('update','Update'), ('delete','Delete'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTIONS)
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    station = models.ForeignKey(Station, null=True, blank=True, on_delete=models.SET_NULL)
    sensor = models.ForeignKey(Sensor, null=True, blank=True, on_delete=models.SET_NULL)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

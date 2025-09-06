# CoreApps/measurements/admin.py
from django.contrib import admin
from .models import Measurement

@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    # Lo esencial en la lista
    list_display = ('id', 'measured_at', 'sensor', 'value')
    ordering = ('-measured_at',)
    date_hierarchy = 'measured_at'

    # Filtros y búsqueda útiles (sin is_valid)
    list_filter = ('sensor__station', 'sensor__sensor_type')
    search_fields = ('sensor__name', 'sensor__station__name')

    # En general estas mediciones no se editan desde admin
    readonly_fields = ('measured_at', 'sensor', 'value')

    # Optimiza las consultas en la lista
    list_select_related = ('sensor', 'sensor__station', 'sensor__sensor_type')

from django.contrib import admin
from django.utils.translation import gettext_lazy as _  # Añadimos esta importación
from .models import Station, SensorType, Sensor, SensorMaintenanceLog

class SensorInline(admin.TabularInline):
    model = Sensor
    extra = 1

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'location', 'is_active')
    list_filter = ('owner', 'is_active')
    search_fields = ('name', 'description', 'location', 'owner__email')
    inlines = [SensorInline]
    filter_horizontal = ('supervisors',)

@admin.register(SensorType)
class SensorTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit')
    search_fields = ('name', 'description')

class MaintenanceLogInline(admin.TabularInline):
    model = SensorMaintenanceLog
    extra = 1

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('name', 'station', 'sensor_type', 'is_active', 'min_value', 'max_value')
    list_filter = ('station', 'sensor_type', 'is_active')
    search_fields = ('name', 'station__name', 'station__owner__email')
    fieldsets = (
        (None, {
            'fields': ('name', 'station', 'sensor_type', 'is_active')
        }),
        (_('Configuración de rangos'), {
            'fields': ('min_value', 'max_value'),
        }),
        (_('Información técnica'), {
            'fields': ('configuration', 'firmware_version', 'installation_date', 'last_maintenance'),
        }),
    )
    inlines = [MaintenanceLogInline]

@admin.register(SensorMaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'maintenance_date', 'performed_by', 'next_maintenance')
    list_filter = ('maintenance_date', 'performed_by')
    search_fields = ('sensor__name', 'description', 'performed_by__email')

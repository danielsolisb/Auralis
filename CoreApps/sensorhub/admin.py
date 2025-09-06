from django.contrib import admin
from django.utils.translation import gettext_lazy as _  # Añadimos esta importación
from .models import Station, SensorType, Sensor, SensorMaintenanceLog, SensorSystem, DataSource
from django.utils.html import format_html


class SensorInline(admin.TabularInline):
    model = Sensor
    extra = 1

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'location', 'is_active', 'get_related_users')
    list_filter = ('company', 'is_active')
    search_fields = ('name', 'description', 'location', 'company__name')
    # Ahora solo se muestra el campo relacionado que existe
    filter_horizontal = ('related_users',)  
    
    def get_related_users(self, obj):
        return ", ".join([str(user) for user in obj.related_users.all()])
    get_related_users.short_description = 'Usuarios asociados'

@admin.register(SensorType)
class SensorTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit')
    search_fields = ('name', 'description')

class MaintenanceLogInline(admin.TabularInline):
    model = SensorMaintenanceLog
    extra = 1

@admin.register(SensorSystem)
class SensorSystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'color_chip')
    search_fields = ('name', 'slug')
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}

    def color_chip(self, obj):
        if not obj.color:
            return ''
        return format_html(
            '<span style="display:inline-block;width:14px;height:14px;border:1px solid #ddd;'
            'border-radius:3px;background:{};width:14px;height:14px;vertical-align:middle;"></span> {}',
            obj.color, obj.color
        )
    color_chip.short_description = 'Color'

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    search_fields = ('name', 'slug')
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('name', 'station', 'sensor_type', 'system', 'source', 'is_active', 'min_value', 'max_value', 'color', 'site')
    list_filter  = ('station', 'sensor_type', 'system', 'source', 'is_active')
    search_fields = ('name', 'station__name', 'sensor_type__name', 'system__name', 'source__name', 'site')
    list_select_related = ('station', 'sensor_type', 'system', 'source')

    fieldsets = (
        (None, {
            'fields': ('name', 'station', 'sensor_type', 'system', 'source', 'is_active', 'color', 'site')
        }),
        (_('Rangos'), {
            'fields': ('min_value', 'max_value'),
        }),
        (_('Técnico'), {
            'fields': ('configuration', 'firmware_version', 'installation_date', 'last_maintenance'),
        }),
    )

@admin.register(SensorMaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'maintenance_date', 'performed_by', 'next_maintenance')
    list_filter = ('maintenance_date', 'performed_by')
    search_fields = ('sensor__name', 'description', 'performed_by__email')

# CoreApps/events/admin.py (VERSIÓN CORREGIDA Y FINAL)

from django.contrib import admin
from .models import Alarm, Warning

class BaseEventAdmin(admin.ModelAdmin):
    """
    Configuración base para el admin de Alarmas y Advertencias.
    """
    list_display = ('sensor', 'started_at', 'triggering_value', 'is_active', 'resolved_at')
    list_filter = ('is_active', 'sensor__station__company', 'sensor__station')
    search_fields = ('sensor__name', 'description')
    date_hierarchy = 'started_at'

    # Esta función nos permite separar los campos para la vista de 'añadir' y 'cambiar'
    def get_fieldsets(self, request, obj=None):
        if obj: # Si el objeto ya existe (vista de 'cambiar')
            return (
                ('Información del Incidente (No editable)', {
                    'fields': ('is_active', 'sensor', 'rule', 'started_at')
                }),
                ('Detalles de la Medición (No editable)', {
                    'fields': ('triggering_value', 'peak_value', 'last_value', 'update_count')
                }),
                ('Gestión de Resolución', {
                    'fields': ('description', 'resolved_at', 'resolution_notes')
                }),
            )
        else: # Si es un objeto nuevo (vista de 'añadir')
            return (
                ('Datos del Nuevo Incidente', {
                    'fields': ('sensor', 'rule', 'triggering_value', 'description')
                }),
            )

    def get_readonly_fields(self, request, obj=None):
        if obj: # Si el objeto ya existe, hacemos casi todo de solo lectura
            return (
                'sensor', 'rule', 'started_at', 'triggering_value', 
                'peak_value', 'last_value', 'update_count'
            )
        # En la vista de 'añadir', no hay campos de solo lectura (permitimos crearlo)
        return ()


@admin.register(Alarm)
class AlarmAdmin(BaseEventAdmin):
    list_display = ('sensor', 'severity', 'started_at', 'triggering_value', 'is_active')
    list_filter = ('is_active', 'severity', 'sensor__station__company')
    
    # Sobrescribimos la función para añadir los campos específicos de Alarma
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj: # Vista de 'cambiar'
             return fieldsets + (
                ('Estado de la Alarma', {
                    'fields': ('severity', 'notified')
                }),
            )
        else: # Vista de 'añadir'
            # Añadimos los campos de Alarma al primer fieldset
            # El [0][1]['fields'] accede a la tupla de campos del primer fieldset
            new_fields = fieldsets[0][1]['fields'] + ('severity',)
            return (('Datos de la Nueva Alarma', {'fields': new_fields}),)


@admin.register(Warning)
class WarningAdmin(BaseEventAdmin):
    list_display = ('sensor', 'acknowledged', 'started_at', 'triggering_value', 'is_active')
    list_filter = ('is_active', 'acknowledged', 'sensor__station__company')

    # Sobrescribimos la función para añadir los campos específicos de Warning
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj: # Vista de 'cambiar'
             return fieldsets + (
                ('Estado de la Advertencia', {
                    'fields': ('acknowledged', 'acknowledged_by', 'acknowledged_at')
                }),
            )
        else: # Vista de 'añadir'
            # Añadimos los campos de Warning al primer fieldset
            new_fields = fieldsets[0][1]['fields'] + ('acknowledged',)
            return (('Datos de la Nueva Advertencia', {'fields': new_fields}),)
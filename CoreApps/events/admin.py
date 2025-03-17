from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Alarm, Warning

@admin.register(Alarm)
class AlarmAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'timestamp', 'value', 'severity', 'is_active', 'notified')
    list_filter = ('severity', 'is_active', 'notified', 'sensor__station')
    search_fields = ('sensor__name', 'description', 'resolution_notes')
    readonly_fields = ('timestamp',)
    fieldsets = (
        (_('Información básica'), {
            'fields': ('sensor', 'timestamp', 'value', 'severity', 'description')
        }),
        (_('Estado'), {
            'fields': ('is_active', 'notified')
        }),
        (_('Resolución'), {
            'fields': ('resolved_at', 'resolution_notes'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'timestamp'

@admin.register(Warning)
class WarningAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'timestamp', 'value', 'is_active', 'acknowledged')
    list_filter = ('is_active', 'acknowledged', 'sensor__station')
    search_fields = ('sensor__name', 'description', 'resolution_notes')
    readonly_fields = ('timestamp',)
    fieldsets = (
        (_('Información básica'), {
            'fields': ('sensor', 'timestamp', 'value', 'description')
        }),
        (_('Estado'), {
            'fields': ('is_active', 'acknowledged')
        }),
        (_('Reconocimiento'), {
            'fields': ('acknowledged_by', 'acknowledged_at'),
            'classes': ('collapse',)
        }),
        (_('Resolución'), {
            'fields': ('resolved_at', 'resolution_notes'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'timestamp'

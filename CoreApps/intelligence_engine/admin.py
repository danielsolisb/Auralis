# CoreApps/intelligence_engine/admin.py

from django.contrib import admin
from .models import MLModel, ModelAssignment, PredictionEvent, OperationalLog

@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

@admin.register(ModelAssignment)
class ModelAssignmentAdmin(admin.ModelAdmin):
    list_display = ('station', 'ml_model', 'is_active', 'updated_at')
    list_filter = ('is_active', 'ml_model')
    search_fields = ('station__name',)
    autocomplete_fields = ['station', 'ml_model']

@admin.register(PredictionEvent)
class PredictionEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'assignment', 'status', 'prediction_confidence', 'event_time')
    list_filter = ('status',)
    search_fields = ('title', 'description', 'assignment__station__name')
    readonly_fields = ('created_at',)

@admin.register(OperationalLog)
class OperationalLogAdmin(admin.ModelAdmin):
    list_display = ('station', 'event_type', 'start_time', 'end_time', 'created_by')
    list_filter = ('event_type', 'station')
    search_fields = ('description', 'station__name')
    autocomplete_fields = ['station'] # Asume que tienes búsqueda en el admin para Station
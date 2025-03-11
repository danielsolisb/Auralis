from django.contrib import admin
from .models import Measurement

@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'timestamp', 'value', 'is_valid')
    list_filter = ('is_valid', 'sensor__station', 'sensor')
    search_fields = ('sensor__name', 'sensor__station__name')
    date_hierarchy = 'timestamp'
    readonly_fields = ('is_valid',)

    # Eliminar o comentar esta función para permitir la creación manual
    # def has_add_permission(self, request):
    #     return False

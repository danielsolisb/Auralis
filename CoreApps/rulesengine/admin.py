# CoreApps/rulesengine/admin.py

from django.contrib import admin
from .models import Rule, Condition, RuleNode

@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    # Añadimos 'threshold_type' para verlo en la lista
    list_display = ('name', 'source_sensor', 'threshold_type', 'operator', 'updated_at')
    list_filter = ('threshold_type', 'metric_to_evaluate', 'operator', 'source_sensor__station')
    search_fields = ('name', 'source_sensor__name')
    list_per_page = 25
    
    # Reorganizamos los campos para que sean más intuitivos en el formulario
    fieldsets = (
        (None, {
            'fields': ('name', 'source_sensor')
        }),
        ('Lógica de Evaluación', {
            'fields': ('metric_to_evaluate', 'operator')
        }),
        # Nueva sección para elegir el tipo de umbral
        ('Fuente del Umbral', {
            'description': "Elija el tipo de umbral y rellene solo el campo correspondiente.",
            'fields': ('threshold_type', 'threshold_config', 'linked_policy')
        }),
    )

class RuleNodeInline(admin.TabularInline):
    """
    Permite editar los nodos hijos directamente dentro de la vista de un nodo padre.
    Esto es lo que nos permite construir el árbol visualmente en el admin.
    """
    model = RuleNode
    fk_name = 'parent'
    extra = 1
    verbose_name = "Sub-Nodo"
    verbose_name_plural = "Sub-Nodos (Condiciones u Operadores Lógicos)"

@admin.register(RuleNode)
class RuleNodeAdmin(admin.ModelAdmin):
    """
    Administrador para los nodos individuales. Es útil para ver la estructura,
    pero la edición principal se hará a través de RuleAdmin.
    """
    list_display = ('__str__', 'rule', 'parent')
    list_filter = ('rule__company', 'node_type')
    inlines = [RuleNodeInline]


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    """
    Administrador principal para las Reglas. Desde aquí se construirá
    la lógica completa de una regla avanzada.
    """
    list_display = ('name', 'company', 'severity', 'is_active', 'updated_at')
    list_filter = ('company', 'severity', 'is_active')
    search_fields = ('name', 'description')
    
    # Definimos un inline especial para los nodos raíz (aquellos que no tienen padre)
    class RootRuleNodeInline(admin.TabularInline):
        model = RuleNode
        fk_name = 'rule'
        extra = 1
        verbose_name = "Nodo Raíz"
        verbose_name_plural = "Nodos Raíz (el inicio de la lógica de la regla)"

        def get_queryset(self, request):
            # Mostramos solo los nodos que no tienen padre (son el inicio de la regla)
            qs = super().get_queryset(request)
            return qs.filter(parent__isnull=True)

    inlines = [RootRuleNodeInline]
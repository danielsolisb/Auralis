# CoreApps/rulesengine/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _

# Importamos los modelos de otras aplicaciones con los que nos vamos a relacionar
from CoreApps.users.models import Company
from CoreApps.sensorhub.models import Sensor

class Rule(models.Model):
    """
    Representa una regla de negocio compleja. Es el contenedor principal de una o más condiciones
    lógicas que, en conjunto, pueden disparar una alerta.
    Ej: "Riesgo de Sobrecalentamiento en Data Center"
    """
    class SeverityChoices(models.TextChoices):
        INFO = 'INFO', _('Informativo')
        WARNING = 'WARNING', _('Advertencia')
        CRITICAL = 'CRITICAL', _('Crítico')

    name = models.CharField(
        _('nombre de la regla'),
        max_length=200,
        help_text=_("Un nombre descriptivo y único para la regla.")
    )
    description = models.TextField(
        _('descripción'),
        blank=True,
        help_text=_("Una explicación detallada de lo que esta regla detecta.")
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='rules',
        verbose_name=_('empresa'),
        help_text=_("La empresa a la que pertenece esta regla.")
    )
    severity = models.CharField(
        _('severidad'),
        max_length=10,
        choices=SeverityChoices.choices,
        default=SeverityChoices.WARNING,
        help_text=_("La severidad de la alerta que se generará si la regla se cumple.")
    )
    is_active = models.BooleanField(
        _('activa'),
        default=True,
        db_index=True,
        help_text=_("Desmarque esta opción para desactivar la regla sin eliminarla.")
    )
    created_at = models.DateTimeField(_('fecha de creación'), auto_now_add=True)
    updated_at = models.DateTimeField(_('última actualización'), auto_now=True)

    class Meta:
        verbose_name = _('regla avanzada')
        verbose_name_plural = _('reglas avanzadas')
        ordering = ['company', 'name']
        unique_together = ('company', 'name')

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Condition(models.Model):
    """
    Representa una única condición lógica que se evalúa contra un dato de un sensor.
    Ej: "La temperatura del Sensor 'CPU-Temp' es mayor que 80°C"
    """
    class MetricChoices(models.TextChoices):
        CURRENT_VALUE = "VALUE", _("Valor Actual")
        RATE_OF_CHANGE = "ROC", _("Ritmo de Cambio (valor/tiempo)")
        # --- Opciones para la Fase 2 (Inteligencia Artificial) ---
        # ANOMALY_SCORE = "ANOMALY", _("Puntuación de Anomalía")
        # PREDICTED_VALUE = "PREDICT", _("Valor Predicho")

    class OperatorChoices(models.TextChoices):
        GREATER_THAN = ">", _("Mayor que")
        LESS_THAN = "<", _("Menor que")
        EQUAL_TO = "==", _("Igual a")
        BETWEEN = "BETWEEN", _("Entre")
        NOT_BETWEEN = "NOT_BETWEEN", _("Fuera de")

    name = models.CharField(
        _('nombre de la condición'),
        max_length=150,
        help_text=_("Un nombre descriptivo para la condición. Ej: Temp > 80°C")
    )
    source_sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='conditions',
        verbose_name=_('sensor de origen')
    )
    metric_to_evaluate = models.CharField(
        _('métrica a evaluar'),
        max_length=10,
        choices=MetricChoices.choices,
        default=MetricChoices.CURRENT_VALUE
    )
    operator = models.CharField(
        _('operador de comparación'),
        max_length=15,
        choices=OperatorChoices.choices,
        default=OperatorChoices.GREATER_THAN
    )
    threshold_config = models.JSONField(
        _('configuración de umbrales'),
        default=dict,
        help_text=_("Valores de umbral en formato JSON. Ej: {'type': 'STATIC', 'value': 30} o {'type': 'TIME_BASED', 'weekday_value': 25, 'weekend_value': 28}")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('condición')
        verbose_name_plural = _('condiciones')

    def __str__(self):
        return f"{self.name} [{self.source_sensor.name}]"


class RuleNode(models.Model):
    """
    Define la estructura de árbol de una Regla. Cada nodo puede ser una Condición
    o un Operador Lógico (AND/OR) que agrupa a otros nodos.
    """
    class NodeType(models.TextChoices):
        CONDITION = "COND", _("Condición")
        OPERATOR = "OP", _("Operador Lógico")

    class LogicalOperatorChoices(models.TextChoices):
        AND = 'AND', _('Y (todas las sub-condiciones deben ser verdaderas)')
        OR = 'OR', _('O (al menos una sub-condición debe ser verdadera)')

    rule = models.ForeignKey(
        Rule,
        related_name='nodes',
        on_delete=models.CASCADE,
        verbose_name=_('regla')
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
        on_delete=models.CASCADE,
        verbose_name=_('nodo padre')
    )
    node_type = models.CharField(
        _('tipo de nodo'),
        max_length=4,
        choices=NodeType.choices
    )
    
    # Si el nodo es de tipo 'COND', apunta a una condición específica
    condition = models.ForeignKey(
        Condition,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_('condición vinculada')
    )

    # Si el nodo es de tipo 'OP', define qué operador lógico usa
    logical_operator = models.CharField(
        _('operador lógico'),
        max_length=3,
        choices=LogicalOperatorChoices.choices,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('nodo de regla')
        verbose_name_plural = _('nodos de regla')

    def __str__(self):
        if self.node_type == self.NodeType.CONDITION and self.condition:
            return f"Condición: {self.condition.name}"
        elif self.node_type == self.NodeType.OPERATOR:
            return f"Operador: {self.get_logical_operator_display()}"
        return f"Nodo #{self.pk}"
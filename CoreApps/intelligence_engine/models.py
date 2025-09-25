# CoreApps/intelligence_engine/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _

# Importamos los modelos de otras apps con los que nos relacionaremos
from CoreApps.sensorhub.models import Station
from django.conf import settings

class MLModel(models.Model):
    """
    Registra la metadata de un modelo de Machine Learning entrenado.
    Este es nuestro "Catálogo de Cerebros".
    """
    name = models.CharField(
        _("nombre del modelo"),
        max_length=200,
        unique=True,
        help_text=_("Ej: 'Predictor de Producción - Pozos BES v1.1'")
    )
    description = models.TextField(
        _("descripción"),
        blank=True,
        help_text=_("¿Qué hace este modelo? ¿Para qué industria sirve? ¿Qué variables espera?")
    )
    version = models.CharField(
        _("versión"),
        max_length=20,
        default="1.0.0",
        help_text=_("Versión del modelo, ej: '1.0.1'.")
    )
    model_file_path = models.CharField(
        _("ruta del archivo del modelo"),
        max_length=512,
        help_text=_("Ruta en Google Cloud Storage al archivo .h5 o .pkl del modelo entrenado.")
    )
    training_parameters = models.JSONField(
        _("parámetros de entrenamiento"),
        default=dict,
        blank=True,
        help_text=_("Metadata sobre cómo fue entrenado. Ej: {'industry': 'Oil&Gas', 'features': ['Temp', 'Pressure']}")
    )
    is_active = models.BooleanField(
        _("activo"),
        default=True,
        help_text=_("Solo los modelos activos serán utilizados para predicciones.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("modelo de ML")
        verbose_name_plural = _("modelos de ML")
        ordering = ['name', '-version']

    def __str__(self):
        return f"{self.name} ({self.version})"


class ModelAssignment(models.Model):
    """
    Asigna un Modelo de ML específico a una o más Estaciones.
    Esta es la pieza clave que conecta todo sin modificar modelos existentes.
    """
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="model_assignments",
        verbose_name=_("estación")
    )
    ml_model = models.ForeignKey(
        MLModel,
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name=_("modelo de ML")
    )
    is_active = models.BooleanField(
        _("asignación activa"),
        default=True,
        db_index=True,
        help_text=_("Desmarcar para pausar las predicciones para esta estación sin borrar la configuración.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("asignación de modelo")
        verbose_name_plural = _("asignaciones de modelos")
        # Evita asignar el mismo modelo a la misma estación dos veces
        unique_together = ('station', 'ml_model')

    def __str__(self):
        return f"'{self.station.name}' -> '{self.ml_model.name}'"


class PredictionEvent(models.Model):
    """
    Almacena una predicción o evento generado por un modelo de ML.
    Este es el registro de los hallazgos de nuestros "cerebros".
    """
    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Activo')
        ACKNOWLEDGED = 'ACKNOWLEDGED', _('Confirmado')
        RESOLVED = 'RESOLVED', _('Resuelto')

    assignment = models.ForeignKey(
        ModelAssignment,
        on_delete=models.CASCADE,
        related_name="prediction_events",
        verbose_name=_("asignación de modelo")
    )
    title = models.CharField(
        _("título del evento"),
        max_length=255
    )
    description = models.TextField(
        _("descripción detallada")
    )
    prediction_confidence = models.FloatField(
        _("confianza de la predicción"),
        null=True, blank=True,
        help_text=_("Valor entre 0.0 y 1.0 que indica la confianza del modelo.")
    )
    event_time = models.DateTimeField(
        _("fecha y hora del evento predicho"),
        help_text=_("El momento en el futuro para el cual se predice el evento.")
    )
    status = models.CharField(
        _("estado"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
        db_index=True
    )
    details = models.JSONField(
        _("detalles adicionales"),
        default=dict,
        blank=True,
        help_text=_("Cualquier otra data relevante, como los valores de los sensores en ese momento.")
    )
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)

    class Meta:
        verbose_name = _("evento de predicción")
        verbose_name_plural = _("eventos de predicción")
        ordering = ['-event_time']

    def __str__(self):
        return f"{self.title} en {self.assignment.station.name}"


# CoreApps/intelligence_engine/models.py
# (Añadir al final del archivo)

class OperationalLog(models.Model):
    """
    Registra eventos operativos o cambios de estado en una estación,
    proporcionando contexto crucial para el entrenamiento de los modelos de ML.
    """
    # --- Tipos de Evento Predefinidos y Extensibles ---
    class EventType(models.TextChoices):
        MAINTENANCE = 'MAINTENANCE', _('Mantenimiento')
        VALVE_OPERATION = 'VALVE_OPERATION', _('Operación de Válvula')
        GAS_VENTING = 'GAS_VENTING', _('Venteo de Gas / Mechero')
        SCHEDULED_STOP = 'SCHEDULED_STOP', _('Parada Programada')
        UNSCHEDULED_STOP = 'UNSCHEDULED_STOP', _('Parada No Programada')
        PARAMETER_CHANGE = 'PARAMETER_CHANGE', _('Cambio de Parámetro Operativo')
        OTHER = 'OTHER', _('Otro')

    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="operational_logs",
        verbose_name=_("estación")
    )
    event_type = models.CharField(
        _("tipo de evento"),
        max_length=50,
        choices=EventType.choices,
        default=EventType.OTHER,
        help_text=_("Clasificación del evento para facilitar el análisis del modelo.")
    )
    start_time = models.DateTimeField(
        _("inicio del evento"),
        help_text=_("Fecha y hora en que comenzó la operación o el cambio de estado.")
    )
    # --- CAMBIO CLAVE: end_time es opcional ---
    end_time = models.DateTimeField(
        _("fin del evento"),
        null=True,  # Permite que el campo esté vacío en la base de datos
        blank=True, # Permite que el campo esté vacío en los formularios de Django
        help_text=_("Dejar en blanco si es un cambio de estado permanente o si el evento aún no ha terminado.")
    )
    description = models.TextField(
        _("descripción"),
        help_text=_("Detalles de la operación. Ej: 'Apertura de mechero en espera de instalación de GAE.'")
    )
    # Para saber quién registró el evento
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("registrado por")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("registro operacional")
        verbose_name_plural = _("registros operacionales")
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.get_event_type_display()} en {self.station.name} a las {self.start_time.strftime('%Y-%m-%d %H:%M')}"
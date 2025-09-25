# CoreApps/intelligence_engine/serializers.py

from rest_framework import serializers
from .models import PredictionEvent

class PredictionEventCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para que el servicio de ML pueda crear un nuevo evento de predicción.
    """
    class Meta:
        model = PredictionEvent
        # Definimos los campos que esperamos recibir en la petición de la API
        fields = [
            'assignment',
            'title',
            'description',
            'prediction_confidence',
            'event_time',
            'details'
        ]
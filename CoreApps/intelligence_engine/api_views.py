# CoreApps/intelligence_engine/api_views.py

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.conf import settings
from .models import PredictionEvent
from .serializers import PredictionEventCreateSerializer

# --- Medida de Seguridad: API Key Personalizada ---
class HasPredictionServiceAPIKey(permissions.BasePermission):
    """
    Permite el acceso solo si la petición incluye la API Key correcta.
    """
    def has_permission(self, request, view):
        # Compara el valor del header 'X-API-KEY' con el que guardamos en settings.py
        api_key = request.headers.get('X-API-KEY')
        return api_key == getattr(settings, 'PREDICTION_SERVICE_API_KEY', None)


class PredictionEventCreateAPIView(generics.CreateAPIView):
    """
    Endpoint para crear un nuevo evento de predicción.
    """
    queryset = PredictionEvent.objects.all()
    serializer_class = PredictionEventCreateSerializer
    # Aplicamos la seguridad: solo peticiones con la API Key correcta pasarán
    permission_classes = [HasPredictionServiceAPIKey]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # Puedes personalizar esta respuesta si quieres que devuelva algo específico
        return Response(
            {"message": "Prediction event created successfully."},
            status=status.HTTP_201_CREATED,
            headers=headers
        )
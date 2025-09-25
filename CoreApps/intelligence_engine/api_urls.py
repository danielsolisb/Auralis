# CoreApps/intelligence_engine/api_urls.py

from django.urls import path
from .api_views import PredictionEventCreateAPIView

app_name = 'intelligence_engine_api'

urlpatterns = [
    path(
        'events/create/',
        PredictionEventCreateAPIView.as_view(),
        name='create-prediction-event'
    ),
]
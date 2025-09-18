# CoreApps/rulesengine/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import RuleViewSet, SensorListView, AlertPolicyListView, StationListView

# Le damos un 'namespace' a nuestra API para poder referenciarla
app_name = 'rulesengine-api'

router = DefaultRouter()
#
# LA CORRECCIÓN ESTÁ EN ESTA LÍNEA:
# Añadimos basename='rule' para ayudar al router de DRF
#
router.register(r'rules', RuleViewSet, basename='rule')

urlpatterns = [
    path('', include(router.urls)),
    path('stations/', StationListView.as_view(), name='api-station-list'),
    path('sensors/', SensorListView.as_view(), name='api-sensor-list'),
    path('alert-policies/', AlertPolicyListView.as_view(), name='api-alertpolicy-list'),
]
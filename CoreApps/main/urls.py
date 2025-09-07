from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from .views import (
    CustomLoginView, SignUpView, DashboardView,
    DashboardMapView, DashboardMonitorView, 
    DashboardSettingsView, DashboardSupportView,
    StationDataView, DataHistoryView, DataReportView,
    get_station_sensors, get_station_data, get_station_history, 
    StationLocationsView, 
    DashboardOperatorMonitorView,  # Asegúrate de importar esta función también
    api_settings_companies,
    api_settings_stations,
    api_settings_station_detail,
    api_settings_sensors_by_station,
    api_settings_sensor_detail,
    api_settings_policy_by_sensor,
)

# Elimina esta línea redundante
# from django.urls import path
# from . import view

urlpatterns = [
    path('', CustomLoginView.as_view(), name='login'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/map/', DashboardMapView.as_view(), name='dashboard-map'),
    path('api/map/stations/', StationLocationsView.as_view(), name='api-map-stations'),
    path('dashboard/station-data/', StationDataView.as_view(), name='dashboard-station-data'),
    path('api/station-data/', get_station_data, name='get_station_data'),
    path('dashboard/data-history/', DataHistoryView.as_view(), name='dashboard-data-history'),
    path('dashboard/data-report/', DataReportView.as_view(), name='dashboard-data-report'),
    # Corrige esta línea para usar views en lugar de view
    path('dashboard/monitor/', DashboardMonitorView.as_view(), name='dashboard-monitor'),
    #Dashboard para tecnicos con visualizacion multiescala
    path('dashboard/monitor-tecnico/', DashboardOperatorMonitorView.as_view(), name='dashboard-monitor-tecnico'),

    
    # Corrige esta línea para usar views en lugar de view
    path('api/stations/<int:station_id>/sensors/', get_station_sensors, name='get_station_sensors'),
    path('api/stations/<int:station_id>/history/', get_station_history, name='get_station_history'),

    path('dashboard/settings/', DashboardSettingsView.as_view(), name='dashboard-settings'),
    path('api/settings/companies/', api_settings_companies, name='api_settings_companies'),
    path('api/settings/stations/', api_settings_stations, name='api_settings_stations'),
    path('api/settings/stations/<int:pk>/', api_settings_station_detail, name='api_settings_station_detail'),
    path('api/settings/sensors/', api_settings_sensors_by_station, name='api_settings_sensors_by_station'),   # ?station_id=#
    path('api/settings/sensors/<int:pk>/', api_settings_sensor_detail, name='api_settings_sensor_detail'),
    path('api/settings/policy/<int:sensor_id>/', api_settings_policy_by_sensor, name='api_settings_policy_by_sensor'),
    path('dashboard/support/', DashboardSupportView.as_view(), name='dashboard-support'),
    
]
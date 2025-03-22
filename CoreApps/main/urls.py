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
    get_station_sensors, get_station_data  # Asegúrate de importar esta función también
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
    path('dashboard/station-data/', StationDataView.as_view(), name='dashboard-station-data'),
    path('api/station-data/', get_station_data, name='get_station_data'),
    path('dashboard/data-history/', DataHistoryView.as_view(), name='dashboard-data-history'),
    path('dashboard/data-report/', DataReportView.as_view(), name='dashboard-data-report'),
    # Corrige esta línea para usar views en lugar de view
    path('dashboard/monitor/', DashboardMonitorView.as_view(), name='dashboard-monitor'),
    
    # Corrige esta línea para usar views en lugar de view
    path('api/stations/<int:station_id>/sensors/', get_station_sensors, name='get_station_sensors'),
    path('dashboard/settings/', DashboardSettingsView.as_view(), name='dashboard-settings'),
    path('dashboard/support/', DashboardSupportView.as_view(), name='dashboard-support'),
    
]
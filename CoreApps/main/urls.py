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
    StationDataView, DataOverviewView
)

urlpatterns = [
    path('', CustomLoginView.as_view(), name='login'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/map/', DashboardMapView.as_view(), name='dashboard-map'),
    path('dashboard/station-data/', StationDataView.as_view(), name='dashboard-station-data'),
    path('dashboard/data-overview/', DataOverviewView.as_view(), name='dashboard-data-overview'),
    path('dashboard/monitor/', DashboardMonitorView.as_view(), name='dashboard-monitor'),
    path('dashboard/settings/', DashboardSettingsView.as_view(), name='dashboard-settings'),
    path('dashboard/support/', DashboardSupportView.as_view(), name='dashboard-support'),
    path('dashboard/data-history/', DashboardSupportView.as_view(), name='dashboard-data-history'),
]
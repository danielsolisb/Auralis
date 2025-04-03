from django.shortcuts import render
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from CoreApps.users.forms import UserRegistrationForm
from django.contrib.auth import login
from CoreApps.users.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from CoreApps.sensorhub.models import Sensor, Station
from CoreApps.users.models import User
from CoreApps.measurements.models import Measurement
from CoreApps.events.models import Alarm, Warning
# Añadir esta importación para JsonResponse
from django.http import JsonResponse

from django.conf import settings
from datetime import datetime

class CustomLoginView(LoginView):
    template_name = 'main/login.html'
    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor verifica tus credenciales e intenta nuevamente.')
        return super().form_invalid(form)

class SignUpView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'main/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        form.instance.user_type = User.UserType.CLIENT
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

#class DashboardView(LoginRequiredMixin, TemplateView):
#    template_name = 'main/dashboard/main_dashboard.html'
#    login_url = 'login'
#
#    def get_context_data(self, **kwargs):
#        context = super().get_context_data(**kwargs)
#        context['title']= "Dashboard"
#        context['subtitle']= "Dashboard"
#        context['user'] = self.request.user
#        return context
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/main_dashboard.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Obtén las estaciones asociadas al usuario
        stations = Station.objects.filter(related_users=user)
        context['stations'] = stations
        
        # Cuenta de estaciones activas
        context['active_count'] = stations.filter(is_active=True).count()
        
        # Obtén los IDs de todos los sensores de las estaciones del usuario
        sensor_ids = []
        for station in stations:
            sensor_ids.extend(list(station.sensors.values_list('id', flat=True)))
        
        # Advertencias: se cuentan aquellas no reconocidas
        context['warning_count'] = Warning.objects.filter(sensor_id__in=sensor_ids, acknowledged=False).count()
        # Alarmas: se cuentan las que están activas
        context['alarm_count'] = Alarm.objects.filter(sensor_id__in=sensor_ids, is_active=True).count()

        # Prepara una lista con los datos por estación, incluyendo sus sensores y el último registro (Measurement)
        station_data = []
        for station in stations:
            sensors_list = []
            for sensor in station.sensors.all():
                last_measurement = sensor.measurements.order_by('-timestamp').first()
                sensors_list.append({
                    'id': sensor.id,
                    'name': sensor.name,
                    'last_value': last_measurement.value if last_measurement else None,
                    'last_timestamp': last_measurement.timestamp if last_measurement else None,
                })
            station_data.append({
                'id': station.id,
                'name': station.name,
                'is_active': station.is_active,
                'sensors': sensors_list,
            })
        context['station_data'] = station_data

        # Otros datos de contexto (título, subtítulo, etc.)
        context['title'] = "Dashboard"
        context['subtitle'] = "Dashboard"
        context['user'] = user
        return context

class DashboardMapView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/map.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Maps"
        context['subtitle']= "Maps"
        return context

class DashboardDataView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/data.html'
    login_url = 'login'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Data"
        context['subtitle']= "Data"
        return context

class DashboardMonitorView(LoginRequiredMixin, TemplateView):
    """
    Vista para el dashboard de monitoreo de sensores en tiempo real.
    Muestra las estaciones asociadas al usuario y permite seleccionar
    una para ver los datos de sus sensores.
    """
    template_name = 'main/dashboard/monitor.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        #stations = Station.objects.filter(owner=user)
        stations = Station.objects.filter(related_users=user)
        context['stations'] = stations
        context['mqtt_broker_ip'] = settings.MQTT_BROKER_IP  # IP del broker
        context['mqtt_broker_port'] = settings.MQTT_BROKER_PORT  # Puerto del broker
        return context

    #def get_context_data(self, **kwargs):
    #    context = super().get_context_data(**kwargs)
    #    
    #    # Obtener las estaciones asociadas al usuario actual
    #    user = self.request.user
    #    # Cambiamos user por owner para filtrar correctamente
    #    stations = Station.objects.filter(owner=user)
    #    
    #    context['stations'] = stations
    #    return context


@login_required
def get_station_sensors(request, station_id):
    """
    API para obtener los sensores asociados a una estación específica.
    Solo devuelve sensores de estaciones que pertenecen al usuario actual.
    """
    try:
        # Verificar que la estación pertenece al usuario actual
        #station = Station.objects.get(id=station_id, owner=request.user)
        station = Station.objects.get(id=station_id, related_users=request.user)

        
        # Obtener los sensores de la estación
        sensors = Sensor.objects.filter(station=station)
        
        # Preparar la respuesta
        sensors_data = []
        for sensor in sensors:
            sensors_data.append({
                'id': sensor.id,
                'name': sensor.name,
                'unit': sensor.sensor_type.unit,  # Corregido: usar sensor_type.unit
                'type': sensor.sensor_type.name,   # Corregido: usar sensor_type.name
            })
        
        return JsonResponse({
            'station_name': station.name,
            'sensors': sensors_data
        })
    
    except Station.DoesNotExist:
        return JsonResponse({'error': 'Estación no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


class DashboardSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/settings.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Settings"
        context['subtitle']= "Settings"
        return context

class DashboardSupportView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/support.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Support"
        context['subtitle']= "Support"
        return context

class StationDataView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/station_data.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Station Data"
        context['subtitle'] = "Station Data"
        # Incluir las estaciones relacionadas al usuario para el selector
        context['stations'] = Station.objects.filter(related_users=self.request.user)
        return context

@login_required
def get_station_data(request):
    station_id = request.GET.get('station_id')
    start_str = request.GET.get('start_date')  # Formato "YYYY-MM-DDTHH:mm"
    end_str = request.GET.get('end_date')      # Formato "YYYY-MM-DDTHH:mm"

    if not station_id or not start_str or not end_str:
        return JsonResponse({'error': 'Faltan parámetros: station_id, start_date y end_date'}, status=400)

    try:
        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(end_str)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha/hora inválido. Use YYYY-MM-DDTHH:MM'}, status=400)

    try:
        station = Station.objects.get(id=station_id, related_users=request.user)
    except Station.DoesNotExist:
        return JsonResponse({'error': 'Estación no encontrada'}, status=404)

    sensor_data = []
    from CoreApps.events.models import Alarm, Warning  # Asegúrate de importar estos modelos
    for sensor in station.sensors.all():
        measurements_qs = sensor.measurements.filter(timestamp__range=[start_dt, end_dt]).order_by('timestamp')
        readings = list(measurements_qs.values('timestamp', 'value', 'is_valid'))
        summary = {}
        if readings:
            values = [r['value'] for r in readings]
            max_val = max(values)
            min_val = min(values)
            avg_val = sum(values) / len(values)
            # Obtener el primer registro que tiene el valor máximo y mínimo
            max_reading = next(r for r in readings if r['value'] == max_val)
            min_reading = next(r for r in readings if r['value'] == min_val)
            summary['max_value'] = max_val
            summary['min_value'] = min_val
            summary['avg_value'] = avg_val
            summary['max_timestamp'] = max_reading['timestamp']
            summary['min_timestamp'] = min_reading['timestamp']
        else:
            summary['max_value'] = None
            summary['min_value'] = None
            summary['avg_value'] = None
            summary['max_timestamp'] = None
            summary['min_timestamp'] = None
        alarm_count = Alarm.objects.filter(sensor=sensor, timestamp__range=[start_dt, end_dt]).count()
        warning_count = Warning.objects.filter(sensor=sensor, timestamp__range=[start_dt, end_dt]).count()
        summary['total_alarms'] = alarm_count
        summary['total_warnings'] = warning_count

        sensor_data.append({
            'sensor_id': sensor.id,
            'sensor_name': sensor.name,
            'readings': readings,
            'summary': summary,
        })

    return JsonResponse({
        'station_name': station.name,
        'sensors': sensor_data
    })


#@login_required
#def get_station_data(request):
#    station_id = request.GET.get('station_id')
#    start_str = request.GET.get('start_date')  # Esto llega con formato "YYYY-MM-DDTHH:mm"
#    end_str = request.GET.get('end_date')      # Ej: "2025-03-21T08:30"
#
#    # 1. Validar que los parámetros existan
#    if not station_id or not start_str or not end_str:
#        return JsonResponse({'error': 'Faltan parámetros: station_id, start_date y end_date'}, status=400)
#
#    # 2. Intentar parsear las fechas usando fromisoformat
#    try:
#        start_dt = datetime.fromisoformat(start_str)
#        end_dt = datetime.fromisoformat(end_str)
#    except ValueError:
#        return JsonResponse({'error': 'Formato de fecha/hora inválido. Use YYYY-MM-DDTHH:MM'}, status=400)
#
#    # 3. Verificar que la estación pertenezca al usuario, etc.
#    try:
#        station = Station.objects.get(id=station_id, related_users=request.user)
#    except Station.DoesNotExist:
#        return JsonResponse({'error': 'Estación no encontrada'}, status=404)
#
#    # 4. Filtrar mediciones (Measurement) en ese rango de fechas
#    sensor_data = []
#    for sensor in station.sensors.all():
#        measurements_qs = sensor.measurements.filter(timestamp__range=[start_dt, end_dt]).order_by('timestamp')
#        readings = list(measurements_qs.values('timestamp', 'value', 'is_valid'))
#
#        sensor_data.append({
#            'sensor_id': sensor.id,
#            'sensor_name': sensor.name,
#            'readings': readings
#        })
#
#    return JsonResponse({
#        'station_name': station.name,
#        'sensors': sensor_data
#    })

class DataHistoryView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/data_history.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasamos las estaciones asociadas para el filtro (igual que en StationDataView)
        context['stations'] = Station.objects.filter(related_users=self.request.user)
        context['title'] = "Data History"
        context['subtitle'] = "Histórico de Datos"
        return context
#class DataHistoryView(LoginRequiredMixin, TemplateView):
#    template_name = 'main/dashboard/data_history.html'
#    login_url = 'login'
#    def get_context_data(self, **kwargs):
#        context = super().get_context_data(**kwargs)
#        context['title']= "Data History"
#        context['subtitle']= "Data History"
#        return context

class DataReportView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/data_report.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasar las estaciones asociadas para el filtro
        context['stations'] = Station.objects.filter(related_users=self.request.user)
        context['title'] = "Data Report"
        context['subtitle'] = "Reporte de Datos"
        return context

class CustomLogoutView(LogoutView):
    next_page = 'login'
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(request, 'session'):
            request.session.flush()
            request.session.clear()
        return response

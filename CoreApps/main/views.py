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
from CoreApps.sensorhub.models import Sensor, Station, AlertPolicy
from CoreApps.users.models import User
from CoreApps.measurements.models import Measurement
from CoreApps.events.models import Alarm, Warning
# Añadir esta importación para JsonResponse
from django.http import JsonResponse
from django.db import models

from django.conf import settings
from datetime import datetime, timedelta

from django.utils import timezone

from django.views import View
from django.db.models import Q, OuterRef, Subquery

import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.db import transaction

from CoreApps.users.models import Company
from .models import SettingAuditLog

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

        stations = Station.objects.filter(related_users=user)
        context['stations'] = stations
        context['active_count'] = stations.filter(is_active=True).count()

        sensor_ids = []
        for station in stations:
            sensor_ids.extend(list(station.sensors.values_list('id', flat=True)))

        context['warning_count'] = Warning.objects.filter(sensor_id__in=sensor_ids, acknowledged=False).count()
        context['alarm_count'] = Alarm.objects.filter(sensor_id__in=sensor_ids, is_active=True).count()

        station_data = []
        for station in stations:
            sensors_list = []
            for sensor in station.sensors.all():
                last_measurement = sensor.measurements.order_by('-measured_at').first()
                sensors_list.append({
                    'id': sensor.id,
                    'name': sensor.name,
                    'last_value': last_measurement.value if last_measurement else None,
                    'last_timestamp': last_measurement.measured_at if last_measurement else None,
                })
            station_data.append({
                'id': station.id,
                'name': station.name,
                'is_active': station.is_active,
                'sensors': sensors_list,
            })

        context['station_data'] = station_data
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

class StationLocationsView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        user = request.user

        qs = Station.objects.filter(is_active=True)
        if not user.is_superuser:
            qs = qs.filter(Q(company=user.company) | Q(related_users=user)).distinct()

        qs = qs.exclude(latitude__isnull=True).exclude(longitude__isnull=True)

        sensors_qs = Sensor.objects.select_related('sensor_type', 'station') \
                                   .filter(station__in=qs)

        from CoreApps.measurements.models import Measurement
        last_meas = Measurement.objects.filter(sensor=OuterRef('pk')).order_by('-measured_at')
        sensors_qs = sensors_qs.annotate(
            last_value=Subquery(last_meas.values('value')[:1]),
            last_ts=Subquery(last_meas.values('measured_at')[:1])
        )

        sensors_by_station = {}
        for s in sensors_qs:
            sensors_by_station.setdefault(s.station_id, []).append(s)

        stations_data = []
        for st in qs.select_related('company'):
            sensor_list = sensors_by_station.get(st.id, [])
            total_sensors = len(sensor_list)
            active_sensors = sum(1 for s in sensor_list if s.is_active)

            stations_data.append({
                "id": st.id,
                "name": st.name,
                "description": st.description or "",
                "lat": float(st.latitude),
                "lng": float(st.longitude),
                "company": st.company.name,
                "is_active": st.is_active,
                "sensor_count": total_sensors,
                "sensor_active_count": active_sensors,
                "sensors": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "unit": s.sensor_type.unit if s.sensor_type else "",
                        "is_active": s.is_active,
                        "last_value": None if s.last_value is None else float(s.last_value),
                        "last_ts": s.last_ts.isoformat() if s.last_ts else None
                    } for s in sensor_list
                ]
            })

        return JsonResponse({"stations": stations_data})


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
        context['title']= "Monitor"
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

class DashboardOperatorMonitorView(LoginRequiredMixin, TemplateView):
    """
    Vista de monitoreo multiescala (técnica) para operadores.
    - Conserva selector de estación y chips de rango (5m, 30m, 1h, 3h, 6h, 12h)
    - Un solo gráfico con múltiples ejes Y (uno por sensor), ordenados por 'site'
    - Panel derecho con último valor en vivo
    - Tiempo real por MQTT con tópico /<Estacion>/<Sensor>/
    """
    template_name = 'main/dashboard/monitor_tecnico.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        stations = Station.objects.filter(related_users=user)
        context['title'] = "Monitor Multiescala"
        context['stations'] = stations
        context['mqtt_broker_ip'] = settings.MQTT_BROKER_IP
        context['mqtt_broker_port'] = settings.MQTT_BROKER_PORT
        return context

def get_sensors_for_station(request, station_id):
    sensors = Sensor.objects.filter(station_id=station_id, is_active=True)
    sensor_list = list(sensors.values('id', 'name', 'sensor_type__unit'))
    # El resultado sería un JSON como:
    # [{"id": 1, "name": "Temperatura", "sensor_type__unit": "°C"}, {"id": 2, "name": "Humedad", "sensor_type__unit": "%"}]
    return JsonResponse(sensor_list, safe=False)

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
                'min_value': sensor.min_value,
                'max_value': sensor.max_value,
                'site': getattr(sensor, 'site', None),
                'color': getattr(sensor, 'color', None),
                'topic': sensor.name, 
            })
        
        return JsonResponse({
            'station_name': station.name,
            'sensors': sensors_data
        })
    
    except Station.DoesNotExist:
        return JsonResponse({'error': 'Estación no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_station_history(request, station_id):
    timescale = request.GET.get('timescale', '5m')
    now = timezone.now()

    if timescale == '1m':
        start_time = now - timedelta(minutes=1)
    elif timescale == '5m':
        start_time = now - timedelta(minutes=5)
    elif timescale == '30m':
        start_time = now - timedelta(minutes=30)
    elif timescale == '1h':
        start_time = now - timedelta(hours=1)
    elif timescale == '3h':
        start_time = now - timedelta(hours=3)
    elif timescale == '6h':
        start_time = now - timedelta(hours=6)
    elif timescale == '12h':
        start_time = now - timedelta(hours=12)
    else:
        start_time = now - timedelta(minutes=5)

    try:
        station = Station.objects.get(id=station_id, related_users=request.user)

        from CoreApps.measurements.models import Measurement
        measurements = (
            Measurement.objects
            .filter(sensor__station=station, measured_at__gte=start_time)
            .order_by('measured_at')
            .values('sensor_id', 'measured_at', 'value')
        )

        history_data = {}
        for m in measurements:
            sid = m['sensor_id']
            history_data.setdefault(sid, []).append([
                m['measured_at'].isoformat(),
                float(m['value']),
            ])

        return JsonResponse(history_data)

    except Station.DoesNotExist:
        return JsonResponse({'error': 'Estación no encontrada'}, status=404)

class DashboardSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/settings.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Settings"
        ctx['subtitle'] = "Settings"
        ctx['is_admin'] = self.request.user.is_staff or self.request.user.is_superuser
        return ctx

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
    start_str = request.GET.get('start_date')
    end_str = request.GET.get('end_date')

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
    from CoreApps.events.models import Alarm, Warning

    for sensor in station.sensors.all():
        qs = sensor.measurements.filter(measured_at__range=[start_dt, end_dt]).order_by('measured_at')
        raw = list(qs.values('measured_at', 'value'))

        # Aliasing para compatibilidad: devolver 'timestamp'
        readings = []
        for r in raw:
            readings.append({
                'timestamp': r['measured_at'],
                'value': r['value'],
            })

        summary = {}
        if readings:
            values = [r['value'] for r in readings]
            max_val = max(values); min_val = min(values); avg_val = sum(values) / len(values)
            max_reading = next(r for r in readings if r['value'] == max_val)
            min_reading = next(r for r in readings if r['value'] == min_val)
            summary.update({
                'max_value': max_val,
                'min_value': min_val,
                'avg_value': avg_val,
                'max_timestamp': max_reading['timestamp'],
                'min_timestamp': min_reading['timestamp'],
            })
        else:
            summary.update({
                'max_value': None, 'min_value': None, 'avg_value': None,
                'max_timestamp': None, 'min_timestamp': None,
            })

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



def is_admin(user):
    return user.is_staff or user.is_superuser

def station_queryset_for(user):
    # Admin: todas; no admin: solo las asignadas por M2M related_users
    if is_admin(user):
        return Station.objects.all()
    return Station.objects.filter(related_users=user)

def log_audit(user, action, model_name, object_id, station=None, sensor=None, changes=None):
    SettingAuditLog.objects.create(
        user=user, action=action, model_name=model_name, object_id=object_id,
        station=station, sensor=sensor, changes=changes or {}
    )

# --- Companies (para select en crear/editar estación) ---
@ensure_csrf_cookie
@login_required
@require_http_methods(["GET"])
def api_settings_companies(request):
    data = list(Company.objects.values('id', 'name'))
    return JsonResponse({'results': data})

# --- Stations list + create ---
@ensure_csrf_cookie
@login_required
@require_http_methods(["GET", "POST"])
def api_settings_stations(request):
    user = request.user
    if request.method == "GET":
        qs = station_queryset_for(user).select_related('company').order_by('name')
        out = []
        for s in qs:
            out.append({
                'id': s.id,
                'name': s.name,
                'description': s.description or '',
                'company_id': s.company_id,
                'company_name': s.company.name if s.company_id else '',
                'location': s.location,
                'latitude': float(s.latitude) if s.latitude is not None else None,
                'longitude': float(s.longitude) if s.longitude is not None else None,
            })
        return JsonResponse({'results': out})

    # POST (crear) -> solo admin
    if not is_admin(user):
        return HttpResponseForbidden("Solo administradores pueden crear estaciones.")
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    with transaction.atomic():
        s = Station.objects.create(
            name=payload.get('name','').strip(),
            description=payload.get('description','') or '',
            location=payload.get('location','') or '',
            company_id=payload.get('company_id'),
            latitude=payload.get('latitude'),
            longitude=payload.get('longitude'),
            is_active=True,
        )
        # Asignar usuarios (opcional)
        member_ids = payload.get('user_ids') or []
        if member_ids:
            s.related_users.set(member_ids)

        log_audit(user, 'create', 'Station', s.id, station=s, changes=payload)
    return JsonResponse({'ok': True, 'id': s.id})

# --- Station detail (get/update/delete) ---
@ensure_csrf_cookie
@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_settings_station_detail(request, pk):
    user = request.user
    try:
        s = Station.objects.get(pk=pk)
    except Station.DoesNotExist:
        return HttpResponseBadRequest("Estación no encontrada")

    # permiso de acceso (no-admin solo si es miembro)
    if not is_admin(user) and not s.related_users.filter(id=user.id).exists():
        return HttpResponseForbidden("No tienes acceso a esta estación.")

    if request.method == "GET":
        data = {
            'id': s.id,
            'name': s.name,
            'description': s.description or '',
            'company_id': s.company_id,
            'company_name': s.company.name if s.company_id else '',
            'location': s.location,
            'latitude': float(s.latitude) if s.latitude is not None else None,
            'longitude': float(s.longitude) if s.longitude is not None else None,
            'user_ids': list(s.related_users.values_list('id', flat=True)),
            'is_active': s.is_active,
        }
        return JsonResponse(data)

    if not is_admin(user):
        return HttpResponseForbidden("Solo administradores pueden modificar estaciones.")

    if request.method == "DELETE":
        sid = s.id
        s.delete()
        log_audit(user, 'delete', 'Station', sid, changes={})
        return JsonResponse({'ok': True})

    # PUT
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    with transaction.atomic():
        for f in ['name','description','location','company_id','latitude','longitude','is_active']:
            if f in payload:
                setattr(s, f if f!='company_id' else 'company_id', payload[f])
        s.save()
        if 'user_ids' in payload:
            s.related_users.set(payload.get('user_ids') or [])
        log_audit(user, 'update', 'Station', s.id, station=s, changes=payload)
    return JsonResponse({'ok': True})

# --- Sensors by station (list) ---
@ensure_csrf_cookie
@login_required
@require_http_methods(["GET"])
def api_settings_sensors_by_station(request):
    user = request.user
    station_id = request.GET.get('station_id')
    if not station_id:
        return HttpResponseBadRequest("station_id requerido")
    # acceso
    if not station_queryset_for(user).filter(id=station_id).exists():
        return HttpResponseForbidden("No tienes acceso a esta estación.")

    sensors = Sensor.objects.filter(station_id=station_id).order_by('site','name')
    out = []
    for x in sensors:
        out.append({
            'id': x.id,
            'name': x.name,
            'unit': x.sensor_type.unit if x.sensor_type_id else '',  # unidad por tipo
            'color': x.color or '',
            'site': x.site or '',
            'min_value': x.min_value,
            'max_value': x.max_value,
            'is_active': x.is_active,
        })
    return JsonResponse({'results': out})

# --- Sensor create/update ---
@ensure_csrf_cookie
@login_required
@require_http_methods(["POST", "PUT"])
def api_settings_sensor_detail(request, pk=None):
    user = request.user
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    # Crear sensor (solo admin)
    if request.method == "POST":
        if not is_admin(user):
            return HttpResponseForbidden("Solo administradores pueden crear sensores.")
        station_id = payload.get('station_id')
        sensor_type_id = payload.get('sensor_type_id')
        if not station_id or not sensor_type_id:
            return HttpResponseBadRequest("station_id y sensor_type_id son requeridos")
        # acceso estación
        if not station_queryset_for(user).filter(id=station_id).exists():
            return HttpResponseForbidden("No tienes acceso a esa estación.")
        with transaction.atomic():
            s = Sensor.objects.create(
                station_id=station_id,
                sensor_type_id=sensor_type_id,
                name=payload.get('name','').strip(),
                color=payload.get('color') or '#3b82f6',
                site=str(payload.get('site','') or ''),
                min_value=payload.get('min_value'),
                max_value=payload.get('max_value'),
                is_active=payload.get('is_active', True),
            )
            log_audit(user, 'create', 'Sensor', s.id, station=s.station, sensor=s, changes=payload)
        return JsonResponse({'ok': True, 'id': s.id})

    # PUT (editar sensor)
    try:
        s = Sensor.objects.get(pk=pk)
    except Sensor.DoesNotExist:
        return HttpResponseBadRequest("Sensor no encontrado")
    # acceso estación
    if not station_queryset_for(user).filter(id=s.station_id).exists():
        return HttpResponseForbidden("No tienes acceso a esta estación.")

    # Campos editables:
    if is_admin(user):
        allowed = {'name','color','site','min_value','max_value','is_active','sensor_type_id'}
    else:
        # usuario no admin: solo estos (como pediste)
        allowed = {'color','site','min_value','max_value'}
        # unidad: viene de SensorType; si quieres que cambien unidad sin cambiar tipo,
        # tendríamos que separar unit en Sensor; por ahora unit = sensor_type.unit (read-only)

    changes = {}
    with transaction.atomic():
        for f,v in payload.items():
            if f in allowed:
                old = getattr(s, f)
                if f == 'site':
                    v = str(v) if v is not None else ''
                if old != v:
                    setattr(s, f, v)
                    changes[f] = {'old': old, 'new': v}
        if changes:
            s.save()
            log_audit(user, 'update', 'Sensor', s.id, station=s.station, sensor=s, changes=changes)
    return JsonResponse({'ok': True, 'changed': list(changes.keys())})

# --- AlertPolicy por sensor (1:1) ---
@ensure_csrf_cookie
@login_required
@require_http_methods(["GET", "POST", "PUT"])
def api_settings_policy_by_sensor(request, sensor_id):
    user = request.user
    try:
        sensor = Sensor.objects.select_related('station','sensor_type').get(pk=sensor_id)
    except Sensor.DoesNotExist:
        return HttpResponseBadRequest("Sensor no encontrado")

    # acceso estación
    if not station_queryset_for(user).filter(id=sensor.station_id).exists():
        return HttpResponseForbidden("No tienes acceso a esta estación.")

    try:
        policy = AlertPolicy.objects.get(sensor=sensor)
    except AlertPolicy.DoesNotExist:
        policy = None

    if request.method == "GET":
        data = {
            'sensor_id': sensor.id,
            'sensor_unit': sensor.sensor_type.unit if sensor.sensor_type_id else '',
            'sensor_min': sensor.min_value,
            'sensor_max': sensor.max_value,
            'exists': bool(policy),
        }
        if policy:
            data.update({
                'id': policy.id,
                'alert_mode': policy.alert_mode,
                'warn_low': policy.warn_low, 'alert_low': policy.alert_low,
                'warn_high': policy.warn_high, 'alert_high': policy.alert_high,
                'enable_low_thresholds': policy.enable_low_thresholds,
                'hysteresis': policy.hysteresis,
                'persistence_seconds': policy.persistence_seconds,
                'bands_active': policy.bands_active,
                'color_warn': policy.color_warn,
                'color_alert': policy.color_alert,
            })
        return JsonResponse(data)

    # Crear policy (solo admin)
    if request.method == "POST":
        if policy:
            return HttpResponseBadRequest("Ya existe una política para este sensor.")
        if not is_admin(user):
            return HttpResponseForbidden("Solo administradores pueden crear políticas.")
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest("JSON inválido")
        with transaction.atomic():
            p = AlertPolicy.objects.create(sensor=sensor, **payload)
            log_audit(user, 'create', 'AlertPolicy', p.id, station=sensor.station, sensor=sensor, changes=payload)
        return JsonResponse({'ok': True, 'id': p.id})

    # Editar policy
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")
    if not policy:
        return HttpResponseBadRequest("No existe política para este sensor. (Crea con POST)")

    # No admin: solo 4 campos
    if not is_admin(user):
        whitelist = {'warn_low','alert_low','warn_high','alert_high'}
        payload = {k:v for k,v in payload.items() if k in whitelist}

    changes = {}
    with transaction.atomic():
        for k,v in payload.items():
            old = getattr(policy, k)
            if old != v:
                setattr(policy, k, v)
                changes[k] = {'old': old, 'new': v}
        if changes:
            policy.save()
            log_audit(user, 'update', 'AlertPolicy', policy.id, station=sensor.station, sensor=sensor, changes=changes)

    return JsonResponse({'ok': True})

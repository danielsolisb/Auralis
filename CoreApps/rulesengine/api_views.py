# CoreApps/rulesengine/api_views.py
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from django.db import transaction
from .models import Rule, Condition, RuleNode
from .serializers import (
    RuleListSerializer, 
    RuleDetailSerializer, 
    SensorSerializer, 
    AlertPolicySerializer,
    StationSerializer
)
from CoreApps.sensorhub.models import Sensor, AlertPolicy, Station

# Vista para listar las estaciones a las que el usuario tiene acceso
class StationListView(generics.ListAPIView):
    serializer_class = StationSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # --- LOGS DE DIAGNÓSTICO AÑADIDOS ---
        print("\n--- [API] Petición recibida en StationListView ---")
        user = self.request.user
        print(f"[API] Usuario autenticado: {user.email}")
        
        if hasattr(user, 'company') and user.company:
            print(f"[API] Compañía del usuario: {user.company.name} (ID: {user.company.id})")
            print(f"[API] ¿Es dueño de la plataforma?: {user.company.is_platform_owner}")

            if user.company.is_platform_owner:
                queryset = Station.objects.filter(is_active=True)
                print(f"[API] Acceso de Dueño: Se encontraron {queryset.count()} estaciones activas.")
                return queryset
            
            queryset = Station.objects.filter(company=user.company, is_active=True)
            print(f"[API] Acceso de Compañía: Se encontraron {queryset.count()} estaciones para esta compañía.")
            return queryset
            
        print("[API] El usuario no tiene una compañía asignada. Devolviendo lista vacía.")
        return Station.objects.none()

# Vistas de solo lectura para poblar el editor
class SensorListView(generics.ListAPIView):
    serializer_class = SensorSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Sensor.objects.none() 

        if hasattr(user, 'company') and user.company:
            if user.company.is_platform_owner:
                queryset = Sensor.objects.filter(is_active=True)
            else:
                queryset = Sensor.objects.filter(is_active=True, station__company=user.company)

        station_id = self.request.query_params.get('station_id', None)
        if station_id:
            queryset = queryset.filter(station_id=station_id)

        return queryset.select_related('station', 'sensor_type')

class AlertPolicyListView(generics.ListAPIView):
    queryset = AlertPolicy.objects.filter(bands_active=True)
    serializer_class = AlertPolicySerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]


class RuleViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtra las reglas para que solo muestre las de la compañía del usuario.
        """
        user = self.request.user
        if hasattr(user, 'company') and user.company:
            if user.company.is_platform_owner:
                return Rule.objects.all()
            return Rule.objects.filter(company=user.company)
        return Rule.objects.none()

    def get_serializer_class(self):
        """
        Usa un serializer simple para la lista y uno detallado para una sola regla.
        """
        if self.action == 'list':
            return RuleListSerializer
        return RuleDetailSerializer

    def get_serializer_context(self):
        """
        Pasa el objeto 'request' al serializador.
        Esto es necesario para que en el serializer podamos acceder a request.user.
        """
        return {'request': self.request}

    def perform_create(self, serializer):
        """
        Al crear una regla, DRF llama a este método.
        Nosotros no necesitamos hacer nada extra aquí porque toda la lógica
        está ahora en el método .create() del serializador.
        """
        serializer.save()

    def update(self, request, *args, **kwargs):
        """
        La lógica de actualización se queda como estaba, ya que funcionaba correctamente.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                # Borramos los nodos antiguos para reconstruir el árbol
                instance.nodes.all().delete()

                # Actualizamos los campos de la regla principal
                # Usamos serializer.save() que maneja la actualización de los campos
                instance = serializer.save()

                # Guardamos la nueva estructura de nodos
                nodes_data = serializer.validated_data.get('nodes_data', [])
                if nodes_data:
                    # Para la actualización, llamamos a la función del serializador manualmente
                    serializer._save_nodes_recursively(instance, None, nodes_data)

            read_serializer = RuleDetailSerializer(instance)
            return Response(read_serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    # --- NUEVA FUNCIÓN AUXILIAR RECURSIVA ---
    def _save_nodes_recursively(self, rule, parent_node, nodes_data, condition_counter=None):
        """
        Función auxiliar que recorre la estructura de nodos y los crea en la BD,
        generando nombres de condición dinámicos.
        """
        # Inicializamos el contador si es la primera llamada (nodo raíz)
        if condition_counter is None:
            condition_counter = [1]  # Usamos una lista como contador mutable para la recursión

        for node_data in nodes_data:
            condition_instance = None
            if node_data.get('condition'):
                condition_data = node_data['condition']
                
                # --- INICIO DE LA MEJORA ---
                # 1. Eliminamos el nombre genérico que viene del frontend.
                condition_data.pop('name', None) 
                
                # 2. Creamos un nombre descriptivo y único para la condición.
                new_condition_name = f"Cond_{condition_counter[0]}_{rule.name[:20]}"
                condition_data['name'] = new_condition_name
                condition_counter[0] += 1 # Incrementamos el contador para la siguiente condición.
                # --- FIN DE LA MEJORA ---

                # La lógica para obtener el sensor y crear la instancia no cambia.
                sensor_id = condition_data.pop('source_sensor')
                try:
                    sensor_instance = Sensor.objects.get(pk=sensor_id)
                except Sensor.DoesNotExist:
                    raise Exception(f"El sensor con ID {sensor_id} no fue encontrado.")

                condition_instance = Condition.objects.create(
                    source_sensor=sensor_instance, 
                    **condition_data
                )
            
            current_node = RuleNode.objects.create(
                rule=rule,
                parent=parent_node,
                node_type=node_data['node_type'],
                logical_operator=node_data.get('logical_operator'),
                condition=condition_instance
            )

            if 'children' in node_data and node_data['children']:
                # Pasamos el contador a las llamadas recursivas.
                self._save_nodes_recursively(rule, current_node, node_data['children'], condition_counter)


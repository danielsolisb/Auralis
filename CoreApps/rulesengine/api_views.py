# CoreApps/rulesengine/api_views.py
from rest_framework import viewsets, generics, response, status
from django.db import transaction # Importar transaction
from .models import Rule, Condition, RuleNode
from .serializers import RuleSerializer, RuleDetailSerializer, SensorSerializer, AlertPolicySerializer 
#from .serializers import RuleSerializer, SensorSerializer, AlertPolicySerializer, ConditionSerializer, RuleNodeSerializer
from CoreApps.sensorhub.models import Sensor, AlertPolicy


class RuleViewSet(viewsets.ModelViewSet):
    # Retiramos el queryset de aquí
    serializer_class = RuleSerializer 
    # Aquí añadiríamos la lógica de permisos más adelante

    def get_queryset(self):
        """
        CORREGIDO: Ahora, si el usuario pertenece a la empresa dueña de la plataforma,
        podrá ver las reglas de todas las empresas. De lo contrario, solo ve las suyas.
        """
        user = self.request.user
        if not user.is_authenticated or not user.company:
            return Rule.objects.none()

        # Si la compañía del usuario es la dueña de la plataforma, mostramos todo.
        if user.company.is_platform_owner:
            return Rule.objects.all()
        
        # Si no, filtramos por su compañía.
        return Rule.objects.filter(company=user.company)

    def get_serializer_class(self):
        # Usamos un serializer detallado para la vista de un solo objeto
        if self.action == 'retrieve' or self.action == 'update':
            return RuleDetailSerializer
        return RuleSerializer

    def _create_nodes_recursively(self, rule, parent_node_obj, nodes_data):
        """Función auxiliar recursiva para crear el árbol de nodos."""
        for node_data in nodes_data:
            condition = None
            # Si es un nodo de condición, creamos la condición primero
            if node_data.get('node_type') == 'COND' and 'condition_data' in node_data:
                condition = Condition.objects.create(**node_data['condition_data'])

            # Creamos el objeto RuleNode
            current_node_obj = RuleNode.objects.create(
                rule=rule,
                parent=parent_node_obj,
                node_type=node_data['node_type'],
                condition=condition,
                logical_operator=node_data.get('logical_operator')
            )

            # Si tiene hijos, llamamos a la función de nuevo para ellos
            if 'children' in node_data and node_data['children']:
                self._create_nodes_recursively(rule, current_node_obj, node_data['children'])
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Sobrescribe el método para crear una nueva regla y todo su árbol de nodos.
        """
        rule_data = request.data
        nodes_data = rule_data.pop('nodes', [])

        # Asignamos la empresa del usuario automáticamente
        rule_data['company_id'] = request.user.company_id
        
        serializer = self.get_serializer(data=rule_data)
        serializer.is_valid(raise_exception=True)
        rule = serializer.save()

        # Creamos los nodos recursivamente (sin padre al inicio)
        self._create_nodes_recursively(rule, None, nodes_data)

        headers = self.get_success_headers(serializer.data)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Sobrescribe el método para actualizar una regla y reconstruir su árbol de nodos.
        """
        instance = self.get_object()
        rule_data = request.data
        nodes_data = rule_data.pop('nodes', [])

        serializer = self.get_serializer(instance, data=rule_data, partial=True)
        serializer.is_valid(raise_exception=True)
        rule = serializer.save()
        
        # La forma más sencilla de actualizar es borrar y volver a crear el árbol
        rule.nodes.all().delete()
        Condition.objects.filter(rulenode__rule=rule).delete() # Borra condiciones huérfanas
        
        self._create_nodes_recursively(rule, None, nodes_data)

        return response.Response(serializer.data)

# Vistas de solo lectura para poblar el editor
class SensorListView(generics.ListAPIView):
    queryset = Sensor.objects.filter(is_active=True)
    serializer_class = SensorSerializer

class AlertPolicyListView(generics.ListAPIView):
    queryset = AlertPolicy.objects.filter(bands_active=True)
    serializer_class = AlertPolicySerializer
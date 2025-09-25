# CoreApps/rulesengine/serializers.py
from rest_framework import serializers
from .models import Rule, Condition, RuleNode
from CoreApps.sensorhub.models import Sensor, AlertPolicy, Station
from django.db import transaction

class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ['id', 'name']

# Serializers de solo lectura
class SensorSerializer(serializers.ModelSerializer):
    # Crea un campo "display_name" combinando el nombre de la estación y el del sensor
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Sensor
        fields = ['id', 'display_name']

    def get_display_name(self, obj):
        return f"{obj.station.name} - {obj.name}"


class AlertPolicySerializer(serializers.ModelSerializer):
    label = serializers.CharField(source='__str__', read_only=True)
    class Meta:
        model = AlertPolicy
        fields = ['id', 'label']

class ConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = '__all__'

# Este serializer ahora se encargará de la recursión para mostrar el árbol
class RuleNodeSerializer(serializers.ModelSerializer):
    condition = ConditionSerializer(read_only=True)
    # DRF puede manejar la recursión si lo definimos así:
    children = serializers.SerializerMethodField()

    class Meta:
        model = RuleNode
        fields = ['id', 'node_type', 'logical_operator', 'condition', 'children']
    
    def get_children(self, obj):
        # Para cada hijo, usamos este mismo serializer.
        return RuleNodeSerializer(obj.children.all(), many=True).data

# Serializer para la VISTA DE LISTA (simple)
class RuleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = ['id', 'name']

# Serializer para la VISTA DE DETALLE (completo, con el árbol de nodos)
class RuleDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de detalle que maneja tanto la lectura del árbol de nodos
    como la escritura de la estructura completa de la regla.
    """
    # Para LEER (mostrar el grafo)
    nodes = serializers.SerializerMethodField(read_only=True)

    # Para ESCRIBIR (guardar el grafo)
    nodes_data = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = Rule
        fields = [
            'id', 'name', 'description', 'severity', 'is_active', 
            'nodes', 'nodes_data'
        ]

    def get_nodes(self, instance):
        # La lógica de lectura no cambia: busca los nodos raíz.
        root_nodes = instance.nodes.filter(parent__isnull=True)
        return RuleNodeReadSerializer(root_nodes, many=True).data

    def _save_nodes_recursively(self, rule, parent_node, nodes_data, condition_counter=None):
        """
        Función auxiliar que recorre la estructura de nodos y los crea en la BD.
        """
        if condition_counter is None:
            condition_counter = [1]

        for node_data in nodes_data:
            condition_instance = None
            if node_data.get('condition'):
                condition_data = node_data['condition']

                new_condition_name = f"Cond_{condition_counter[0]}_{rule.name[:20]}"
                condition_data['name'] = new_condition_name
                condition_counter[0] += 1

                sensor_id = condition_data.pop('source_sensor')
                try:
                    sensor_instance = Sensor.objects.get(pk=sensor_id)
                except Sensor.DoesNotExist:
                    raise serializers.ValidationError(f"El sensor con ID {sensor_id} no fue encontrado.")

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
                self._save_nodes_recursively(rule, current_node, node_data['children'], condition_counter)

    def create(self, validated_data):
        # Obtenemos la compañía desde el contexto que pasará la vista.
        company = self.context['request'].user.company
        if not company:
            raise serializers.ValidationError("El usuario no tiene una compañía asignada.")

        # Extraemos los datos de los nodos antes de crear la regla.
        nodes_data = validated_data.pop('nodes_data', [])

        try:
            with transaction.atomic():
                # Creamos la regla principal con los datos restantes.
                rule_instance = Rule.objects.create(company=company, **validated_data)

                # Si hay nodos, los creamos recursivamente.
                if nodes_data:
                    self._save_nodes_recursively(rule_instance, None, nodes_data)

            return rule_instance
        except Exception as e:
            raise serializers.ValidationError(str(e))
            
#escritura
class ConditionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        # Incluimos todos los campos necesarios para crear una condición
        fields = [
            'name', 'source_sensor', 'metric_to_evaluate', 'operator', 
            'threshold_type', 'threshold_config', 'linked_policy'
        ]

class RuleNodeWriteSerializer(serializers.ModelSerializer):
    # Permite recibir datos anidados para la condición y los hijos
    condition = ConditionWriteSerializer(required=False, allow_null=True)
    children = serializers.ListField(child=serializers.DictField(), required=False)

    class Meta:
        model = RuleNode
        fields = ['node_type', 'logical_operator', 'condition', 'children']

# --- Serializer Principal (modificado para lectura y escritura) ---

class RuleNodeReadSerializer(serializers.ModelSerializer):
    """Serializer de solo lectura para mostrar el árbol de nodos."""
    condition = ConditionWriteSerializer(read_only=True) # Usamos el serializer de escritura como base
    children = serializers.SerializerMethodField()

    class Meta:
        model = RuleNode
        fields = ['id', 'node_type', 'logical_operator', 'condition', 'children']
    
    def get_children(self, obj):
        return RuleNodeReadSerializer(obj.children.all(), many=True).data
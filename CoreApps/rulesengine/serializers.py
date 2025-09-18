# CoreApps/rulesengine/serializers.py
from rest_framework import serializers
from .models import Rule, Condition, RuleNode
from CoreApps.sensorhub.models import Sensor, AlertPolicy, Station

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
    # Acepta una lista de diccionarios que representa la estructura del árbol.
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
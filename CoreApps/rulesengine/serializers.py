# CoreApps/rulesengine/serializers.py
from rest_framework import serializers
from .models import Rule, Condition, RuleNode
from CoreApps.sensorhub.models import Sensor, AlertPolicy

# Serializers de solo lectura
class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ['id', 'name']

class AlertPolicySerializer(serializers.ModelSerializer):
    label = serializers.CharField(source='__str__', read_only=True)
    class Meta:
        model = AlertPolicy
        fields = ['id', 'label']

class ConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = '__all__'

# --- CORRECCIÓN CLAVE ---
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
    nodes = serializers.SerializerMethodField()

    class Meta:
        model = Rule
        fields = ['id', 'name', 'description', 'severity', 'is_active', 'nodes']

    def get_nodes(self, instance):
        # Buscamos los nodos que no tienen padre (la raíz del árbol)
        root_nodes = instance.nodes.filter(parent__isnull=True)
        return RuleNodeSerializer(root_nodes, many=True).data
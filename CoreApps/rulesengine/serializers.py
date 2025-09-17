# CoreApps/rulesengine/serializers.py
from rest_framework import serializers
from .models import Rule, Condition, RuleNode
from CoreApps.sensorhub.models import Sensor, AlertPolicy

# Serializer para listar Sensores (solo lectura)
class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ['id', 'name', 'station'] # Lo que el frontend necesita para mostrar

# Serializer para listar Políticas de Alerta (solo lectura)
class AlertPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertPolicy
        fields = ['id', 'scope', '__str__'] # Usamos __str__ para un nombre descriptivo

# Serializers para las Reglas (lectura y escritura)
class ConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = '__all__'


class RuleNodeSerializer(serializers.ModelSerializer):
    # Al leer, usamos un serializador anidado para mostrar los datos de la condición
    condition = ConditionSerializer(read_only=True) 
    # Usamos recursión para los hijos
    children = serializers.SerializerMethodField()

    class Meta:
        model = RuleNode
        # Al escribir, solo necesitamos el ID de la condición
        fields = ['id', 'node_type', 'condition', 'logical_operator', 'children']

    def get_children(self, obj):
        # Evita la recursión infinita
        if 'no_children' in self.context:
            return []
        # Serializa los hijos del nodo
        return RuleNodeSerializer(obj.children.all(), many=True, context=self.context).data



class RuleSerializer(serializers.ModelSerializer):
    # Anidamos el nodo raíz del árbol de reglas
    nodes = RuleNodeSerializer(many=True, read_only=True)

    class Meta:
        model = Rule
        fields = ['id', 'name', 'description', 'company', 'severity', 'is_active', 'nodes']

class RuleDetailSerializer(serializers.ModelSerializer):
    # Usamos un SerializerMethodField para obtener solo los nodos raíz (sin padre)
    nodes = serializers.SerializerMethodField()

    class Meta:
        model = Rule
        fields = ['id', 'name', 'description', 'company', 'severity', 'is_active', 'nodes']

    def get_nodes(self, obj):
        # Filtramos por nodos que no tienen padre para empezar el árbol
        root_nodes = obj.nodes.filter(parent__isnull=True)
        return RuleNodeSerializer(root_nodes, many=True).data
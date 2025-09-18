# CoreApps/rulesengine/api_views.py
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
# --- ¡NUEVAS IMPORTACIONES! ---
from rest_framework.authentication import SessionAuthentication
from .models import Rule
from .serializers import RuleListSerializer, RuleDetailSerializer, SensorSerializer, AlertPolicySerializer 
from CoreApps.sensorhub.models import Sensor, AlertPolicy

# Vistas de solo lectura para poblar el editor
class SensorListView(generics.ListAPIView):
    queryset = Sensor.objects.filter(is_active=True).select_related('station')
    serializer_class = SensorSerializer
    authentication_classes = [SessionAuthentication] # Aseguramos que use la sesión
    permission_classes = [IsAuthenticated]

class AlertPolicyListView(generics.ListAPIView):
    queryset = AlertPolicy.objects.filter(bands_active=True)
    serializer_class = AlertPolicySerializer
    authentication_classes = [SessionAuthentication] # Aseguramos que use la sesión
    permission_classes = [IsAuthenticated]

class RuleViewSet(viewsets.ModelViewSet):
    # --- CORRECCIÓN CLAVE: Forzamos el método de autenticación ---
    # Con esto, le decimos a esta vista que SIEMPRE intente usar la sesión
    # de Django para autenticar al usuario. Esto anula cualquier conflicto.
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Esta lógica ahora funcionará, ya que 'request.user' será el usuario correcto.
        """
        user = self.request.user
        
        # --- LOGS PARA DEPURACIÓN (Ahora son seguros) ---
        print(f"\n--- [API] Comprobando permisos para el usuario: {user.email} ---")
        if hasattr(user, 'company') and user.company:
            print(f"[API] ID de la compañía del usuario: {user.company.id}")
            print(f"[API] ¿Es dueño de la plataforma?: {user.company.is_platform_owner}")

            if user.company.is_platform_owner:
                print("[API] Acceso como Dueño de Plataforma: Devolviendo TODAS las reglas.")
                return Rule.objects.all()
            
            print(f"[API] Acceso de usuario normal: Filtrando reglas por company_id = {user.company.id}")
            return Rule.objects.filter(company=user.company)
        
        print("[API] El usuario no tiene compañía asignada. Devolviendo conjunto vacío.")
        return Rule.objects.none()

    def get_serializer_class(self):
        """
        Usa un serializer simple para la lista y uno detallado para una sola regla.
        """
        if self.action == 'list':
            return RuleListSerializer
        return RuleDetailSerializer


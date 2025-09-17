# CoreApps/rulesengine/views.py

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class RuleEditorView(LoginRequiredMixin, TemplateView):
    """
    Vista Basada en Clase para renderizar el editor de reglas.
    - LoginRequiredMixin: Asegura que solo usuarios autenticados puedan acceder.
    - TemplateView: Se encarga de mostrar la plantilla especificada.
    """
    template_name = 'main/rulesengine/editor.html'

    def get_context_data(self, **kwargs):
        # Llamamos al método base primero para obtener el contexto
        context = super().get_context_data(**kwargs)
        # Añadimos nuestro contexto personalizado
        context['page_title'] = 'Editor de Reglas'
        context['title'] = 'Editor de Reglas' # Para la lógica de "active" en tu menú
        return context
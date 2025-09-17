# CoreApps/rulesengine/urls.py

from django.urls import path
#from . import views
from .views import RuleEditorView

# Este es el 'namespace' que nos permitirá referirnos a estas URLs fácilmente
app_name = 'rulesengine'

urlpatterns = [
    # URL para mostrar el editor visual
    path('editor/', RuleEditorView.as_view(), name='rulesengine-editor'),
]
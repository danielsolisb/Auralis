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

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class DashboardMapView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/map.html'
    login_url = 'login'

class DashboardDataView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/data.html'
    login_url = 'login'

class DashboardMonitorView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/monitor.html'
    login_url = 'login'

class DashboardSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/settings.html'
    login_url = 'login'

class DashboardSupportView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/support.html'
    login_url = 'login'

class StationDataView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/station_data.html'
    login_url = 'login'

class DataOverviewView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/data_overview.html'
    login_url = 'login'

class CustomLogoutView(LogoutView):
    next_page = 'login'
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(request, 'session'):
            request.session.flush()
            request.session.clear()
        return response

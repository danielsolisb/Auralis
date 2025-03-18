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
    template_name = 'main/dashboard/main_dashboard.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Dashboard"
        context['subtitle']= "Dashboard"
        context['user'] = self.request.user
        return context

class DashboardMapView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/map.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Maps"
        context['subtitle']= "Maps"
        return context

class DashboardDataView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/data.html'
    login_url = 'login'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Data"
        context['subtitle']= "Data"
        return context

class DashboardMonitorView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/monitor.html'
    login_url = 'login'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Monitor"
        context['subtitle']= "Monitor"
        return context

class DashboardSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/settings.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Settings"
        context['subtitle']= "Settings"
        return context

class DashboardSupportView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/support.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Support"
        context['subtitle']= "Support"
        return context

class StationDataView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/station_data.html'
    login_url = 'login'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Station Data"
        context['subtitle']= "Station Data"
        return context

class DataOverviewView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard/data_overview.html'
    login_url = 'login'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']= "Data Overview"
        context['subtitle']= "Data Overview"
        return context

class CustomLogoutView(LogoutView):
    next_page = 'login'
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(request, 'session'):
            request.session.flush()
            request.session.clear()
        return response

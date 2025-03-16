from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'identification_type', 
                 'identification_number', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aseguramos que el usuario será de tipo CLIENT
        self.instance.user_type = User.UserType.CLIENT

    def clean(self):
        cleaned_data = super().clean()
        # No necesitamos validar company para clientes
        self.instance._skip_company_validation = True
        return cleaned_data
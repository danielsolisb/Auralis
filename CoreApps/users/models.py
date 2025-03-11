from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El Email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', User.UserType.SUPERUSER)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    class UserType(models.TextChoices):
        SUPERUSER = 'SU', _('Superuser')
        ADMIN = 'AD', _('Administrador')
        CLIENT = 'CL', _('Cliente')
        SUPERVISOR = 'SV', _('Supervisor')
        OPERATOR = 'OP', _('Operador')
        INSTALLER = 'IN', _('Instalador')

    COMPANY_REQUIRED_TYPES = ['AD', 'CL', 'SV', 'OP']

    username = None
    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(
        max_length=2,
        choices=UserType.choices,
        default=UserType.OPERATOR,
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text=_('Requerido para administradores, clientes, supervisores y operadores')
    )
    identification_type = models.CharField(
        max_length=3,
        choices=[
            ('DNI', 'Cédula'),
            ('PAS', 'Pasaporte'),
        ],
        default='DNI'
    )
    identification_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='Para cédula: Ingrese exactamente 10 dígitos numéricos',
            )
        ]
    )
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['identification_number', 'identification_type']

    class Meta:
        verbose_name = _('usuario')
        verbose_name_plural = _('usuarios')

    def clean(self):
        super().clean()
        if self.user_type in self.COMPANY_REQUIRED_TYPES and not self.company:
            raise ValidationError({
                'company': _('La empresa es obligatoria para este tipo de usuario')
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Company(models.Model):
    name = models.CharField(max_length=100)
    ruc = models.CharField(max_length=13, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_platform_owner = models.BooleanField(
        _('empresa dueña de plataforma'),
        default=False,
        help_text=_('Indica si esta empresa es la dueña de la plataforma')
    )

    class Meta:
        verbose_name = _('empresa')
        verbose_name_plural = _('empresas')

    def __str__(self):
        return self.name

class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    department = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class EmployeeHistory(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='history')
    position = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    change_reason = models.TextField()

    class Meta:
        verbose_name = _('historial de empleado')
        verbose_name_plural = _('historiales de empleados')

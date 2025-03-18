from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, EmployeeProfile, EmployeeHistory

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'identification_number', 'user_type', 'company', 'is_active')
    search_fields = ('email', 'identification_number')
    ordering = ('email',)
    list_filter = ('user_type', 'is_active', 'company')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'identification_type', 'identification_number', 'profile_image')}),
        ('Permisos', {'fields': ('user_type', 'company', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'identification_type', 'identification_number', 'user_type', 'company'),
        }),
    )

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'ruc', 'email', 'phone')
    search_fields = ('name', 'ruc')
    ordering = ('name',)

class EmployeeHistoryInline(admin.TabularInline):
    model = EmployeeHistory
    extra = 1

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'get_company')
    search_fields = ('user__email', 'department')
    inlines = [EmployeeHistoryInline]

    def get_company(self, obj):
        return obj.user.company
    get_company.short_description = 'Empresa'
    get_company.admin_order_field = 'user__company'

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser,Partenaire



@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'order')
    list_editable = ('is_active', 'order')

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'is_superuser')
    search_fields = ('username', 'email', 'nom', 'prenom')
    ordering = ('date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        ('Infos personnelles', {
            'fields': ('phone_number', 'profile_picture', 'bio', 'job_title', 'department',
                       'social_facebook', 'social_linkedin', 'social_twitter')
        }),
        ('Rôle et dates', {
            'fields': ('role', 'date_started')
        }),
    )

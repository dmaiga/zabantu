# intervenants/admin.py
from django.contrib import admin
from .models import Intervenant

@admin.register(Intervenant)
class IntervenantAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'organization', 'intervenant_type', 'is_available')
    list_filter = ('intervenant_type', 'is_available', 'organization')
    search_fields = ('first_name', 'last_name', 'organization', 'email')
    list_editable = ('is_available',)
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'photo')
        }),
        ('Informations professionnelles', {
            'fields': ('organization', 'position', 'intervenant_type', 'expertise', 'bio')
        }),
        ('Réseaux sociaux', {
            'fields': ('linkedin', 'twitter', 'website'),
            'classes': ('collapse',)
        }),
        ('Disponibilité', {
            'fields': ('is_available', 'note_internal'),
            'classes': ('collapse',)
        }),
    )
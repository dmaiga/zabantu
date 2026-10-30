from django.contrib import admin
from .models import Event, EventIntervenant

class EventIntervenantInline(admin.TabularInline):
    model = EventIntervenant
    extra = 1
    autocomplete_fields = ['intervenant']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'date', 'status', 'is_webinar', 'participants_count')
    list_filter = ('status', 'event_type', 'is_webinar', 'date')  # Remplacer is_published par status
    search_fields = ('title', 'content', 'primary_topic')
    readonly_fields = ('created_at', 'updated_at', 'published_at', 'participants_count_display')
    list_editable = ('status',)  # Permettre de modifier le statut directement depuis la liste
    
    # Ajouter l'inline pour gérer les intervenants
    inlines = [EventIntervenantInline]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'event_type', 'content', 'image', 'status', 'is_featured')
        }),
        ('Dates et lieu', {
            'fields': ('date', 'end_date', 'location', 'lieu_gps')
        }),
        ('Webinaire', {
            'fields': ('is_webinar', 'webinar_link'),
            'classes': ('collapse',)
        }),
        ('Métadonnées pour analyse', {
            'fields': ('target_audience', 'expected_attendees', 'primary_topic', 'secondary_topics'),
            'classes': ('collapse',)
        }),
        ('Informations techniques', {
            'fields': ('author', 'created_at', 'updated_at', 'published_at', 'participants_count_display'),
            'classes': ('collapse',)
        }),
    )
    
    def participants_count(self, obj):
        return obj.intervenants.count()
    participants_count.short_description = 'Participants'
    
    def participants_count_display(self, obj):
        return self.participants_count(obj)
    participants_count_display.short_description = 'Total participants'
    
    def get_queryset(self, request):
        # Optimiser les requêtes pour éviter le N+1
        return super().get_queryset(request).prefetch_related('intervenants')

@admin.register(EventIntervenant)
class EventIntervenantAdmin(admin.ModelAdmin):
    list_display = ('intervenant', 'event', 'role', 'order')
    list_filter = ('role', 'event')
    search_fields = ('intervenant__first_name', 'intervenant__last_name', 'event__title')
    ordering = ('event', 'order')
    autocomplete_fields = ['intervenant', 'event']
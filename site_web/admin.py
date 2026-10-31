# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect
from .models import BlockedSender, ContactMessage, MessageResponse, MembershipApplication, NewsletterSubscriber

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'subscribed_at')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)
    ordering = ('-subscribed_at',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = [
        'get_full_name', 
        'email', 
        'subject', 
        'status_badge',
        'created_at',
        'has_responses'
    ]
    
    list_filter = ['status', 'created_at', 'is_read', 'replied']
    search_fields = ['name', 'last_name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'message_preview', 'get_full_name']
    actions = ['mark_as_replied', 'mark_as_read', 'mark_as_archived']
    
    fieldsets = (
        ("Informations de contact", {
            'fields': ('name', 'last_name', 'email', 'phone', 'get_full_name')
        }),
        ("Message", {
            'fields': ('subject', 'message_preview', 'message')
        }),
        ("Statut", {
            'fields': ('status', 'is_read', 'replied')
        }),
        ("Métadonnées", {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        return f"{obj.name} {obj.last_name}"
    get_full_name.short_description = "Nom complet"
    
    def has_responses(self, obj):
        return obj.responses.exists()
    has_responses.boolean = True
    has_responses.short_description = "Réponses"
    
    def status_badge(self, obj):
        colors = {
            'new': '#6c757d',  # gray
            'read': '#007bff',  # blue
            'replied': '#28a745',  # green
            'archived': '#fd7e14',  # orange
        }
        return format_html(
            '<span style="padding: 5px; border-radius: 3px; background: {}; color: white;">{}</span>',
            colors[obj.status],
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def message_preview(self, obj):
        preview = obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
        return format_html('<div style="max-height: 100px; overflow: auto; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #f8f9fa;">{}</div>', preview)
    message_preview.short_description = "Aperçu du message"
    
    # Actions personnalisées
    def mark_as_replied(self, request, queryset):
        updated = queryset.update(status=ContactMessage.Status.REPLIED, replied=True)
        self.message_user(request, f"{updated} message(s) marqué(s) comme répondu(s).")
    mark_as_replied.short_description = "Marquer comme répondu"
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(status=ContactMessage.Status.READ, is_read=True)
        self.message_user(request, f"{updated} message(s) marqué(s) comme lu(s).")
    mark_as_read.short_description = "Marquer comme lu"
    
    def mark_as_archived(self, request, queryset):
        updated = queryset.update(status=ContactMessage.Status.ARCHIVED)
        self.message_user(request, f"{updated} message(s) archivé(s).")
    mark_as_archived.short_description = "Archiver"
    
    # Vue détaillée personnalisée avec formulaire de réponse
    def change_view(self, request, object_id, form_url='', extra_context=None):
        message = get_object_or_404(ContactMessage, id=object_id)
        
        # Marquer comme lu si c'est nouveau
        if message.status == ContactMessage.Status.NEW:
            message.status = ContactMessage.Status.READ
            message.is_read = True
            message.save()
        
        # Gérer l'envoi de réponse
        if request.method == 'POST' and 'response_content' in request.POST:
            response_content = request.POST.get('response_content')
            if response_content.strip():
                # Créer la réponse
                MessageResponse.objects.create(
                    contact_message=message,
                    responded_by=request.user,
                    response_content=response_content
                )
                # Mettre à jour le statut
                message.status = ContactMessage.Status.REPLIED
                message.replied = True
                message.save()
                
                messages.success(request, "Réponse enregistrée avec succès.")
                return HttpResponseRedirect(request.path)
            else:
                messages.error(request, "Le contenu de la réponse ne peut pas être vide.")
        
        # Préparer le contexte
        extra_context = extra_context or {}
        extra_context['responses'] = message.responses.all().order_by('-created_at')
        
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
    
    # Ajouter le template personnalisé pour la vue de détail
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if change and obj:
            # Ajouter le formulaire de réponse au contexte
            context['show_response_form'] = True
        return super().render_change_form(request, context, add, change, form_url, obj)

@admin.register(MessageResponse)
class MessageResponseAdmin(admin.ModelAdmin):
    list_display = ['contact_message', 'responded_by', 'created_at', 'response_preview']
    list_filter = ['created_at', 'responded_by']
    readonly_fields = ['created_at', 'response_preview']
    search_fields = [
        'contact_message__name', 
        'contact_message__last_name', 
        'response_content',
        'responded_by__username',
        'responded_by__email'
    ]
    
    def response_preview(self, obj):
        preview = obj.response_content[:100] + "..." if len(obj.response_content) > 100 else obj.response_content
        return format_html('<div style="max-height: 100px; overflow: auto; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #f8f9fa;">{}</div>', preview)
    response_preview.short_description = "Aperçu de la réponse"


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'academic_status', 'institution', 'city_country',
                    'status_badge', 'created_at']
    list_filter = ['status', 'academic_status', 'created_at']
    search_fields = ['full_name', 'email', 'institution', 'city_country', 'research_interests']
    date_hierarchy = 'created_at'
    actions = ['approve_applications', 'reject_applications', 'revoke_applications', 'reset_applications']

    fieldsets = (
        ("Informations personnelles", {'fields': ('full_name', 'email', 'phone', 'city_country')}),
        ("Profil", {'fields': ('academic_status', 'institution', 'research_interests')}),
        ("Adhésion", {'fields': ('how_heard_choices', 'how_heard', 'contribution', 'career_benefit', 'consent')}),
        ("Profil public", {'fields': ('profile_picture', 'bio', 'social_linkedin', 'social_facebook',
                                       'social_twitter', 'social_instagram', 'scholar_link', 'personal_website')}),
        ("Traitement de la demande", {'fields': (
            'status', 'created_at', 'reviewed_at', 'reviewed_by',
            'revoked_at', 'revoked_by', 'revocation_reason', 'internal_notes')}),
    )
    # Le statut ne se change que via les actions (traçabilité : date + auteur).
    readonly_fields = ['full_name', 'email', 'phone', 'city_country', 'academic_status', 'institution',
                       'research_interests', 'how_heard_choices', 'how_heard', 'contribution', 'career_benefit',
                       'consent', 'profile_picture', 'bio', 'social_linkedin', 'social_facebook',
                       'social_twitter', 'social_instagram', 'scholar_link', 'personal_website', 'member',
                       'status', 'created_at', 'reviewed_at', 'reviewed_by', 'revoked_at', 'revoked_by']

    def has_add_permission(self, request):
        return False

    def status_badge(self, obj):
        colors = {'pending': '#6c757d', 'approved': '#28a745', 'rejected': '#fd7e14', 'revoked': '#dc3545'}
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 3px; background: {}; color: white;">{}</span>',
            colors[obj.status], obj.get_status_display())
    status_badge.short_description = "Statut"
    status_badge.admin_order_field = 'status'

    def _apply(self, request, queryset, allowed, action, label, **kwargs):
        done = 0
        for application in queryset:
            if application.status in allowed:
                action(application)
                done += 1
        skipped = queryset.count() - done
        self.message_user(request, f"{done} demande(s) {label}.")
        if skipped:
            self.message_user(request, f"{skipped} demande(s) ignorée(s) : statut incompatible.",
                              level=messages.WARNING)

    P, A, R, V = (MembershipApplication.Status.PENDING, MembershipApplication.Status.APPROVED,
                  MembershipApplication.Status.REJECTED, MembershipApplication.Status.REVOKED)

    @admin.action(description="Valider les demandes sélectionnées")
    def approve_applications(self, request, queryset):
        self._apply(request, queryset, {self.P, self.R, self.V},
                    lambda a: a.approve(request.user), "validée(s)")

    @admin.action(description="Refuser les demandes sélectionnées")
    def reject_applications(self, request, queryset):
        self._apply(request, queryset, {self.P},
                    lambda a: a.reject(request.user), "refusée(s)")

    @admin.action(description="Révoquer les adhésions validées sélectionnées")
    def revoke_applications(self, request, queryset):
        self._apply(request, queryset, {self.A},
                    lambda a: a.revoke(request.user, a.revocation_reason), "révoquée(s)")

    @admin.action(description="Remettre en attente")
    def reset_applications(self, request, queryset):
        self._apply(request, queryset, {self.A, self.R, self.V},
                    lambda a: a.reset_to_pending(), "remise(s) en attente")


@admin.register(BlockedSender)
class BlockedSenderAdmin(admin.ModelAdmin):
    list_display = ('email', 'blocked_at', 'blocked_by')
    search_fields = ('email',)

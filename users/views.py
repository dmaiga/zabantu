from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import CustomUserCreationForm, LoginForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import CustomUser
from .forms import CustomMemberCreationForm
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import LoginForm
# users/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from articles.models import Article, Guelekan
from events.models import Event
from gallery.models import Gallery, Photo
from intervenants.models import Intervenant
from django.db.models import Count, Q
from django.utils import timezone
from site_web.models import NewsletterSubscriber, ContactMessage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import CustomUserUpdateForm
from .models import CustomUser
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from site_web.models import NewsletterSubscriber, ContactMessage
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings

from site_web.models import ContactMessage
from .forms import ContactReplyForm
from site_web.models import MessageResponse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from site_web.models import NewsletterCampaign, NewsletterRecipient
from .forms import NewsletterCampaignForm
from site_web.models import NewsletterSubscriber

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from site_web.models import NewsletterCampaign, NewsletterRecipient, NewsletterSubscriber
import logging
from .forms import NewsletterCampaignForm
from .email_utils import send_newsletter_email  # Import de notre utilitaire

logger = logging.getLogger(__name__)

#--------------------------------------------------------------------
#08_08
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import DetailView, UpdateView
from django.contrib import messages
from .models import CustomUser
from .forms import ProfileEditForm, CustomPasswordChangeForm

class ProfileView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'users/profile.html'
    context_object_name = 'user'

    def get_object(self):
        return self.request.user

class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = ProfileEditForm
    template_name = 'users/profile_edit.html'
    success_url = reverse_lazy('profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Votre profil a été mis à jour avec succès.")
        return super().form_valid(form)

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        messages.success(self.request, "Votre mot de passe a été changé avec succès.")
        return super().form_valid(form)
#_______________________________________________________________

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Bienvenue {user.get_full_name()} !")
                
                # Redirection vers la page demandée (si elle appartient à ce site) ou dashboard
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url and url_has_allowed_host_and_scheme(
                        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                messages.error(request, "Identifiants invalides")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous")
    else:
        form = LoginForm()
    
    return render(request, 'users/login.html', {'form': form})

@login_required
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('login')



@login_required
def dashboard_view(request):
    # Récupération des statistiques basiques
    newsletter_count = NewsletterSubscriber.objects.count()
    contact_messages_count = ContactMessage.objects.count()
    unread_messages_count = ContactMessage.objects.filter(is_read=False).count()
    replied_messages_count = ContactMessage.objects.filter(replied=True).count()
    
    # Calcul des pourcentages
    unread_percentage = (unread_messages_count / contact_messages_count * 100) if contact_messages_count > 0 else 0
    replied_percentage = (replied_messages_count / contact_messages_count * 100) if contact_messages_count > 0 else 0
    
    # Récupération des derniers abonnés et messages
    latest_subscribers = NewsletterSubscriber.objects.order_by('-subscribed_at')[:5]
    latest_messages = ContactMessage.objects.order_by('-created_at')[:5]
    
    Status = MembershipApplication.Status
    pending_applications_count = MembershipApplication.objects.filter(status=Status.PENDING).count()
    approved_applications_count = MembershipApplication.objects.filter(status=Status.APPROVED).count()
    latest_applications = MembershipApplication.objects.order_by('-created_at')[:5]

    context = {
        'pending_applications_count': pending_applications_count,
        'approved_applications_count': approved_applications_count,
        'latest_applications': latest_applications,
        'user': request.user,
        'article_count': Article.objects.count(),
        'gelekan_count': Guelekan.objects.count(),
        'event_count': Event.objects.count(),
        'gallery_count': Gallery.objects.count(),
        'member_count': CustomUser.objects.count(),
        'intervenant_count': Intervenant.objects.count(),
        'newsletter_count': newsletter_count,
        'contact_messages_count': contact_messages_count,
        'unread_messages_count': unread_messages_count,
        'replied_messages_count': replied_messages_count,
        'unread_percentage': unread_percentage,
        'replied_percentage': replied_percentage,
        'latest_subscribers': latest_subscribers,
        'latest_messages': latest_messages,
        'photo_count': Photo.objects.count(),
    }
    
    return render(request, 'users/dashboard.html', context)

@login_required
def create_user_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES) 
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur créé avec succès!")
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/register.html', {'form': form})

@login_required
def user_list_view(request):
    users = CustomUser.objects.exclude(role='admin').order_by('role', 'last_name')
    return render(request, 'users/user_list.html', {'users': users})

@login_required
def user_detail_view(request, id):
    user = get_object_or_404(CustomUser, id=id)
    return render(request, 'users/user_detail.html', {'user_detail': user})

@login_required
def create_member_view(request):
    if request.user.role not in ['admin', 'moderateur']:
        return redirect('login')

    if request.method == 'POST':
        form = CustomMemberCreationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Le membre a été créé avec succès.")
            return redirect('user_list')  # ou admin_dashboard
    else:
        form = CustomMemberCreationForm()
    return render(request, 'users/create_member.html', {'form': form})


@login_required
def update_user_view(request, pk):
    user_to_update = get_object_or_404(CustomUser, pk=pk)
    
    # Vérification des permissions
    
    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, request.FILES, instance=user_to_update)
        if form.is_valid():
            updated_user = form.save()
            
            # Message différent selon qui est modifié
            if request.user.pk == user_to_update.pk:
                messages.success(request, "Votre profil a été mis à jour avec succès.")
            else:
                messages.success(request, f"Le profil de {updated_user.get_full_name()} a été mis à jour.")
            
            return redirect('user_list')
    else:
        form = CustomUserUpdateForm(instance=user_to_update)
    
    context = {
        'form': form,
        'user_to_update': user_to_update,
        'is_self_update': request.user.pk == user_to_update.pk
    }
    return render(request, 'users/update_user.html', context)


def newsletter_list(request):
    subscribers = NewsletterSubscriber.objects.all().order_by('-subscribed_at')
    total_count = subscribers.count()
    active_count = subscribers.filter(is_active=True).count()
    campaigns_count = NewsletterCampaign.objects.count()
    
    # Pagination
    paginator = Paginator(subscribers, 20)  # 20 abonnés par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'subscribers': page_obj,
        'total_count': total_count,
        'active_count': active_count,
        'campaigns_count': campaigns_count,
    }
    return render(request, 'users/newsletter_list.html', context)


@login_required
def contact_message_list(request):
    messages_list = ContactMessage.objects.all().order_by('-created_at')
    
    # Filtrage par statut
    status_filter = request.GET.get('status')
    if status_filter == 'unread':
        messages_list = messages_list.filter(is_read=False)
    elif status_filter == 'read':
        messages_list = messages_list.filter(is_read=True)
    elif status_filter == 'replied':
        messages_list = messages_list.filter(replied=True)
    elif status_filter == 'new':
        messages_list = messages_list.filter(status='new')
    
    # Pagination
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'contact_messages': page_obj,
        'total_count': messages_list.count(),
        'unread_count': ContactMessage.objects.filter(is_read=False).count(),
        'status_filter': status_filter,
    }
    return render(request, 'users/contact_message_list.html', context)

@login_required
def contact_message_detail(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    
    # Marquer comme lu
    if not message.is_read:
        message.is_read = True
        message.status = ContactMessage.Status.READ
        message.save()
    
    # Récupérer l'historique des réponses
    responses = message.responses.all().order_by('-created_at')
    
    context = {
        'message': message,
        'responses': responses,
    }
    return render(request, 'users/contact_message_detail.html', context)

@login_required
def contact_message_delete(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    
    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Message supprimé avec succès.')
        return redirect('contact_message_list')
    
    context = {
        'message': message,
    }
    return render(request, 'users/contact_message_confirm_delete.html', context)

# views.py
@login_required
def contact_message_reply(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    
    if request.method == 'POST':
        form = ContactReplyForm(request.POST)
        if form.is_valid():
            reply_content = form.cleaned_data['reply_content']
            
            # Ajouter la réponse à l'historique
            response = message.add_response(request.user, reply_content)
            
            # Envoyer l'email
            subject = f"Re: {message.subject}"
            context = {
                'original_message': message,
                'reply_content': reply_content,
                'admin_name': request.user.get_full_name() or request.user.username,
                'site_name': 'Zabantu',  # Ajoutez le nom de votre site
            }

            # Génération du contenu HTML + version texte
            html_content = render_to_string('emails/contact_reply.html', context)
            text_content = strip_tags(html_content)

            try:
                # Création de l'email multi-format
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[message.email],
                    reply_to=[settings.DEFAULT_FROM_EMAIL], 
                )
                # Ajouter la version HTML
                email.attach_alternative(html_content, "text/html")
                email.send()

                # Mettre à jour le statut d'envoi
                response.email_sent = True
                response.sent_at = timezone.now()
                response.save()
                
                # Mettre à jour le message principal
                message.replied_by = request.user
                message.replied_at = timezone.now()
                message.save()

                messages.success(request, f'Réponse envoyée à {message.email} avec succès.')
                return redirect('contact_message_detail', pk=message.pk)

            except Exception as e:
                messages.error(request, f'Erreur lors de l\'envoi de l\'email: {str(e)}')
                # Garder la réponse même si l'email n'a pas pu être envoyé
                response.save()
    
    else:
        form = ContactReplyForm(initial={
            'reply_content': f"\n\n--- Message original ---\nDe: {message.full_name} ({message.email})\nSujet: {message.subject}\nMessage:\n{message.message}"
        })
    
    return render(request, 'users/contact_message_reply.html', {
        'message': message, 
        'form': form,
        'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
    })


# views.py
@login_required
def sent_messages_list(request):
    # Récupérer toutes les réponses envoyées par l'utilisateur connecté
    sent_responses = MessageResponse.objects.filter(
        responded_by=request.user,
        email_sent=True
    ).order_by('-created_at')
    
    # Filtrer par date si spécifié
    date_filter = request.GET.get('date')
    if date_filter:
        try:
            filter_date = timezone.datetime.strptime(date_filter, '%Y-%m-%d').date()
            sent_responses = sent_responses.filter(created_at__date=filter_date)
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(sent_responses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sent_responses': page_obj,
        'total_count': sent_responses.count(),
        'date_filter': date_filter,
    }
    return render(request, 'users/sent_messages_list.html', context)



@login_required
def newsletter_campaign_list(request):
    campaigns = NewsletterCampaign.objects.all().order_by('-created_at')
    return render(request, 'users/newsletter/campaign_list.html', {
        'campaigns': campaigns,
        'title': 'Campagnes de newsletter'
    })

@login_required
def newsletter_campaign_create(request):
    if request.method == 'POST':
        form = NewsletterCampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()
            form.save()  # Pour sauvegarder les relations many-to-many
            
            messages.success(request, "La campagne a été créée avec succès.")
            return redirect('newsletter_campaign_list')
    else:
        form = NewsletterCampaignForm()
    
    return render(request, 'users/newsletter/campaign_form.html', {
        'form': form,
        'title': 'Créer une campagne'
    })

@login_required
def newsletter_campaign_edit(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    
    if request.method == 'POST':
        form = NewsletterCampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, "La campagne a été modifiée avec succès.")
            return redirect('newsletter_campaign_list')
    else:
        form = NewsletterCampaignForm(instance=campaign)
    
    return render(request, 'users/newsletter/campaign_form.html', {
        'form': form,
        'title': 'Modifier la campagne'
    })

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'moderateur'])
def newsletter_campaign_send(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    
    if campaign.status != 'draft':
        messages.error(request, "Seules les campagnes en brouillon peuvent être envoyées.")
        return redirect('newsletter_campaign_list')
    
    # Vérifier qu'il y a des destinataires
    if campaign.recipients.count() == 0:
        messages.error(request, "Aucun destinataire sélectionné pour cette campagne.")
        return redirect('newsletter_campaign_edit', pk=pk)
    
    # Mettre à jour le statut de la campagne
    campaign.status = 'sending'
    campaign.save()
    
    # Envoyer la newsletter
    success_count = 0
    error_count = 0
    error_details = []
    
    for recipient in campaign.recipients.all():
        try:
            # Créer le contenu HTML
            html_content = render_to_string('emails/content_published.html', {
                'content': campaign.content,
                'subject': campaign.subject,
                'unsubscribe_url': f"{settings.SITE_URL}/newsletter/unsubscribe/{recipient.subscriber.token}/"
            })
            
            # Envoyer l'email
            if send_newsletter_email(campaign.subject, html_content, [recipient.subscriber.email]):
                # Marquer comme envoyé
                recipient.sent_at = timezone.now()
                recipient.save()
                success_count += 1
                logger.info(f"Email envoyé avec succès à {recipient.subscriber.email}")
            else:
                error_count += 1
                error_details.append(f"Échec d'envoi à {recipient.subscriber.email}")
                logger.error(f"Échec d'envoi à {recipient.subscriber.email}")
                
        except Exception as e:
            error_count += 1
            error_details.append(f"Erreur avec {recipient.subscriber.email}: {str(e)}")
            logger.error(f"Erreur lors de l'envoi à {recipient.subscriber.email}: {e}")
    
    # Mettre à jour le statut de la campagne en fonction du résultat
    if error_count == 0:
        campaign.status = 'sent'
        messages.success(request, f"Newsletter envoyée avec succès à {success_count} destinataires.")
    elif success_count > 0:
        campaign.status = 'partial'
        messages.warning(
            request, 
            f"Newsletter partiellement envoyée: {success_count} succès, {error_count} échecs. " +
            "Certains emails n'ont pas pu être envoyés."
        )
    else:
        campaign.status = 'failed'
        messages.error(
            request, 
            f"Échec complet de l'envoi: {error_count} échecs. " +
            "Aucun email n'a pu être envoyé. Vérifiez la configuration email."
        )
    
    campaign.sent_at = timezone.now()
    campaign.save()
    
    # Enregistrer les détails d'erreur dans les logs
    if error_details:
        logger.error(f"Détails des erreurs d'envoi pour la campagne {campaign.id}:")
        for error in error_details:
            logger.error(f"  - {error}")
    
    return redirect('newsletter_campaign_list')

@login_required
def newsletter_campaign_preview(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    return render(request, 'emails/newsletter_preview.html', {
        'content': campaign.content,
        'subject': campaign.subject,
        'campaign': campaign
    })

@require_POST
@login_required
def newsletter_campaign_delete(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    campaign.delete()
    messages.success(request, "La campagne a été supprimée avec succès.")
    return redirect('newsletter_campaign_list')






@login_required
@user_passes_test(lambda u: u.role in ['admin', 'moderateur'])
def user_delete(request, id):
    user_to_delete = get_object_or_404(CustomUser, id=id)
    
    # Empêcher l'auto-suppression
    if user_to_delete == request.user:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect('user_list')
    
    # Empêcher la suppression d'un administrateur par un modérateur
    if request.user.role == 'moderateur' and user_to_delete.role == 'admin':
        messages.error(request, "Vous n'avez pas les permissions pour supprimer un administrateur.")
        return redirect('user_list')
    
    # Validation de la confirmation
    if request.method == 'POST':
        confirmation = request.POST.get('confirmation', '').strip().upper()
        if confirmation != 'SUPPRIMER':
            messages.error(request, "La confirmation est incorrecte. Veuillez taper 'SUPPRIMER' pour confirmer.")
            return render(request, 'users/user_confirm_delete.html', {'user_to_delete': user_to_delete})
        
        username = user_to_delete.get_full_name()
        user_to_delete.delete()
        messages.success(request, f"Le membre {username} a été supprimé avec succès.")
        return redirect('user_list')
    
    context = {
        'user_to_delete': user_to_delete,
    }
    return render(request, 'users/user_confirm_delete.html', context)


from .models import Partenaire

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Partenaire
from .forms import PartenaireForm


@login_required
def partenaire_list(request):
    partenaires = Partenaire.objects.all()

    return render(request, "users/partenaires/list.html", {
        "partenaires": partenaires
    })


@login_required
def partenaire_create(request):
    form = PartenaireForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        form.save()
        messages.success(request, "Partenaire créé avec succès.")
        return redirect("partenaire_list")

    return render(request, "users/partenaires/form.html", {
        "form": form,
        "title": "Créer un partenaire"
    })


@login_required
def partenaire_detail(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)

    return render(request, "users/partenaires/detail.html", {
        "partenaire": partenaire
    })


@login_required
def partenaire_toggle(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)

    partenaire.is_active = not partenaire.is_active
    partenaire.save()

    status = "activé" if partenaire.is_active else "désactivé"
    messages.success(request, f"Partenaire {status}.")

    return redirect("partenaire_list")

# --- Demandes d'adhésion (back-office) ---
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from site_web.models import MembershipApplication


def _can_manage_applications(user):
    return user.is_authenticated and user.role in ['admin', 'moderateur']


@login_required
@user_passes_test(_can_manage_applications)
def membership_application_list(request):
    Status = MembershipApplication.Status
    applications = MembershipApplication.objects.all()

    status_filter = request.GET.get('status', '')
    if status_filter in Status.values:
        applications = applications.filter(status=status_filter)

    query = request.GET.get('q', '').strip()
    if query:
        applications = applications.filter(
            Q(full_name__icontains=query) | Q(email__icontains=query) | Q(institution__icontains=query)
        )

    page_obj = Paginator(applications, 20).get_page(request.GET.get('page'))
    counts = {s: MembershipApplication.objects.filter(status=s).count() for s in Status.values}
    return render(request, 'users/membership_application_list.html', {
        'applications': page_obj,
        'status_filter': status_filter,
        'query': query,
        'counts': counts,
        'total_count': sum(counts.values()),
    })


@login_required
@user_passes_test(_can_manage_applications)
def membership_application_detail(request, pk):
    application = get_object_or_404(MembershipApplication, pk=pk)
    return render(request, 'users/membership_application_detail.html', {'application': application})


@login_required
@user_passes_test(_can_manage_applications)
@require_POST
def membership_application_action(request, pk, action):
    application = get_object_or_404(MembershipApplication, pk=pk)
    Status = MembershipApplication.Status
    name = application.full_name

    if action == 'approve' and application.status in (Status.PENDING, Status.REJECTED, Status.REVOKED):
        application.approve(request.user)
        messages.success(request, f"L'adhésion de {name} a été validée.")
    elif action == 'reject' and application.status == Status.PENDING:
        application.reject(request.user)
        messages.success(request, f"La demande de {name} a été refusée.")
    elif action == 'revoke' and application.status == Status.APPROVED:
        application.revoke(request.user, request.POST.get('reason', '').strip())
        messages.success(request, f"L'adhésion de {name} a été révoquée.")
    elif action == 'reset' and application.status != Status.PENDING:
        application.reset_to_pending()
        messages.success(request, f"La demande de {name} est de nouveau en attente.")
    else:
        messages.error(request, "Action impossible pour le statut actuel de cette demande.")
    return redirect('membership_application_detail', pk=pk)

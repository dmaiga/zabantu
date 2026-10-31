# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from users.permissions import moderator_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import Event,EventIntervenant
from .forms import EventForm,EventIntervenantForm
 
from articles.views import send_content_published_newsletter
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


EVENT_SORTS = {'date', '-date', 'title', '-title', 'created_at', '-created_at'}


# Créer un événement (toujours en mode brouillon)
@login_required
def event_create(request):

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)  
        if form.is_valid():
            event = form.save(commit=False)
            event.author = request.user
            event.status = 'draft'  # Toujours créer en mode brouillon
            event.save()
            form.save_m2m()
            
            messages.success(request, "L'événement a été créé en mode brouillon.")
            return redirect('event_detail', id=event.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = EventForm()
    if not form.is_valid():
        print(form.errors)
    return render(request, 'events/event_form.html', {
        'form': form,
        'title': 'Créer un événement'
    })

# Modifier un événement
@login_required
def event_update(request, id):
    event = get_object_or_404(Event, id=id)
    
    # Vérifier que l'utilisateur peut modifier cet événement
    if not (request.user == event.author or request.user.role in ['admin', 'moderateur']):
        messages.error(request, "Vous n'avez pas la permission de modifier cet événement.")
        return redirect('event_detail', id=event.id)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event) 
        if form.is_valid():
            form.save()
            messages.success(request, "L'événement a été mis à jour avec succès.")
            return redirect('event_detail', id=event.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = EventForm(instance=event)
    
    return render(request, 'events/event_form.html', {
        'form': form,
        'title': f"Modifier {event.title}",
        'event': event
    })

# Publier un événement
@require_POST
@moderator_required
def event_publish(request, id):
    event = get_object_or_404(Event, id=id)
    
    if event.status != 'published':
        event.status = 'published'
        event.save()
        
        # Envoyer la newsletter seulement si configuré et si l'événement est à venir
        if settings.SEND_NEWSLETTER_ON_PUBLISH:
            
            try:
                send_content_published_newsletter(event, "Nouvel Événement")
                messages.success(request, f"L'événement « {event.title} » a été publié et envoyé aux abonnés.")
            except Exception as e:
                # Logger l'erreur mais continuer
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erreur lors de l'envoi de la newsletter: {e}")
                messages.warning(request, f"L'événement a été publié mais l'envoi de la newsletter a échoué.")
        else:
            messages.success(request, f"L'événement « {event.title} » a été publié avec succès.")
    else:
        messages.info(request, f"L'événement « {event.title} » est déjà publié.")
    
    return redirect('event_detail', id=event.id)

# Dépublier un événement (mettre en brouillon)
@require_POST
@moderator_required
def event_unpublish(request, id):
    event = get_object_or_404(Event, id=id)
    
    if event.status == 'published':
        event.status = 'draft'
        event.save()
        messages.success(request, f"L'événement « {event.title} » a été retiré de la publication.")
    else:
        messages.info(request, f"L'événement « {event.title} » n'est pas publié.")
    
    return redirect('event_detail', id=event.id)

# Archiver un événement
@require_POST
@moderator_required
def event_archive(request, id):
    event = get_object_or_404(Event, id=id)
    
    if event.status != 'archived':
        event.status = 'archived'
        event.save()
        messages.success(request, f"L'événement « {event.title} » a été archivé.")
    else:
        messages.info(request, f"L'événement « {event.title} » est déjà archivé.")
    
    return redirect('event_list')

# Supprimer un événement
@moderator_required
def event_delete(request, id):
    event = get_object_or_404(Event, id=id)
    if request.method == 'POST':
        event.delete()
        return redirect('event_list')
    return render(request, 'events/event_delete.html', {'event': event})


# Liste des événements avec filtres
@login_required
def event_list(request):
    events = Event.objects.all()

    status = request.GET.get('status', 'all')
    event_type = request.GET.get('type', 'all')
    if status in dict(Event.STATUS_CHOICES):
        events = events.filter(status=status)
    if event_type in dict(Event.EVENT_TYPE_CHOICES):
        events = events.filter(event_type=event_type)

    # Recherche
    search_query = request.GET.get('q', '')
    if search_query:
        events = events.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(primary_topic__icontains=search_query)
        )
    
    # Tri
    sort = request.GET.get('sort')
    if sort not in EVENT_SORTS:
        sort = '-date'
    events = events.order_by(sort)
    
    context = {
        'events': events,
        'current_status': status,
        'current_type': event_type,
        'search_query': search_query,
        'current_sort': sort,
    }
    
    return render(request, 'events/event_list.html', context)

# Détail d’un événement
@login_required
def event_detail(request, id):
    # On utilise select_related et prefetch_related pour charger l'auteur 
    # et les intervenants avec leurs profils en une seule fois
    event = get_object_or_404(
        Event.objects.select_related('author').prefetch_related('eventintervenant_set__intervenant'), 
        id=id
    )
    return render(request, 'events/event_detail.html', {'event': event})


@login_required
def manage_event_intervenants(request, id):
    event = get_object_or_404(Event, id=id)

    if request.method == 'POST':
        form = EventIntervenantForm(request.POST)
        if form.is_valid():
            ei = form.save(commit=False)
            ei.event = event
            ei.save()
            return redirect('manage_event_intervenants', id=event.id)
    else:
        form = EventIntervenantForm()

    event_intervenants = EventIntervenant.objects.filter(event=event)

    return render(request, 'events/manage_intervenants.html', {
        'event': event,
        'form': form,
        'event_intervenants': event_intervenants
    })

@login_required
def remove_event_intervenant(request, id):
    ei = get_object_or_404(EventIntervenant, id= id)
    event_id = ei.event.id
    ei.delete()
    return redirect('manage_event_intervenants', id=event_id)
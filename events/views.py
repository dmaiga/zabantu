# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from users.permissions import moderator_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Q
from .models import Event,EventIntervenant
from .forms import EventForm,EventIntervenantForm
from .filters import EventFilterForm
from users.listing import paginate
 
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


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
    return render(request, 'events/event_form.html', {
        'form': form,
        'title': 'Créer un événement',
        'back_url': reverse('event_list'),
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
        'event': event,
        'back_url': reverse('event_detail', args=[event.id]),
    })

# Publier un événement
@require_POST
@moderator_required
def event_publish(request, id):
    event = get_object_or_404(Event, id=id)
    
    if event.status == 'published':
        messages.info(request, f"L'événement « {event.title} » est déjà publié.")
        return redirect('event_detail', id=event.id)

    event.status = 'published'
    event.save()
    messages.success(request, f"L'événement « {event.title} » a été publié.")
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
    form = EventFilterForm(request.GET)
    page_obj, querystring = paginate(request, form.apply(Event.objects.select_related('author')))
    return render(request, 'events/event_list.html', {
        'form': form,
        'page_obj': page_obj,
        'querystring': querystring,
        'type_choices': Event.EVENT_TYPE_CHOICES,
        'status_choices': Event.STATUS_CHOICES,
    })

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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.urls import reverse
from django.views.decorators.http import require_POST
from users.listing import paginate
from users.permissions import moderator_required
from .filters import IntervenantFilterForm
from .models import Intervenant
from .forms import IntervenantForm


@login_required
def intervenant_list(request):
    """Liste des intervenants, avec filtres et pagination"""
    form = IntervenantFilterForm(request.GET)
    intervenants = form.apply(
        Intervenant.objects.annotate(n_events=Count('eventintervenant')).order_by('last_name', 'first_name'))
    page_obj, querystring = paginate(request, intervenants)
    return render(request, 'intervenants/intervenant_list.html', {
        'form': form,
        'page_obj': page_obj,
        'querystring': querystring,
        'type_choices': Intervenant.TYPE_INTERVENANT_CHOICES,
    })

@login_required
def intervenant_detail(request, id):
    """Détail d'un intervenant"""
    intervenant = get_object_or_404(Intervenant, id=id)
    
    # Récupérer les événements où l'intervenant participe
    from events.models import EventIntervenant
    participations = EventIntervenant.objects.filter(intervenant=intervenant).select_related('event')
    
    context = {
        'intervenant': intervenant,
        'participations': participations,
    }
    return render(request, 'intervenants/intervenant_detail.html', context)

@login_required
def intervenant_create(request):
    """Créer un nouvel intervenant"""
    if request.method == 'POST':
        form = IntervenantForm(request.POST, request.FILES)
        if form.is_valid():
            intervenant = form.save()
            messages.success(request, f"L'intervenant {intervenant.full_name()} a été créé avec succès.")
            return redirect('intervenant_detail', id=intervenant.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = IntervenantForm()
    
    context = {
        'form': form,
        'title': 'Nouvel intervenant',
        'back_url': reverse('intervenant_list'),
    }
    return render(request, 'intervenants/intervenant_form.html', context)

@login_required
def intervenant_update(request, id):
    """Modifier un intervenant existant"""
    intervenant = get_object_or_404(Intervenant, id=id)
    
    if request.method == 'POST':
        form = IntervenantForm(request.POST, request.FILES, instance=intervenant)
        if form.is_valid():
            intervenant = form.save()
            messages.success(request, f"L'intervenant {intervenant.full_name()} a été mis à jour avec succès.")
            return redirect('intervenant_detail', id=intervenant.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = IntervenantForm(instance=intervenant)
    
    context = {
        'form': form,
        'intervenant': intervenant,
        'title': f"Modifier {intervenant.full_name()}",
        'back_url': reverse('intervenant_detail', args=[intervenant.id]),
    }
    return render(request, 'intervenants/intervenant_form.html', context)

@require_POST
@moderator_required
def intervenant_delete(request, id):
    """Supprimer un intervenant (depuis sa fiche, avec confirmation)"""
    intervenant = get_object_or_404(Intervenant, id=id)
    name = intervenant.full_name()
    intervenant.delete()
    messages.success(request, f"L'intervenant {name} a été supprimé avec succès.")
    return redirect('intervenant_list')

@login_required
def search_intervenants_ajax(request):
    """Recherche AJAX d'intervenants pour les formulaires"""
    query = request.GET.get('q', '')
    intervenant_type = request.GET.get('type', '')
    
    intervenants = Intervenant.objects.filter(is_available=True)
    
    if query:
        intervenants = intervenants.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(organization__icontains=query)
        )
    
    if intervenant_type:
        intervenants = intervenants.filter(intervenant_type=intervenant_type)
    
    results = [
        {
            'id': i.id,
            'text': f"{i.first_name} {i.last_name} ({i.organization}) - {i.get_intervenant_type_display()}",
            'type': i.intervenant_type
        }
        for i in intervenants
    ]
    
    return JsonResponse({'results': results})
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from site_web.models import NewsletterCampaign, NewsletterSubscriber
from ..forms import NewsletterCampaignForm
from ..permissions import moderator_required


@moderator_required
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


@moderator_required
def newsletter_campaign_list(request):
    campaigns = NewsletterCampaign.objects.all().order_by('-created_at')
    return render(request, 'users/newsletter/campaign_list.html', {
        'campaigns': campaigns,
        'title': 'Campagnes d\'info-lettre'
    })


@moderator_required
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


@moderator_required
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


@require_POST
@moderator_required
def newsletter_campaign_send(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    
    if campaign.status != 'draft':
        messages.error(request, "Seules les campagnes en brouillon peuvent être envoyées.")
        return redirect('newsletter_campaign_list')
    
    # Vérifier qu'il y a des destinataires
    if campaign.recipients.count() == 0:
        messages.error(request, "Aucun destinataire sélectionné pour cette campagne.")
        return redirect('newsletter_campaign_edit', pk=pk)
    
    sent, failed = campaign.send()
    if not failed:
        messages.success(request, f"Info-lettre envoyée à {sent} destinataire(s).")
    elif sent:
        messages.warning(request, f"Info-lettre partiellement envoyée : {sent} réussi(s), {failed} échec(s).")
    else:
        messages.error(request, "Aucun e-mail n'a pu être envoyé. Vérifiez la configuration e-mail.")

    return redirect('newsletter_campaign_list')


@moderator_required
def newsletter_campaign_preview(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    return render(request, 'emails/campaign.html', {'title': campaign.title, 'body': campaign.content})


@require_POST
@moderator_required
def newsletter_campaign_delete(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    campaign.delete()
    messages.success(request, "La campagne a été supprimée avec succès.")
    return redirect('newsletter_campaign_list')

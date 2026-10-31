from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from site_web.models import BlockedSender, NewsletterCampaign, NewsletterSubscriber
from ..forms import NewsletterCampaignForm
from ..permissions import moderator_required


@moderator_required
def newsletter_list(request):
    subscribers = NewsletterSubscriber.objects.all().order_by('-subscribed_at')
    total_count = subscribers.count()
    active_count = subscribers.filter(is_active=True).count()
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        subscribers = subscribers.filter(is_active=True)
    elif status_filter == 'inactive':
        subscribers = subscribers.filter(is_active=False)
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
        'status_filter': status_filter,
        'blocked_emails': set(BlockedSender.objects.filter(
            email__in=[s.email.strip().lower() for s in page_obj]).values_list('email', flat=True)),
    }
    return render(request, 'users/newsletter_list.html', context)


@moderator_required
@require_POST
def newsletter_subscriber_bulk(request):
    """Actions réversibles sur les abonnés cochés : désactiver (plus d'envoi), réactiver, bloquer ou débloquer l'adresse.
    Rien n'est supprimé : un abonné désactivé reste dans la liste et peut être réactivé."""
    action = request.POST.get('action')
    ids = [int(i) for i in request.POST.getlist('selected') if i.isdigit()]
    selected = NewsletterSubscriber.objects.filter(pk__in=ids)
    count = selected.count()
    plural = 's' if count > 1 else ''
    emails = {e.strip().lower() for e in selected.values_list('email', flat=True)}
    if not count:
        messages.error(request, "Cochez au moins un abonné.")
    elif action == 'deactivate':
        selected.update(is_active=False)
        messages.success(request, f"{count} abonné{plural} désactivé{plural} : plus d'envoi d'info-lettre. Vous pouvez les réactiver à tout moment.")
    elif action == 'activate':
        selected.update(is_active=True)
        messages.success(request, f"{count} abonné{plural} réactivé{plural}.")
    elif action == 'deactivate_block':
        selected.update(is_active=False)
        for email in emails:
            BlockedSender.objects.get_or_create(email=email, defaults={'blocked_by': request.user})
        messages.success(request, f"{count} abonné{plural} désactivé{plural} et adresse{plural} bloquée{plural} : elles ne peuvent plus se réinscrire ni envoyer de formulaire.")
    elif action == 'unblock':
        BlockedSender.objects.filter(email__in=emails).delete()
        messages.success(request, f"{len(emails)} adresse{'s' if len(emails) > 1 else ''} débloquée{'s' if len(emails) > 1 else ''}.")
    else:
        messages.error(request, "Action inconnue.")
    target = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = 'newsletter_list'
    return redirect(target)


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

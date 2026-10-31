from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from site_web.models import BlockedSender, NewsletterCampaign, NewsletterSubscriber, PublicationDelivery
from ..forms import NewsletterCampaignForm
from ..permissions import moderator_required


@moderator_required
def newsletter_list(request):
    """Page unique de l'info-lettre : abonnés (avec leurs actions) à gauche, campagnes à droite."""
    blocked = BlockedSender.objects.values_list('email', flat=True)
    everyone = NewsletterSubscriber.objects.annotate(email_key=Lower('email'))
    stats = everyone.aggregate(
        total=Count('pk'), active=Count('pk', filter=Q(is_active=True)),
        blocked=Count('pk', filter=Q(email_key__in=blocked)))

    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()
    subscribers = everyone.order_by('-subscribed_at')
    if status_filter == 'active':
        subscribers = subscribers.filter(is_active=True)
    elif status_filter == 'inactive':
        subscribers = subscribers.filter(is_active=False)
    elif status_filter == 'blocked':
        subscribers = subscribers.filter(email_key__in=blocked)
    if query:
        subscribers = subscribers.filter(email__icontains=query)

    page_obj = Paginator(subscribers, 20).get_page(request.GET.get('page'))
    campaigns = (NewsletterCampaign.objects.order_by('-created_at')
                 .annotate(total=Count('recipients'), delivered=Count('recipients', filter=Q(recipients__sent_at__isnull=False)),
                           failed=Count('recipients', filter=Q(recipients__sent_at__isnull=True, recipients__attempts__gt=0))))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'users/newsletter_list.html', {
        'subscribers': page_obj,
        'page_obj': page_obj,
        'querystring': params.urlencode(),
        'stats': stats,
        'status_filter': status_filter,
        'query': query,
        'campaigns': campaigns,
        'blocked_emails': set(BlockedSender.objects.filter(
            email__in=[s.email.strip().lower() for s in page_obj]).values_list('email', flat=True)),
    })


@moderator_required
@require_POST
def newsletter_subscriber_bulk(request):
    """Actions réversibles sur les abonnés cochés : désactiver (plus d'envoi), réactiver, bloquer ou débloquer l'adresse.
    Rien n'est supprimé : un abonné désactivé reste dans la liste et peut être réactivé."""
    action = request.POST.get('action')
    ids = [int(i) for i in request.POST.getlist('selected') + request.POST.getlist('single') if i.isdigit()]
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
    return redirect('newsletter_list')


@moderator_required
def newsletter_campaign_create(request):
    form = NewsletterCampaignForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.instance.created_by = request.user
        campaign = form.save()
        messages.success(request, f"Brouillon enregistré pour {campaign.recipients.count()} destinataire(s). Vérifiez-le puis envoyez-le.")
        return redirect('newsletter_list')
    return render(request, 'users/newsletter/campaign_form.html', {'form': form, 'title': 'Nouvelle campagne'})


@moderator_required
def newsletter_campaign_edit(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    if campaign.status != 'draft':
        messages.error(request, "Une campagne déjà envoyée ne peut plus être modifiée.")
        return redirect('newsletter_list')
    form = NewsletterCampaignForm(request.POST or None, instance=campaign)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "La campagne a été modifiée.")
        return redirect('newsletter_list')
    return render(request, 'users/newsletter/campaign_form.html', {
        'form': form, 'campaign': campaign, 'title': 'Modifier la campagne'})


@require_POST
@moderator_required
def newsletter_campaign_send(request, pk):
    """Envoie un brouillon, ou renvoie aux seuls destinataires en échec d'une campagne partielle."""
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    if campaign.status not in ('draft', 'partial', 'failed'):
        messages.error(request, "Cette campagne ne peut pas être envoyée dans son état actuel.")
        return redirect('newsletter_list')
    if not campaign.recipients.filter(sent_at=None, subscriber__is_active=True).exists():
        messages.error(request, "Aucun destinataire actif à qui envoyer cette campagne.")
        return redirect('newsletter_campaign_edit', pk=pk) if campaign.status == 'draft' else redirect('newsletter_list')

    sent, failed = campaign.send()
    if not failed:
        messages.success(request, f"Info-lettre envoyée à {sent} destinataire(s).")
    elif sent:
        messages.warning(request, f"Info-lettre partiellement envoyée : {sent} réussi(s), {failed} échec(s). Vous pouvez réessayer.")
    else:
        messages.error(request, "Aucun e-mail n'a pu être envoyé. Vérifiez la configuration e-mail.")
    return redirect('newsletter_list')


@moderator_required
def newsletter_campaign_detail(request, pk):
    """À qui la campagne est destinée, et ce qu'il est advenu de chaque envoi."""
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    recipients = campaign.recipients.select_related('subscriber').order_by('subscriber__email')
    state = request.GET.get('state', '')
    if state == 'sent':
        recipients = recipients.filter(sent_at__isnull=False)
    elif state == 'failed':
        recipients = recipients.filter(sent_at__isnull=True, attempts__gt=0)
    elif state == 'pending':
        recipients = recipients.filter(sent_at__isnull=True, attempts=0)
    else:
        state = ''
    page_obj = Paginator(recipients, 30).get_page(request.GET.get('page'))
    counts = campaign.recipients.aggregate(
        total=Count('pk'), sent=Count('pk', filter=Q(sent_at__isnull=False)),
        failed=Count('pk', filter=Q(sent_at__isnull=True, attempts__gt=0)),
        pending=Count('pk', filter=Q(sent_at__isnull=True, attempts=0)))
    return render(request, 'users/newsletter/campaign_detail.html', {
        'campaign': campaign, 'recipients': page_obj, 'page_obj': page_obj,
        'querystring': f'state={state}' if state else '', 'state': state, 'counts': counts})


@moderator_required
def newsletter_campaign_preview(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    return render(request, 'emails/campaign.html', {'title': campaign.title, 'body': campaign.content})


@require_POST
@moderator_required
def newsletter_campaign_delete(request, pk):
    campaign = get_object_or_404(NewsletterCampaign, pk=pk)
    campaign.delete()
    messages.success(request, "La campagne a été supprimée.")
    return redirect('newsletter_list')


DELIVERY_FILTERS = ('sent', 'pending', 'failed', 'abandoned')


def _delivery_state(qs, state):
    limit = settings.NEWSLETTER_MAX_ATTEMPTS
    if state == 'sent':
        return qs.filter(sent_at__isnull=False)
    unsent = qs.filter(sent_at__isnull=True)
    if state == 'pending':
        return unsent.filter(attempts=0)
    if state == 'failed':
        return unsent.filter(attempts__gt=0, attempts__lt=limit)
    if state == 'abandoned':
        return unsent.filter(attempts__gte=limit)
    return qs


@moderator_required
def email_delivery_list(request):
    """Annonces de publication envoyées automatiquement : reçues, en attente, en échec, avec relance possible."""
    deliveries = PublicationDelivery.objects.select_related('subscriber', 'notice__content_type')
    counts = {state: _delivery_state(deliveries, state).count() for state in DELIVERY_FILTERS}
    state = request.GET.get('state', '')
    if state in DELIVERY_FILTERS:
        deliveries = _delivery_state(deliveries, state)
    else:
        state = ''
    deliveries = deliveries.order_by('-notice__created_at', 'subscriber__email')
    page_obj = Paginator(deliveries, 30).get_page(request.GET.get('page'))
    return render(request, 'users/email_delivery_list.html', {
        'deliveries': page_obj,
        'page_obj': page_obj,
        'querystring': f'state={state}' if state else '',
        'state': state,
        'counts': counts,
        'retryable': counts['failed'] + counts['abandoned'],
        'max_attempts': settings.NEWSLETTER_MAX_ATTEMPTS,
    })


@moderator_required
@require_POST
def email_delivery_retry(request):
    """Remet des envois non réussis dans la file : le prochain passage du cron les reprend."""
    unsent = PublicationDelivery.objects.filter(sent_at__isnull=True, attempts__gt=0)
    if request.POST.get('scope') == 'all':
        selected = unsent
    else:
        selected = unsent.filter(pk__in=[int(i) for i in request.POST.getlist('selected') if i.isdigit()])
    count = selected.update(attempts=0, last_error='')
    if count:
        messages.success(request, f"{count} envoi{'s' if count > 1 else ''} relancé{'s' if count > 1 else ''} : "
                                  f"{'ils partiront' if count > 1 else 'il partira'} automatiquement dans quelques minutes.")
    else:
        messages.error(request, "Aucun envoi en échec à relancer.")
    target = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = 'email_delivery_list'
    return redirect(target)

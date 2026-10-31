from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from site_web import mailing
from site_web.models import BlockedSender, ContactMessage, MessageResponse
from ..forms import ContactReplyForm
from ..permissions import moderator_required


@moderator_required
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
        'blocked_emails': set(BlockedSender.objects.filter(
            email__in=[m.email.strip().lower() for m in page_obj]).values_list('email', flat=True)),
    }
    return render(request, 'users/contact_message_list.html', context)


@moderator_required
@require_POST
def contact_message_bulk(request):
    """Actions groupées sur les messages cochés : marquer comme lus, bloquer les expéditeurs, supprimer."""
    action = request.POST.get('action')
    ids = [int(i) for i in request.POST.getlist('selected') if i.isdigit()]
    selected = ContactMessage.objects.filter(pk__in=ids)
    count = selected.count()
    if not count:
        messages.error(request, "Cochez au moins un message.")
    elif action == 'mark_read':
        selected.filter(status=ContactMessage.Status.NEW).update(status=ContactMessage.Status.READ)
        selected.update(is_read=True)
        messages.success(request, f"{count} message{'s' if count > 1 else ''} marqué{'s' if count > 1 else ''} comme lu{'s' if count > 1 else ''}.")
    elif action == 'block':
        emails = {m.email.strip().lower() for m in selected}
        new = sum(BlockedSender.objects.get_or_create(email=e, defaults={'blocked_by': request.user})[1] for e in emails)
        messages.success(request, f"{len(emails)} adresse{'s' if len(emails) > 1 else ''} bloquée{'s' if len(emails) > 1 else ''}"
                                  f"{'' if new == len(emails) else f' ({len(emails) - new} déjà bloquée(s))'}. Les messages sont conservés.")
    elif action == 'delete':
        selected.delete()
        messages.success(request, f"{count} message{'s' if count > 1 else ''} supprimé{'s' if count > 1 else ''}.")
    else:
        messages.error(request, "Action inconnue.")
    target = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = 'contact_message_list'
    return redirect(target)


@moderator_required
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
        'sender_blocked': BlockedSender.is_blocked(message.email),
    }
    return render(request, 'users/contact_message_detail.html', context)


@moderator_required
@require_POST
def contact_message_block(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    _, created = BlockedSender.objects.get_or_create(
        email=message.email.strip().lower(), defaults={'blocked_by': request.user})
    if created:
        messages.success(request, f"{message.email} est bloquée : cette adresse ne peut plus envoyer de formulaire.")
    return redirect('contact_message_detail', pk=pk)


@moderator_required
@require_POST
def contact_message_unblock(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    BlockedSender.objects.filter(email=message.email.strip().lower()).delete()
    messages.success(request, f"{message.email} est débloquée.")
    return redirect('contact_message_detail', pk=pk)


@moderator_required
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


@moderator_required
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

            html_content = render_to_string('emails/contact_reply.html', context)
            if mailing.send_reply(message.email, subject, html_content):
                response.email_sent = True
                response.sent_at = timezone.now()
                response.save()

                message.replied_by = request.user
                message.replied_at = timezone.now()
                message.save()

                messages.success(request, f'Réponse envoyée à {message.email} avec succès.')
                return redirect('contact_message_detail', pk=message.pk)

            # La réponse reste dans l'historique même si l'e-mail n'est pas parti
            messages.error(request, "L'e-mail n'a pas pu être envoyé ; la réponse est conservée dans l'historique.")
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


@moderator_required
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

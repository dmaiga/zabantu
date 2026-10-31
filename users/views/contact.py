from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from site_web import mailing
from site_web.models import ContactMessage, MessageResponse
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
    }
    return render(request, 'users/contact_message_list.html', context)


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
    }
    return render(request, 'users/contact_message_detail.html', context)


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

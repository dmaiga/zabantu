from articles.models import Article, Guelekan
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from events.models import Event
from gallery.models import Gallery, Photo
from intervenants.models import Intervenant
from site_web.models import ContactMessage, MembershipApplication, NewsletterSubscriber
from ..models import CustomUser


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

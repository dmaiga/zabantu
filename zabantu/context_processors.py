from django.conf import settings

def global_settings(request):
    user = getattr(request, 'user', None)
    pending = 0
    unread = 0
    if user is not None and user.is_authenticated and getattr(user, 'role', '') in ('admin', 'moderateur'):
        from site_web.models import MembershipApplication
        pending = MembershipApplication.objects.filter(
            status=MembershipApplication.Status.PENDING).count()
        from site_web.models import ContactMessage
        unread = ContactMessage.objects.filter(is_read=False).count()
    return {
        'pending_applications_count': pending,
        'unread_messages_count': unread,
        'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        'DEFAULT_FROM_EMAIL_NEWS': settings.DEFAULT_FROM_EMAIL_NEWS,
        'SITE_URL': settings.SITE_URL,
    }
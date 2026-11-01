from django.conf import settings
from django.templatetags.static import static

def global_settings(request):
    from site_web.seo import page_seo
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
        'seo': page_seo(request),
        'SITE_URL': settings.SITE_URL,
        'SITE_ORIGIN': settings.SITE_URL.rstrip('/'),
        'SEO_DEFAULT_IMAGE': settings.SITE_URL.rstrip('/') + static('site_web/images/og-default.jpg'),
    }
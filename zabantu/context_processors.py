from django.conf import settings

def global_settings(request):
    user = getattr(request, 'user', None)
    pending = 0
    if user is not None and user.is_authenticated and getattr(user, 'role', '') in ('admin', 'moderateur'):
        from site_web.models import MembershipApplication
        pending = MembershipApplication.objects.filter(
            status=MembershipApplication.Status.PENDING).count()
    return {
        'pending_applications_count': pending,
        'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        'DEFAULT_FROM_EMAIL_NEWS': settings.DEFAULT_FROM_EMAIL_NEWS,
        'SITE_URL': settings.SITE_URL,
    }
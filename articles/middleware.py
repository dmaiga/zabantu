# articles/middleware.py
from django.utils import timezone
from .models import Article

class AutoPublishMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifie et publie les articles planifiés à chaque requête
        Article.objects.filter(
            publish_at__lte=timezone.now(),
            status='draft'
        ).update(status='published')
        
        return self.get_response(request)
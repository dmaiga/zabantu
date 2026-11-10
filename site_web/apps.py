from django.apps import AppConfig


class SiteWebConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'site_web'

    def ready(self):
        from . import content_cache, signals  # noqa: F401

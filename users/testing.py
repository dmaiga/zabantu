"""Fabriques utilitaires partagées par les tests des différentes applications."""
from django.contrib.auth import get_user_model


def make_user(role='membre', **extra):
    User = get_user_model()
    n = User.objects.count() + 1
    extra.setdefault('backoffice_access', True)
    return User.objects.create_user(
        username=f'{role}{n}', email=f'{role}{n}@test.org', password='secret-pass-123',
        nom='Test', prenom=role.title(), role=role, **extra)

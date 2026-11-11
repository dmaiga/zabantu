"""Connexion à l'espace participant (formations).

BackofficeBackend refuse les comptes sans accès au backoffice ; ce backend-ci accepte les comptes qui ont un profil
participant : les participants, et ceux d'entre eux devenus membres après une demande d'adhésion. L'accès au backoffice
leur reste fermé (BackofficeGuardMiddleware).
"""
from django.contrib.auth.backends import ModelBackend

PARTICIPANT_ROLE = 'participant'


def has_space(user):
    """Vrai si le compte a un espace participant (profil participant)."""
    if not getattr(user, 'is_authenticated', False):
        return False
    from .models import ParticipantProfile
    return ParticipantProfile.objects.filter(user_id=user.pk).exists()


class ParticipantBackend(ModelBackend):
    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and has_space(user)

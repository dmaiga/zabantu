"""Protection des formulaires publics sans captcha : champ piège et délai minimal d'envoi.
Blocage progressif de la connexion après des échecs répétés.

Les compteurs de connexion sont gardés dans un cache fichier dédié (« antispam »), partagé entre les processus de l'hébergeur.
"""
import time

from django import forms
from django.contrib import messages
from django.core import signing
from django.core.cache import caches

HONEYPOT = 'company_site'   # champ caché que seuls les robots remplissent
STAMP = 'form_ts'           # heure d'affichage du formulaire, signée
SALT = 'zabantu.antispam'
MIN_SECONDS = 3             # un humain ne remplit pas un formulaire plus vite
MAX_SECONDS = 24 * 3600     # au-delà, la page est considérée comme périmée

MSG_HONEYPOT = "Envoi refusé : un champ réservé à la protection anti-robots a été rempli. Rechargez la page et réessayez."
MSG_TOO_FAST = "Formulaire envoyé trop vite. Patientez quelques secondes, puis réessayez."
MSG_BLOCKED = "Cette adresse e-mail ne peut plus envoyer de formulaire sur ce site. Si vous pensez qu'il s'agit d'une erreur, contactez le groupe par un autre moyen."
MSG_EXPIRED = "Le formulaire a expiré ou n'est pas valide. Rechargez la page, puis réessayez."


def new_stamp():
    return signing.dumps({'t': time.time()}, salt=SALT)


class AntiSpamMixin:
    """À placer avant forms.Form / forms.ModelForm. Les champs piège sont lus dans les données postées
    (ils ne sont pas des champs du formulaire : les gabarits qui parcourent les champs ne les voient pas)."""

    def clean(self):
        cleaned = super().clean()
        if self.data.get(HONEYPOT):
            raise forms.ValidationError(MSG_HONEYPOT, code='honeypot')
        try:
            age = time.time() - signing.loads(self.data.get(STAMP, ''), salt=SALT)['t']
        except (signing.BadSignature, KeyError, TypeError):
            raise forms.ValidationError(MSG_EXPIRED, code='expired')
        if age > MAX_SECONDS:
            raise forms.ValidationError(MSG_EXPIRED, code='expired')
        if age < MIN_SECONDS:
            raise forms.ValidationError(MSG_TOO_FAST, code='too_fast')
        from .models import BlockedSender
        if BlockedSender.is_blocked(self.data.get('email')):
            raise forms.ValidationError(MSG_BLOCKED, code='blocked')
        return cleaned


def is_bot_rejection(form):
    """Vrai si le formulaire est refusé par la protection (et non pour une simple erreur de saisie)."""
    return any(e.code in ('honeypot', 'expired', 'too_fast', 'blocked') for e in form.non_field_errors().as_data())


def show_antispam_errors(request, form):
    for error in form.non_field_errors():
        messages.error(request, error)


# ----- Blocage de la connexion : 5 échecs, puis 5 min, 10 min, 15 min… (par identifiant saisi) -----
LOGIN_MAX_FAILURES = 5
LOGIN_BASE_MINUTES = 5
LOGIN_MAX_MINUTES = 24 * 60
LOGIN_MEMORY = 24 * 3600    # un nouveau blocage dans ce délai prolonge le précédent


def _cache():
    return caches['antispam']


def _who(username):
    return (username or '').strip().lower()[:150]


def minutes(seconds):
    return max(1, -(-seconds // 60))


def login_wait_seconds(username):
    until = _cache().get(f'login:until:{_who(username)}')
    return max(0, int(until - time.time())) if until else 0


def login_failed(username):
    """Compte un échec. Retourne le nombre de secondes de blocage si la limite vient d'être atteinte, sinon 0."""
    who = _who(username)
    fails = (_cache().get(f'login:fails:{who}') or 0) + 1
    if fails < LOGIN_MAX_FAILURES:
        _cache().set(f'login:fails:{who}', fails, timeout=LOGIN_MEMORY)
        return 0
    level = (_cache().get(f'login:level:{who}') or 0) + 1
    seconds = min(LOGIN_BASE_MINUTES * level, LOGIN_MAX_MINUTES) * 60
    _cache().set(f'login:level:{who}', level, timeout=LOGIN_MEMORY + seconds)
    _cache().set(f'login:until:{who}', time.time() + seconds, timeout=seconds)
    _cache().delete(f'login:fails:{who}')
    return seconds


def login_succeeded(username):
    who = _who(username)
    for name in ('fails', 'level', 'until'):
        _cache().delete(f'login:{name}:{who}')


def login_block_message(seconds):
    n = minutes(seconds)
    return f"Trop de tentatives de connexion échouées. Réessayez dans {n} minute{'s' if n > 1 else ''}."

import time

from django.core import signing

from . import antispam


def human(data, age=10):
    """Données de formulaire telles qu'un visiteur les enverrait : champ piège vide, formulaire affiché il y a `age` secondes."""
    return {**data, antispam.HONEYPOT: '',
            antispam.STAMP: signing.dumps({'t': time.time() - age}, salt=antispam.SALT)}

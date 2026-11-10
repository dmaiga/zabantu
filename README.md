# Zabantu

Site du groupe de recherche Zabantu (Économie, Conflit, État) : site public (publications, séminaires Gɛlɛkan, événements,
galeries, équipe, adhésion, contact, info-lettre) et espace de gestion (backoffice) pour l'équipe.

Django 4.2 · PostgreSQL · Bootstrap (CDN). Les versions sont celles de `requirements.txt` : elles sont figées par l'hébergement.

## Installer en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # puis renseigner au minimum DB_NAME, DB_USER, DB_PASSWORD
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Le site public est sous `/zabantu/` (français) et `/en/zabantu/` (anglais), le backoffice sous `/users/` (toujours en français).
- PostgreSQL est obligatoire (pas de SQLite). Toute la configuration est dans le `.env` (modèle commenté : `.env.example`).
- Avec `DEBUG=True`, les e-mails s'affichent dans la console.
- Accès au backoffice : administrateurs et modérateurs. Un membre doit avoir la case « accès au backoffice » cochée.

## Tester

```bash
python manage.py test
```

Les tests utilisent une base SQLite en mémoire (réglages dans `zabantu/settings_test.py`) et ne touchent pas aux données.

## Organisation

| Dossier | Rôle |
|---------|------|
| `site_web/` | site public, e-mails (`mailing.py`), protection des formulaires (`antispam.py`) |
| `users/` | comptes, backoffice, tableau de bord, communication (messages, info-lettre, adhésions) |
| `articles/` | publications et séminaires Gɛlɛkan |
| `events/`, `gallery/`, `intervenants/` | événements, galeries photos, intervenants |
| `zabantu/` | réglages du projet, bilingue (`i18n.py` : langue selon l'adresse, champs `_en` avec repli sur le français) |
| `locale/en/` | traductions anglaises des textes fixes (`.po` à éditer, `.mo` compilé et versionné) |
| `docs/` | guide de déploiement, audit de dette technique |

## Commandes utiles

```bash
python manage.py publish_scheduled     # publie les contenus programmés (à lancer toutes les 5 min par cron en production)
python manage.py generate_thumbnails   # crée les miniatures des photos
python manage.py collectstatic         # fichiers statiques (à chaque déploiement)
```

## Site bilingue (français / anglais)

- Le français est la langue source : dans les gabarits publics, tout texte fixe passe par `{% translate %}` ou
  `{% blocktranslate %}` (`{% load i18n %}`), en Python par `gettext` / `gettext_lazy`.
- Contenus : `{{ objet.t.champ }}` affiche le champ anglais (`champ_en`) sur les pages anglaises s'il est rempli, le
  français sinon ; `{{ objet.t.lang_champ }}` donne la langue affichée (attribut `lang`). Les champs `_en` apparaissent
  dans l'étape « Version anglaise (facultatif) » des formulaires du backoffice.
- Pages légales : un gabarit par langue (`site_web/templates/site_web/legal/en/`) ; la version française fait foi.
- Après avoir ajouté ou modifié un texte :
  ```bash
  python manage.py makemessages -l en --ignore=.venv --ignore=staticfiles --ignore=media --ignore=data --ignore=var --add-location=file
  # traduire les nouvelles entrées de locale/en/LC_MESSAGES/django.po (msgstr), puis :
  python manage.py compilemessages -l en --ignore=.venv
  ```
  Versionner le `.po` **et** le `.mo` : `msgfmt` n'est pas installé sur le serveur. Un test échoue si le `.mo` est en retard.

## Mise en production

Voir [docs/DEPLOIEMENT_PROD.md](docs/DEPLOIEMENT_PROD.md) : variables du `.env` du serveur, sauvegardes, migrations, tâche cron.
État de la dette technique : [docs/AUDIT_DETTE_TECHNIQUE.md](docs/AUDIT_DETTE_TECHNIQUE.md).

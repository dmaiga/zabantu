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

- Le site public est sous `/zabantu/`, le backoffice sous `/users/`.
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
| `zabantu/` | réglages du projet |
| `docs/` | guide de déploiement, audit de dette technique |

## Commandes utiles

```bash
python manage.py publish_scheduled     # publie les contenus programmés (à lancer toutes les 5 min par cron en production)
python manage.py generate_thumbnails   # crée les miniatures des photos
python manage.py collectstatic         # fichiers statiques (à chaque déploiement)
```

## Mise en production

Voir [docs/DEPLOIEMENT_PROD.md](docs/DEPLOIEMENT_PROD.md) : variables du `.env` du serveur, sauvegardes, migrations, tâche cron.
État de la dette technique : [docs/AUDIT_DETTE_TECHNIQUE.md](docs/AUDIT_DETTE_TECHNIQUE.md).

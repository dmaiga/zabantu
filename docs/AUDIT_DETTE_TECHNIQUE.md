# Dette technique : ce qui reste à traiter

Date : 1er novembre 2026 (points revérifiés dans le code)

Seuls les points encore ouverts figurent ici. Les versions (Django, Python, paquets) sont hors sujet : l'hébergement ne permet pas de les changer.

**Priorité** : P1 = d'abord, P2 = à planifier, P3 = confort.
**Effort** : S = moins d'une demi-journée, M = 1 à 3 jours, L = plus de 3 jours. La **durée estimée** est un ordre de grandeur pour une personne, tests compris.

## À faire en premier

| # | Problème | Action | Priorité | Effort | Durée estimée |
|---|----------|--------|----------|--------|---------------|
| S3 | Les fichiers téléversés ne sont presque pas contrôlés : seule la photo d'adhésion a une limite (5 Mo) | Ajouter des règles communes : types autorisés, poids maximal, ouverture de l'image avec Pillow | P2 | S | 3 à 4 h |
| S2 | 25 `\|safe` dans les gabarits, dont des titres. `bleach` est installé mais jamais utilisé | Nettoyer le HTML à l'enregistrement (titres en texte brut, contenus avec une liste de balises permises) | P2 | M | 1 à 2 jours |

## À planifier

| # | Problème | Action | Priorité | Effort | Durée estimée |
|---|----------|--------|----------|--------|---------------|
| A1 | Un middleware écrit en base à chaque visite pour publier les articles programmés | Le supprimer une fois le cron `publish_scheduled` en place sur le serveur (voir [DEPLOIEMENT_PROD.md](DEPLOIEMENT_PROD.md), section 4.8). D'ici là, c'est lui qui publie. | P2 | S | 1 à 2 h |
| T1 | Pas d'intégration continue ni de linter | Ajouter une CI qui lance les tests sur SQLite et sur PostgreSQL, et un linter (`ruff`) | P2 | M | 1 jour |

## Confort

| # | Problème | Action | Priorité | Effort | Durée estimée |
|---|----------|--------|----------|--------|---------------|
| A2 | `site_web/models.py` importe le module de réglages du projet au lieu de `django.conf.settings`, avec des imports en double | Corriger les imports | P3 | S | 1 h |
| C3 | Aucune journalisation (`LOGGING`). Le gabarit `contact_reply.html` n'est pas dans le dossier des autres e-mails | Configurer les journaux, déplacer le gabarit | P3 | S | 2 à 3 h |
| S4 | Aucune notion d'auteur : tout compte autorisé peut modifier le brouillon d'un autre (`@login_required` seulement) | Limiter la modification d'un brouillon à son auteur et aux modérateurs, si le groupe le souhaite | P3 | S | 3 à 4 h |
| S5 | Pas de SRI sur les bibliothèques externes, pas d'en-tête CSP | Ajouter les empreintes SRI ; la CSP est plus longue car les pages contiennent du code et du style intégrés. Lancer `python manage.py check --deploy` sur le serveur. | P3 | S | SRI : 2 à 3 h · CSP : 1 jour |
| A3 | Trois éditeurs de texte riche mélangés (Summernote, TinyMCE, CKEditor) | En garder un seul (demande une migration des champs) | P3 | M | 2 à 3 jours |
| C1 | Fichiers trop gros : `site_web/views.py` (606 lignes), `site_web/models.py` (426), `articles/views.py` (332), plusieurs gabarits de 400 à 630 lignes | Découper progressivement | P3 | L | plus de 5 jours, par étapes |
| C2 | CSS copié dans les gabarits : plus de 30 fichiers avec un bloc `<style>` et plusieurs centaines de couleurs écrites en dur | Créer une feuille de style commune quand le design system sera appliqué | P3 | L | plus de 5 jours, par étapes |

## Fermés depuis le dernier audit

- **S1 (secrets)** : le `.env` de production est différent de celui qui a circulé.
- **A4 (ancienne base locale)** : `db_v3.sqlite3` n'existe plus.
- **O1 (sauvegardes)** : les scripts `scripts/backup_db.sh` et `scripts/backup_media.sh` existent (voir [DEPLOIEMENT_PROD.md](DEPLOIEMENT_PROD.md), section 4.9). Reste à activer le cron sur le serveur et à copier les sauvegardes hors du serveur.
- **Tests de `gallery` et `intervenants`** : ces apps ont maintenant leurs propres tests (310 tests au total dans le projet).

## Choix assumés (pas de la dette)

Décidés avec le client :
- E-mails envoyés pendant la requête, publications programmées par une commande cron (l'hébergement n'accepte pas Celery).
- Pas de captcha : champ piège et délai minimal sur les formulaires, blocage de la connexion après 5 échecs, pas de limite par adresse IP, pas de double confirmation à l'info-lettre.
- Les membres n'ont pas accès au backoffice par défaut (case « accès au backoffice »).

## Limites de l'audit

Basé sur la lecture du code et l'exécution locale, sans accès au serveur de production. Le cron `publish_scheduled` (A1) et les sauvegardes planifiées ne peuvent pas être vérifiés d'ici. Les outils `bandit` et `pip-audit` n'ont pas été lancés : ils compléteraient S2, S3 et S5.

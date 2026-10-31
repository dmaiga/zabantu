# Audit de dette technique — projet Zabantu (réévaluation)

Date : 31 octobre 2026 (réévaluation de l'audit du 30 octobre 2026, après nettoyage du code mort)
Périmètre : dépôt `zabantu/` (apps `users`, `articles`, `site_web`, `events`, `gallery`, `intervenants`).

Cette version ne contient **que la dette qui subsiste**. Les points corrigés depuis le premier audit ont été retirés.
Les **versions** (Django, Python, paquets, bibliothèques CDN) sont **hors périmètre** : elles ne peuvent pas être changées
à cause des contraintes de l'hébergement, donc aucun point ci-dessous n'en dépend.

Chaque constat a été revérifié dans le code actuel ; ce qui n'a pas pu l'être est signalé « non vérifié ».

Échelle : **P1** = à traiter en priorité, **P2** = à planifier, **P3** = confort / hygiène.
Effort : S < 0,5 j, M ≈ 1–3 j, L > 3 j (ordre de grandeur).

---

## 1. Synthèse

| # | Constat | Priorité | Effort |
|---|---------|----------|--------|
| S1 | Secrets réels dans le `.env` à renouveler (action de votre côté) | P1 | S |
| S2 | HTML non assaini : 24 `\|safe` dont des titres ; `bleach` installé mais jamais utilisé | P2 | M |
| S3 | Pas de validation des fichiers téléversés (type, poids) hors photo d'adhésion | P2 | S |
| S4 | Droits : les brouillons peuvent être modifiés par tout compte ayant accès au backoffice | P3 | S |
| S5 | Pas de SRI sur les bibliothèques CDN, pas de CSP | P3 | S |
| A1 | Middleware d'auto-publication : une écriture en base à chaque requête | P2 | S |
| A2 | `site_web/models.py` : import du module `settings` du projet, doublons d'imports | P3 | S |
| A3 | Trois éditeurs de texte riche mélangés | P3 | M |
| C1 | Fichiers volumineux, logique métier dans les vues | P3 | L |
| C2 | CSS et couleurs dupliqués dans les templates | P3 | L |
| C3 | Aucune journalisation configurée ; code commenté ; un gabarit d'e-mail hors de son dossier | P3 | S |
| T1 | Pas d'intégration continue ni de linter ; apps `gallery` et `intervenants` sans tests propres | P2 | M |
| O1 | Pas de sauvegarde régulière ni de supervision d'erreurs | P2 | M |

---

## 2. Sécurité

### S1 — Secrets à renouveler (P1)
- Le `.env` a circulé par archives (zips d'origine) et contient des mots de passe SMTP réels : les considérer comme exposés.
  Il est désormais ignoré par git, mais cela ne répare pas l'exposition passée.
- À faire : changer les mots de passe des deux comptes e-mail et de la base, générer une nouvelle `SECRET_KEY` de production
  (elle est exigée par `settings.py` quand `DEBUG=False`), renseigner `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS`.
- Non vérifié : l'état du `.env` sur le serveur de production.

### S2 — HTML non assaini (P2)
- 24 occurrences du filtre `|safe` dans les templates, dont des titres (`{{ article.title|safe }}` dans l'accueil et la liste
  des publications). Sûr seulement tant que seuls des comptes de confiance écrivent.
- `bleach` est dans `requirements.txt` mais **n'est appelé nulle part** dans le code.
- Piste : assainir à l'enregistrement (titres : texte brut ; contenus : liste blanche de balises) ou à l'affichage.

### S3 — Fichiers téléversés (P2)
- Seul le formulaire d'adhésion contrôle le poids de la photo (5 Mo). Aucune validation de type ni de poids pour les images
  et PDF des articles, événements, galeries, intervenants, partenaires ; pas de plafond `DATA_UPLOAD_MAX_MEMORY_SIZE`.
- Piste : validateurs communs (extensions autorisées, poids maximal, ouverture de l'image avec Pillow).

### S4 — Droits sur les brouillons (P3)
- `article_create` et `article_update` (articles et séminaires Gɛlɛkan) ne demandent que `@login_required`. Depuis que les membres
  n'ont plus accès au backoffice par défaut, seuls les comptes autorisés les atteignent, mais il n'existe aucune notion d'auteur :
  tout compte autorisé peut modifier le brouillon d'un autre.
- Piste : limiter la modification d'un brouillon à ses auteurs et aux modérateurs, si le fonctionnement du groupe le demande.

### S5 — Durcissement résiduel (P3)
- Aucun attribut `integrity` (SRI) sur les bibliothèques chargées depuis un CDN (`base_public.html`, `base.html`, `auth_base.html`).
- Aucun en-tête CSP.
- À lancer sur le serveur de production : `python manage.py check --deploy` (non exécutable ici sans les réglages e-mail de production).

---

## 3. Architecture

### A1 — Middleware d'auto-publication (P2)
- `articles/middleware.py` exécute un `UPDATE` sur `Article` à chaque requête. Il double la commande
  `publish_scheduled` (qui sert aussi pour les annonces e-mail) et, comme `update()` n'émet pas de signaux, il publie sans passer
  par la logique de publication.
- Condition avant suppression : la tâche cron `publish_scheduled` doit être en place sur le serveur (voir `docs/DEPLOIEMENT_PROD.md`,
  section 4.8). Tant qu'elle ne l'est pas, c'est ce middleware qui publie les articles programmés.

### A2 — Imports de `site_web/models.py` (P3)
- `from zabantu import settings` (importe le module de configuration au lieu de `django.conf.settings`) écrase l'import correct
  de la ligne 12 ; fonctionne, mais contourne `override_settings` dans les tests.
- Imports en double (`models`, `timezone`, `gettext_lazy`) et `User = get_user_model()` appelé à l'import.

### A3 — Éditeurs de texte riche (P3)
- Trois éditeurs cohabitent : Summernote (utilisé dans les formulaires), TinyMCE (installé) et CKEditor (`RichTextField` importé dans
  `site_web/models.py`, application non installée). Choisir un seul éditeur réduit la surface d'attaque et le poids des pages ;
  cela demande une migration des champs existants. Sans lien avec les versions.

### A4 — Ancienne base locale (P3)
- Le fichier `db_v3.sqlite3` (ancienne base de développement) est encore dans le dossier, ignoré par git : il peut contenir des données
  réelles, à supprimer localement.

---

## 4. Qualité du code

### C1 — Taille et responsabilités (P3)
- `site_web/views.py` 601 lignes, `site_web/models.py` 409, `articles/views.py` 339 : requêtes, règles métier, rendu et e-mails mélangés.
  (`users/views/` est découpé : le plus gros fichier fait 210 lignes.)
- Gabarits les plus gros : `public_event_detail.html` 630, `public_guelekan_detail.html` 616, `public_about.html` 468,
  `public_article_list.html` 438, `gallery/photo_detail.html` 390.

### C2 — CSS dupliqué dans les templates (P3)
- Site public : 20 fichiers avec un bloc `<style>`, 239 couleurs écrites en dur, 2 fichiers qui redéfinissent `:root`.
  Backoffice : 7 fichiers, 129 couleurs, 2 `:root`. Pas de feuille de style commune ni de mise en cache navigateur des styles.
- Le design system n'est pas appliqué au code : tant que ce n'est pas fait, ces styles restent à maintenir page par page.

### C3 — Hygiène (P3)
- Aucun réglage `LOGGING` : les erreurs d'envoi d'e-mails et de traitement ne sont pas journalisées de façon exploitable.
- Code commenté laissé en place (anciens réglages dans `settings.py`).
- `contact_reply.html` est resté dans `users/templates/emails/` alors que les autres e-mails sont dans `site_web/templates/emails/`.

---

## 5. Tests et qualité continue

### T1 — Intégration continue et couverture (P2)
- 282 tests (users 94, site_web 140, articles 27, events 14, zabantu 7) ; les fichiers `tests.py` de `gallery` et `intervenants`
  sont vides (la galerie est en partie couverte par `site_web/tests.py`).
- Aucune intégration continue, aucun linter ni formateur (pas de `pyproject.toml`, `ruff`, `pre-commit`).
- Les tests tournent sur SQLite en mémoire (le rôle PostgreSQL de l'hébergeur ne peut pas créer de base) ; le passage sur PostgreSQL est
  manuel (commande décrite dans `zabantu/settings_test.py`). Une CI devrait lancer les deux.

---

## 6. Exploitation

### O1 — Documentation et reprise (P2)
- Un `README` et un guide de déploiement (`docs/DEPLOIEMENT_PROD.md`) existent. La sauvegarde n'est documentée qu'**avant un déploiement** (`pg_dump`) ; aucune sauvegarde régulière de la base ni du dossier `media/`
  (images et PDF), aucune supervision ni alerte d'erreurs.

---

## 7. Choix assumés (à ne pas traiter)

Décisions prises avec le client ; elles ne sont pas de la dette :
- E-mails envoyés pendant la requête, avec indicateur d'attente, et publications programmées par une commande cron (pas de Celery,
  que l'hébergement ne permet pas). Les échecs d'envoi sont comptés et le statut des campagnes les reflète.
- Pas de captcha : champ piège et délai minimal sur les formulaires publics ; blocage de la connexion après 5 échecs par identifiant ;
  pas de limite d'envois par adresse IP ; pas de double confirmation à l'inscription à l'info-lettre.
- Les membres n'ont pas accès au backoffice par défaut (case « accès au backoffice »).

## 8. Ordre conseillé

1. **Maintenant (avant la mise en production)** : S1 (secrets), puis S3 (téléversements) et S2 (HTML).
2. **Nettoyage rapide** : A2 et A4, puis A1 une fois le cron vérifié sur le serveur.
3. **Exploitation** : O1 (sauvegardes régulières, supervision), C3 (journalisation), T1 (intégration continue).
4. **En continu** : S4, S5, A3, C1, C2.

## 9. Limites
- Lecture du code et exécution locale ; pas d'accès au serveur de production ni à sa base.
- Pas d'analyse automatisée (`bandit`, `pip-audit`) : à lancer pour compléter S2, S3 et S5.

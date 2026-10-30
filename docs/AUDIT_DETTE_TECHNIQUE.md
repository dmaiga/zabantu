# Audit de dette technique — projet Zabantu

Date : 30 octobre 2026
Périmètre : dépôt `zabantu/` (Django 4.2.13, apps `users`, `articles`, `site_web`, `events`, `gallery`, `intervenants`).
Nature du document : constat uniquement. **Aucune correction n'a été appliquée** suite à cet audit.

Les constats sont issus de la lecture du code et de commandes de vérification (taille des fichiers, versions installées,
recherche de motifs). Chaque point cite le fichier concerné. Ce qui n'a pas été vérifié est signalé comme tel.

Échelle : **P1** = à traiter en priorité (sécurité / correction fonctionnelle), **P2** = à planifier, **P3** = confort / hygiène.

---

## 1. Synthèse

| # | Constat | Priorité | Effort estimé |
|---|---------|----------|---------------|
| S1 | Aucun contrôle de rôle sur les actions de gestion de contenu (suppression, publication…) | P1 | M |
| S2 | Redirection ouverte après connexion (`next` non validé) | P1 | S |
| S3 | Désabonnement newsletter : identifiants séquentiels, liens cassés, incohérence entre trois implémentations | P1 | M |
| S4 | Pas de protection contre la force brute sur la connexion | P1 | S |
| S5 | Secrets réels dans `.env` (dont anciens identifiants en commentaire) | P1 | S |
| F1 | Newsletter envoyée à tous les abonnés, y compris les désabonnés | P1 | S |
| F2 | Vue `membre_liste` inutilisable (template absent + URL masquée) | P2 | S |
| A1 | Envois d'e-mails synchrones dans les requêtes HTTP | P2 | M |
| A2 | Middleware qui écrit en base à chaque requête | P2 | S |
| A3 | Cache local mémoire + accès à un attribut privé (`cache._cache`) | P2 | M |
| D1 | Dépendances en retard, éditeurs de texte riche obsolètes et multiples | P2 | M–L |
| T1 | Quasi aucun test (hors module d'adhésion) | P2 | L |
| C1 | Fichiers volumineux, logique métier dans les vues, CSS dupliqué dans les templates | P3 | L |
| C2 | Duplications (3 utilitaires d'envoi d'e-mails, imports répétés, `print` au lieu de logs) | P3 | S |
| O1 | Pas de config de déploiement reproductible (statics, médias, journalisation, sauvegardes) | P2 | M |

Effort : S < 0,5 j, M ≈ 1–3 j, L > 3 j (ordre de grandeur, à confirmer).

---

## 2. Sécurité

### S1 — Pas de contrôle de rôle sur les vues de gestion (P1)
- `articles/views.py` : `article_delete`, `publish_article`, `unpublish_article`, `guelekan_delete`, etc. sont protégées par
  `@login_required` uniquement. Le modèle `users.CustomUser` possède un champ `role` (admin / modérateur / membre),
  mais il n'est testé que dans quelques vues d'`users/views.py` (ex. suppression d'utilisateur, ligne ~597).
- Conséquence : tout compte connecté, quel que soit son rôle, peut supprimer ou dé-publier n'importe quel article.
  Aucune notion de propriété (un membre peut agir sur les articles d'un autre).
- Non vérifié : l'état réel des rôles en base de production.
- Piste : décorateur / mixin de permissions par rôle, et vérification de propriété pour les actions d'édition.

### S2 — Redirection ouverte à la connexion (P1)
- `users/views.py`, `login_view` : `next_url = request.GET.get('next', 'dashboard')` puis `redirect(next_url)` sans validation.
  Un lien `…/auth/?next=https://site-malveillant` redirige l'utilisateur authentifié vers un domaine externe.
- Piste : `url_has_allowed_host_and_scheme()` de Django.

### S3 — Désabonnement newsletter fragile et incohérent (P1)
- `site_web/views.py` : `newsletter_unsubscribe` identifie l'abonné par son **id entier séquentiel**. N'importe qui peut
  désabonner tout le monde en énumérant 1, 2, 3… Le modèle possède pourtant un champ `token` (UUID) non utilisé ici.
- Trois façons différentes de construire le lien de désabonnement :
  - `site_web/models.py` (`NewsletterCampaign.send`) et `articles/views.py` : `…/newsletter/unsubscribe/<id>/`
  - `users/views.py` (~ligne 514) : `…/newsletter/unsubscribe/<token>/`
- Les routes réelles sont sous le préfixe `zabantu/` (`zabantu/newsletter/unsubscribe/<int>/`). Les liens générés
  (`SITE_URL + /newsletter/unsubscribe/…`) ne correspondent donc pas à la route : **probablement des 404** (à confirmer par un test
  de bout en bout). Conséquence réglementaire possible : lien de désinscription non fonctionnel dans les e-mails.
- `newsletter_subscribe` ne valide pas le format de l'e-mail côté serveur (il passe par `request.POST.get`, sans formulaire),
  et il n'y a ni captcha ni double opt-in.

### S4 — Pas de limitation de tentatives de connexion (P1)
- Aucune dépendance de type rate-limit / lockout (`django-axes`, `django-ratelimit`…) dans `requirements.txt`.
  La connexion personnalisée (`login_view`) n'impose aucune temporisation.

### S5 — Gestion des secrets (P1)
- `.env` contient des mots de passe SMTP réels et, en commentaire, d'anciens identifiants de base de données (hôte, utilisateur…).
- Le dossier n'est pas un dépôt git, donc il n'y a pas de fuite via l'historique, mais le fichier circule probablement par archive
  (cf. les deux zips d'origine). Les identifiants doivent être considérés comme exposés.
- Piste : rotation des mots de passe, suppression des lignes commentées, stockage via le gestionnaire du serveur d'hébergement.

### S6 — Durcissement résiduel (P2)
- Après la mise en place des variables d'environnement, `manage.py check --deploy` en mode production ne signale plus que la
  force de la clé (clé de test). Vérifier en production : `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, certificat TLS avant d'activer
  `SECURE_SSL_REDIRECT`.
- Injection de HTML : 24 occurrences du filtre `|safe` dans les templates, dont des titres d'articles
  (`{{ article.title|safe }}`). Les contenus venant d'éditeurs riches sont de confiance seulement si seuls des comptes de
  confiance peuvent écrire (voir S1). `bleach` est installé : vérifier s'il est effectivement appliqué à l'enregistrement.
- CDN externes (Bootstrap via jsDelivr) sans attribut `integrity` (SRI) dans `base_public.html`.
- Non vérifié : en-têtes CSP, politique de téléversement de fichiers (types / tailles) pour les médias et la médiathèque.

---

## 3. Correction fonctionnelle

### F1 — Newsletter envoyée aux désabonnés (P1)
- `articles/views.py`, `send_content_published_newsletter` : `NewsletterSubscriber.objects.all()` — le champ `is_active`
  n'est pas filtré. Un abonné qui s'est désabonné (`is_active=False`) continue de recevoir les publications.

### F2 — `membre_liste` cassée (P2)
- `site_web/views.py:53` rend `site_web/public_membre_liste.html`, **template inexistant**.
- `site_web/urls.py` déclare deux fois le chemin `membres/` ; la seconde déclaration (`membre_liste`) n'est jamais atteinte,
  ainsi que `membres/<int:user_id>/` (`membre_detail`) masqué par `membres/<int:pk>/`. Code mort à supprimer ou à réparer.

### F3 — Mots de passe de réinitialisation et e-mails (P3)
- Les gabarits d'e-mail (`users/templates/emails/content_published.html`) vivent dans l'app `users` alors que l'usage est dans
  `articles` et `site_web` : couplage implicite entre apps.

---

## 4. Architecture

### A1 — E-mails envoyés de façon synchrone (P2)
- Publier un article déclenche une boucle d'envoi SMTP dans la requête (`send_content_published_newsletter`,
  `NewsletterCampaign.send`). Avec quelques centaines d'abonnés, la requête devient lente ou dépasse le timeout du serveur.
  Les erreurs ne sont que `print()`ées ; le statut de campagne passe à `sent` même si des envois ont échoué
  (`error_count` calculé mais non utilisé dans `NewsletterCampaign.send`).
- Piste : file de tâches (Celery/RQ/ `django-q`) ou, a minima, commande de gestion exécutée par cron, avec journalisation.

### A2 — Middleware d'auto-publication (P2)
- `articles/middleware.py` exécute un `UPDATE` sur `Article` **à chaque requête** (y compris statiques en développement).
- Il coexiste avec la commande `articles/management/commands/publish_scheduled.py` qui fait le même travail : doublon.
- Effet de bord : la publication planifiée ne déclenche pas les signaux (`update()` ne les émet pas), donc ni invalidation de cache
  ni newsletter sur ce chemin. Piste : conserver seulement la commande + cron.

### A3 — Cache (P2)
- Aucun réglage `CACHES` : Django utilise le cache **en mémoire locale par processus**. Avec plusieurs workers gunicorn, chaque
  worker a son propre cache, donc les invalidations faites par `site_web/signals.py` ne touchent qu'un worker :
  pages d'accueil / listes potentiellement obsolètes selon le worker servi.
- `signals.py` parcourt `cache._cache` (attribut privé du backend locmem) pour supprimer des clés par préfixe : cela ne
  fonctionnera pas avec un autre backend (Redis, Memcached, fichier).
- Piste : backend de cache partagé + clés versionnées plutôt que suppression par préfixe.

### A4 — Importation du module settings du projet (P3)
- `site_web/models.py:14` : `from zabantu import settings` importe le module de configuration, non `django.conf.settings`.
  Ça fonctionne par chance (les constantes sont lues sur le module), mais contourne les surcharges de test (`override_settings`) et
  casse si le nom du projet change. À remplacer par `from django.conf import settings`.
- Le même fichier appelle `get_user_model()` à l'import (`User = get_user_model()`), risque de dépendance circulaire.

### A5 — Base de données (P2)
- Développement : SQLite. Production : PostgreSQL. Les deux moteurs divergent (types, contraintes, recherche texte).
  Il est recommandé de lancer au moins la CI sur PostgreSQL.
- Les migrations étaient exclues par l'ancien `.gitignore` ; elles sont désormais suivies. À vérifier que l'historique de
  production correspond aux fichiers livrés (`showmigrations` sur le serveur).
- Non vérifié : cohérence du schéma PostgreSQL de production avec le dépôt.

---

## 5. Dépendances

Versions installées (`pip list --outdated`) :

| Paquet | Installé | Dernière |
|--------|----------|----------|
| Django | 4.2.13 | 6.1.2 |
| django-ckeditor | 6.7.3 | 6.7.4 |
| django-tinymce | 4.1.0 | 5.0.0 |
| bleach | 6.2.0 | 6.4.0 |
| pillow | 11.3.0 | 13.0.0 |
| gunicorn | 23.0.0 | 26.2.0 |
| psycopg2-binary | 2.9.10 | 2.9.13 |
| django-environ | 0.12.0 | 0.14.0 |

- **D1 — Django 4.2 est une version LTS en fin de support** : correctifs de sécurité limités. Les commentaires de
  `settings.py` mentionnent déjà Django 5.2 (projet généré avec 5.2.4 puis figé en 4.2.13). Migration à planifier vers la LTS courante,
  par étapes (4.2 → 5.2), avec une suite de tests au préalable (voir T1).
- **D2 — Trois éditeurs de texte riche** coexistent : `django-ckeditor` (CKEditor 4, considéré obsolète / non maintenu en
  licence libre), `django-tinymce` et `django-summernote`, tous trois dans `INSTALLED_APPS`. Choisir un seul éditeur réduit la surface
  d'attaque et le poids des pages. Les migrations d'articles référencent déjà ces champs : prévoir une migration de données.
- **D3 — `requirements.txt` incomplet / non verrouillé** : `django-simple-captcha` n'a aucune version épinglée ; `setuptools`,
  `wheel`, `sqlparse`… sont épinglés alors que ce ne sont pas des dépendances directes. Le fichier était encodé en UTF-16
  (corrigé lors de la mise en place de l'environnement). Piste : `pip-tools` / `uv` avec fichier de verrouillage.
- `whitenoise` est installé mais **absent de `MIDDLEWARE`** : les fichiers statiques en production dépendent de la config du serveur web.

---

## 6. Qualité du code

### C1 — Taille et responsabilités (P3)
Fichiers les plus gros (lignes) : `users/views.py` 670, `site_web/views.py` ~490, `site_web/models.py` ~420 (avec le module
d'adhésion), `articles/views.py` 360. Les vues mélangent requêtes ORM, règles métier, rendu, e-mails et cache. Pas de couche
`services` ni de gestionnaires de requêtes (`QuerySet` personnalisés).
Templates : 14 283 lignes de HTML au total ; les plus gros dépassent 500 lignes (`public_guelekan_detail.html` 616,
`public_event_detail.html` 604, `index.html` 541, `public_article_list.html` ~530).

### C2 — CSS et JS en ligne dans les templates (P3)
Chaque page redéfinit ses propres variables CSS (`--zabantu-*`) et styles de cartes dans un bloc `<style>`. Résultat :
duplication, risques d'incohérence visuelle (ex. les retours client sur les cartes de publications portaient sur ce type de style),
pas de mise en cache navigateur des styles. Piste : feuille de style commune + composants de template (`{% include %}`).

### C3 — Doublons et bruit (P3)
- Imports répétés plusieurs fois dans le même fichier (`site_web/views.py`, `site_web/models.py`).
- Trois utilitaires d'envoi : `users/email_utils.py`, `site_web/email_utils.py` et appels directs (`send_newsletter_email`
  importé depuis deux endroits différents selon le fichier).
- Appels `print()` pour les erreurs (4 occurrences dans les apps) au lieu du module `logging`; aucun réglage `LOGGING` dans les settings.
- Code commenté et blocs désactivés (anciens réglages d'hébergement, constantes HTTPS) laissés dans les fichiers.
- Commentaires datés de type `#05_08`, `#16_08` comme seule documentation des évolutions.

### C4 — Langue et i18n (P3)
`LANGUAGE_CODE = 'en-us'` alors que le contenu est en français : dates formatées en anglais (ex. « 29 August 2026 » sur la capture client).
`USE_I18N` est actif mais seul `gettext_lazy` apparaît dans un fichier. Fuseau `UTC` : les dates affichées sont décalées pour le Mali (UTC, ici sans effet,
mais à confirmer pour d'autres fuseaux).

---

## 7. Tests et qualité continue

### T1 — Couverture quasi nulle (P2)
- `users`, `articles`, `events`, `gallery`, `intervenants` : `tests.py` contient 3 lignes (gabarit vide).
- Seul `site_web/tests.py` (7 tests) existe, ajouté avec le formulaire d'adhésion.
- Aucune CI, aucun linter / formateur configuré (pas de `pyproject.toml`, `ruff`, `pre-commit`).
- Priorités de tests : droits d'accès (S1), flux de publication, désabonnement newsletter, publication planifiée, pages publiques (smoke tests).

---

## 8. Exploitation et déploiement

### O1 — Absence de procédure reproductible (P2)
- Aucun `Dockerfile`, fichier de service, ni documentation de déploiement dans le dépôt (pas de README à la racine).
- Les chemins statiques / médias de production étaient en dur et commentés dans `settings.py` (désormais paramétrables par variables d'environnement).
- Pas de sauvegarde documentée de la base PostgreSQL ni du dossier `media/` ; pas de supervision ni d'alerte d'erreurs.
- La base SQLite de développement (`db_v3.sqlite3`) est livrée avec le projet : elle peut contenir des données réelles (non vérifié) ;
  elle est exclue du suivi par le nouveau `.gitignore`.
- Version de Python non spécifiée (aucun `.python-version`, `runtime.txt` ni `pyproject.toml`) ; le développement local utilise 3.13.

---

## 9. Plan de remédiation proposé

Ordre suggéré (à valider avec le client avant de planifier) :

1. **Sprint 1 — Sécurité immédiate** (≈ 3–4 j) : S1 (permissions par rôle), S2 (`next` validé), S4 (limitation de tentatives),
   S5 (rotation des secrets), F1 (filtre `is_active`).
2. **Sprint 2 — Newsletter fiable** (≈ 3 j) : S3 (jeton unique, URL unique et testée, double opt-in), A1 (file d'envoi et suivi des échecs).
3. **Sprint 3 — Filet de sécurité** (≈ 4–5 j) : T1 (tests ciblés + CI), A2 / A3 (suppression du middleware, cache partagé).
4. **Sprint 4 — Mise à niveau** (≈ 5+ j) : D1–D3 (Django LTS courante, un seul éditeur riche, dépendances verrouillées), A5.
5. **En continu** : C1–C4 (refactorisation progressive, CSS commun, journalisation, langue `fr`), O1 (documentation de déploiement et de reprise).

## 10. Limites de cet audit
- Lecture statique du code et exécution locale en mode développement ; pas d'accès au serveur de production ni à sa base.
- Pas de test d'intrusion ni d'analyse automatisée (`bandit`, `pip-audit`) : à lancer pour compléter les points S6 et D.
- Les durées sont des ordres de grandeur.

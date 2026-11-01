# Production : mise à jour et exploitation

Date : 1er novembre 2026

Le site est **en production** (hébergement cPanel LWS, code tiré depuis GitHub dans `/home/cp2594820p30/repositories/zabantu`). Ce guide décrit la mise à jour de routine, l'état de la dernière mise à jour et les tâches planifiées.

Principe : **rien ne doit modifier ou supprimer de données existantes**. Toute opération sur la base est précédée d'une sauvegarde.

---

## 1. Mise à jour de routine

Après avoir poussé les commits sur GitHub, sur le serveur :
```bash
cd /home/cp2594820p30/repositories/zabantu
PYTHON=/home/cp2594820p30/virtualenv/repositories/zabantu/3.13/bin/python ./deploy.sh
```
`deploy.sh` enchaîne, en s'arrêtant à la première erreur :
1. **Sauvegardes** de la base et des médias (`SKIP_BACKUP=1` pour les passer, déconseillé).
2. **Code** : `git fetch origin main`, puis `git reset --hard origin/main`. Le code du serveur devient identique à GitHub. Les modifications faites à la main sur des fichiers suivis par git sont **écrasées** (le script les affiche) ; le `.env`, `media/` et `logs/` ne sont pas touchés. Ne jamais modifier le code directement sur le serveur.
3. **Dépendances** : `pip install -r requirements.txt`.
4. **Migrations** : le plan est affiché (`migrate --plan`), puis `migrate`.
5. **Fichiers statiques** : `collectstatic` à **chaque** mise à jour (WhiteNoise sert des noms à empreinte : une page qui référence un fichier absent du manifeste échoue).
6. **Miniatures** : `generate_thumbnails`.
7. **Contrôle** : `check --deploy` (aucun avertissement bloquant).
8. Option : `./deploy.sh <username> …` donne l'accès au backoffice à ces comptes.

Ensuite :
- **Redémarrer l'application** (cPanel > Setup Python App > Restart) : obligatoire pour les nouveaux fichiers Python et bibliothèques de balises.
- **Vérifier** (section 5).

À savoir :
- Lire le plan des migrations affiché : si l'une supprime une colonne ou une table, ou si l'historique ne correspond pas à la base, s'arrêter et analyser (pas de `--fake` sans comprendre). Une sauvegarde de la veille ou de l'instant existe.
- **Ne jamais lancer `makemigrations` en production** (`django_summernote` essaierait d'écrire dans le dossier des paquets installés).
- Retour arrière des miniatures : supprimer `MEDIA_ROOT/cache/thumbs/`.
- `deploy.sh` doit d'abord être sur GitHub : un changement du script ne s'applique qu'au déploiement suivant.

## 2. Dernière mise à jour (1er novembre 2026) : effective

Déployée en production ; les sauvegardes ont été testées à la main avec succès (base : 180 Ko ; médias : 42 Mo) et les trois tâches cron sont en place.

| Changement | État |
|------------|------|
| Six migrations « AlterField » (`articles.0012`, `events.0004`, `gallery.0003`, `intervenants.0003`, `site_web.0011`, `users.0004`) : règles de validation des fichiers, aucune table | Appliquées |
| Contrôle des fichiers téléversés (images JPG, PNG, WebP, GIF, 10 Mo ; PDF, 25 Mo) | En service. Les anciens fichiers ne sont pas revérifiés. |
| HTML des éditeurs nettoyé à l'affichage (`bleach`) | En service. Aucune donnée enregistrée modifiée ; les iframes intégrées ne s'affichent plus. |
| Middleware d'auto-publication supprimé | Le cron `publish_scheduled` (3.1) est **obligatoire** et en place. |
| Pages légales, bandeau de cookies, aperçu des liens partagés (Open Graph), `/sitemap.xml`, `/robots.txt` | En service. À faire : déclarer le site dans Google Search Console (une fois). |
| Empreintes SRI sur Bootstrap, Font Awesome, PhotoSwipe CSS, jQuery | En service. Si la mise en page ou les icônes disparaissent, la console du navigateur indique la balise en cause (« integrity »). |
| Scripts de sauvegarde `scripts/backup_*.sh` et leurs cron | En place et testés (3.2). |

Aucune nouvelle variable obligatoire. `SEO_START_DATE` est facultative (1er novembre 2026 par défaut) : elle fixe la date à partir de laquelle un contenu publié figure dans le sitemap et reçoit une balise canonique.

## 3. Tâches planifiées (cPanel > Tâches Cron)

Les trois tâches sont en place :

| Fréquence | Tâche |
|-----------|-------|
| Toutes les 5 minutes | `publish_scheduled` (3.1) |
| Tous les jours à 2 h | `backup_db.sh` (3.2) |
| Tous les jours à 2 h 30 | `backup_media.sh` (3.2) |

### 3.1 Publications programmées
Un contenu « Programmé » est publié, puis annoncé aux abonnés, par cette commande. Elle peut être relancée sans risque : un contenu n'est publié et annoncé qu'une fois. Elle appelle aussi `send_pending_emails` (envoi par lots, nouvelles tentatives des échecs). Sans elle, un contenu programmé reste en attente.
```cron
*/5 * * * * cd /home/cp2594820p30/repositories/zabantu && /home/cp2594820p30/virtualenv/repositories/zabantu/3.13/bin/python manage.py publish_scheduled >> /home/cp2594820p30/repositories/zabantu/logs/publish_scheduled.log 2>&1
```

### 3.2 Sauvegardes
`backup_db.sh` (base PostgreSQL, `pg_dump -Fc`) et `backup_media.sh` (archive de `MEDIA_ROOT`, sans les miniatures). Ils lisent `DB_*` et `MEDIA_ROOT` dans le `.env` sans l'exécuter, écrivent dans `/home/cp2594820p30/backups/zabantu` (hors de `public_html`, lisibles par le seul propriétaire), contrôlent chaque sauvegarde et suppriment celles de plus de 14 jours (`KEEP_DAYS`). `deploy.sh` les lance aussi avant chaque mise à jour.
```cron
0 2 * * *  bash /home/cp2594820p30/repositories/zabantu/scripts/backup_db.sh    >> /home/cp2594820p30/backups/zabantu/backup.log 2>&1
30 2 * * * bash /home/cp2594820p30/repositories/zabantu/scripts/backup_media.sh >> /home/cp2594820p30/backups/zabantu/backup.log 2>&1
```
Copier régulièrement les fichiers **hors du serveur** : une sauvegarde sur le même serveur ne protège pas d'une panne du serveur. Restauration : voir l'en-tête de chaque script.

## 4. Fichier `.env` de production (référence)

Sur le serveur uniquement, jamais dans le dépôt (liste complète dans `.env.example`). Variables essentielles avec `DEBUG=False` :

```
DEBUG=False
SECRET_KEY=<clé longue et aléatoire, ≥ 50 caractères>
ALLOWED_HOSTS=zabantu.net,www.zabantu.net
CSRF_TRUSTED_ORIGINS=https://zabantu.net,https://www.zabantu.net
SITE_URL=https://zabantu.net

DB_NAME / DB_USER / DB_PASSWORD / DB_HOST=localhost / DB_PORT=5432

# E-mail : compte principal (réponses, admissions) et compte de l'info-lettre (suffixe _NEWS)
EMAIL_HOST / EMAIL_PORT / EMAIL_USE_TLS / EMAIL_USE_SSL / EMAIL_HOST_USER_MAIN / EMAIL_HOST_PASSWORD_MAIN / DEFAULT_FROM_EMAIL
EMAIL_HOST_NEWS / EMAIL_PORT_NEWS / EMAIL_USE_TLS_NEWS / EMAIL_USE_SSL_NEWS / EMAIL_HOST_USER_NEWS / EMAIL_HOST_PASSWORD_NEWS / DEFAULT_FROM_EMAIL_NEWS

STATIC_ROOT=/home/cp2594820p30/public_html/static
MEDIA_ROOT=/home/cp2594820p30/public_html/media
```

Points d'attention :
- Le site **refuse de démarrer** si une variable obligatoire manque.
- `SITE_URL` sert aux liens des e-mails, aux balises de partage et au sitemap : une valeur fausse donne des liens faux.
- `SECURE_SSL_REDIRECT` est actif par défaut avec `DEBUG=False`. Redirection en boucle : `SECURE_SSL_REDIRECT=False`, redémarrer.
- `CACHE_DIR` (facultatif) : dossier inscriptible pour les compteurs de connexion bloquée. Pour débloquer quelqu'un tout de suite : vider ce dossier.
- Test d'envoi d'e-mail : `python manage.py shell -c "from django.core.mail import send_mail; send_mail('Test','Bonjour','<expéditeur>',['<destinataire>'])"`.

## 5. Vérifications après une mise à jour

Automatique : `python manage.py check --deploy` (aucun avertissement bloquant).

Sur le site réel :
- [ ] Accueil, Publications, Événements, Galerie, À propos, Membres, Contact : pas d'erreur 500.
- [ ] Un contenu programmé : publié à l'heure par le cron, annonce envoyée aux abonnés.
- [ ] Formulaires d'adhésion et de contact : envoi de test, réception côté tableau de bord. **Supprimer ensuite les données de test.**
- [ ] Ajout d'une photo : une image valide passe, un faux fichier (`.png` qui n'en est pas un) est refusé.
- [ ] Pages légales (`/zabantu/mentions-legales/`, `/confidentialite/`, `/cookies/`) et lien « Gérer mes cookies » du pied de page.
- [ ] `https://zabantu.net/robots.txt` et `https://zabantu.net/sitemap.xml` s'affichent. Le sitemap ne liste que les contenus publiés à partir de `SEO_START_DATE`.
- [ ] Aperçu d'un lien d'article, d'événement et de Gɛlɛkan sur WhatsApp, Facebook et LinkedIn (un réseau peut garder un ancien aperçu en cache).
- [ ] Google Search Console : site déclaré, sitemap envoyé (une seule fois).
- [ ] Console du navigateur (accueil et tableau de bord) : aucune erreur « integrity » ni ressource bloquée ; mise en page et icônes intactes.
- [ ] Pages d'erreur : `https://zabantu.net/zabantu/page-inexistante/` affiche la page 404 aux couleurs du site. (Les pages 500, 400 et 403 s'affichent seulement avec `DEBUG=False`.)
- [ ] HTTPS sans contenu mixte ; e-mail de test reçu.

## 6. Retour arrière

| Situation | Action |
|-----------|--------|
| Page en erreur après mise à jour | Revenir au commit précédent sur le serveur (`git reset --hard <commit>`, `collectstatic`), redémarrer. Ne pas relancer `deploy.sh` avant d'avoir corrigé GitHub : il réaligne le code sur `origin/main`. Les migrations ajoutées n'empêchent pas l'ancien code de fonctionner. |
| Problème de base de données | Restaurer la sauvegarde : `pg_restore --no-owner -U <utilisateur> -d <base> <fichier>.dump`, sur une base vide, application arrêtée. En dernier recours : cela efface les données saisies depuis la sauvegarde. |
| Miniatures problématiques | Supprimer `MEDIA_ROOT/cache/thumbs/`. |
| Redirection HTTPS en boucle | `SECURE_SSL_REDIRECT=False` dans `.env`, redémarrer. |

## 7. Points à surveiller

- **Spam** : les formulaires publics n'ont pas de captcha (champ piège et délai minimal de 3 s). Surveiller les demandes d'adhésion.
- **Sauvegardes** : vérifier de temps en temps `backup.log` et la présence de fichiers récents, et copier les sauvegardes hors du serveur.
- **Dette technique restante** : voir [AUDIT_DETTE_TECHNIQUE.md](AUDIT_DETTE_TECHNIQUE.md).

# Production : mise à jour et exploitation

Date : 1er novembre 2026

Le site est **déjà en production** (hébergement cPanel LWS, code tiré depuis GitHub dans `/home/cp2594820p30/repositories/zabantu`). Ce guide décrit la mise à jour de routine, ce que contient la prochaine, et les tâches planifiées.

Principe : **rien ne doit modifier ou supprimer de données existantes**. Toute opération sur la base est précédée d'une sauvegarde.

---

## 1. Mise à jour de routine

1. **Sauvegarder** (les scripts du 3.2 le font chaque nuit ; avant une mise à jour, les lancer à la main) :
   ```bash
   bash /home/cp2594820p30/repositories/zabantu/scripts/backup_db.sh
   bash /home/cp2594820p30/repositories/zabantu/scripts/backup_media.sh
   ```
2. **Tirer le code** : `git pull` (le `.env`, `media/` et les bases ne sont pas dans le dépôt).
3. **Dépendances**, si `requirements.txt` a changé : `pip install -r requirements.txt` dans le virtualenv du serveur.
4. **Lire le plan des migrations avant de les appliquer** :
   ```bash
   python manage.py migrate --plan
   python manage.py migrate
   ```
   Si une migration supprime une colonne ou une table, ou si l'historique ne correspond pas à la base : s'arrêter et analyser. Pas de `--fake` sans comprendre.
   **Ne jamais lancer `makemigrations` en production** (`django_summernote` essaierait d'écrire dans le dossier des paquets installés).
5. **Fichiers statiques** : `python manage.py collectstatic --noinput` à **chaque** mise à jour (WhiteNoise sert des noms à empreinte : une page qui référence un fichier absent du manifeste échoue).
6. **Miniatures** (si de nouvelles photos sont arrivées) : `python manage.py generate_thumbnails`. Retour arrière : supprimer `MEDIA_ROOT/cache/thumbs/`.
7. **Redémarrer l'application** (obligatoire pour les nouveaux fichiers Python et bibliothèques de balises).
8. **Vérifier** (section 5).

`deploy.sh` enchaîne les étapes 4 (sans le plan), 5 et 6 ; il ne remplace ni la sauvegarde ni le redémarrage.

## 2. Prochaine mise à jour : ce qu'elle change

| Changement | Action à prévoir |
|------------|------------------|
| Six migrations « AlterField » (`articles.0012`, `events.0004`, `gallery.0003`, `intervenants.0003`, `site_web.0011`, `users.0004`) | `migrate`. Elles ne changent que les règles de validation des fichiers téléversés, aucune table. |
| Contrôle des fichiers téléversés (images JPG, PNG, WebP, GIF, 10 Mo ; PDF, 25 Mo) | Aucune. Les anciens fichiers ne sont pas revérifiés. |
| HTML des éditeurs nettoyé à l'affichage (`bleach`) | Aucune : aucune donnée enregistrée n'est modifiée. Les iframes intégrées ne s'affichent plus. |
| Middleware d'auto-publication supprimé | Le cron `publish_scheduled` (3.1) est **obligatoire** : sans lui, un contenu « Programmé » reste en attente. Il est déjà en place. |
| Pages légales, bandeau de cookies, aperçu des liens partagés (Open Graph), `/sitemap.xml`, `/robots.txt` | Vérifier `SITE_URL` dans le `.env` (section 4) ; déclarer le site dans Google Search Console (une fois). |
| Scripts de sauvegarde `scripts/backup_*.sh` | Créer le dossier et ajouter les deux tâches cron (3.2). |

Il n'y a **aucune nouvelle variable obligatoire**. `SEO_START_DATE` est facultative (1er novembre 2026 par défaut) : elle fixe la date à partir de laquelle un contenu publié figure dans le sitemap et reçoit une balise canonique.

## 3. Tâches planifiées (cPanel > Tâches Cron)

### 3.1 Publications programmées (déjà en place)
Un contenu « Programmé » est publié, puis annoncé aux abonnés, par cette commande. Elle peut être relancée sans risque : un contenu n'est publié et annoncé qu'une fois. Elle appelle aussi `send_pending_emails` (envoi par lots, nouvelles tentatives des échecs).
```cron
*/5 * * * * cd /home/cp2594820p30/repositories/zabantu && /home/cp2594820p30/virtualenv/repositories/zabantu/3.13/bin/python manage.py publish_scheduled >> /home/cp2594820p30/repositories/zabantu/logs/publish_scheduled.log 2>&1
```
La fréquence est celle réglée dans cPanel (toutes les 5 minutes suffisent). Le dossier `logs/` doit exister dans le dépôt du serveur.

### 3.2 Sauvegardes (à ajouter)
`backup_db.sh` (base PostgreSQL, `pg_dump -Fc`) et `backup_media.sh` (archive de `MEDIA_ROOT`, sans les miniatures). Ils lisent `DB_*` et `MEDIA_ROOT` dans le `.env` sans l'exécuter, écrivent dans `/home/cp2594820p30/backups/zabantu` (hors de `public_html`, lisibles par le seul propriétaire), contrôlent chaque sauvegarde et suppriment celles de plus de 14 jours (`KEEP_DAYS`).
```cron
0 2 * * *  bash /home/cp2594820p30/repositories/zabantu/scripts/backup_db.sh    >> /home/cp2594820p30/backups/zabantu/backup.log 2>&1
30 2 * * * bash /home/cp2594820p30/repositories/zabantu/scripts/backup_media.sh >> /home/cp2594820p30/backups/zabantu/backup.log 2>&1
```
Avant de planifier : `mkdir -p /home/cp2594820p30/backups/zabantu`, tester chaque script à la main, vérifier que `pg_dump` est disponible pour cet utilisateur. Copier ensuite régulièrement les fichiers **hors du serveur** : une sauvegarde sur le même serveur ne protège pas d'une panne du serveur.
Restauration : voir l'en-tête de chaque script.

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
- [ ] HTTPS sans contenu mixte ; e-mail de test reçu.

## 6. Retour arrière

| Situation | Action |
|-----------|--------|
| Page en erreur après mise à jour | Revenir au commit précédent (`git checkout <commit>`), redémarrer. Les migrations ajoutées n'empêchent pas l'ancien code de fonctionner. |
| Problème de base de données | Restaurer la sauvegarde : `pg_restore --no-owner -U <utilisateur> -d <base> <fichier>.dump`, sur une base vide, application arrêtée. En dernier recours : cela efface les données saisies depuis la sauvegarde. |
| Miniatures problématiques | Supprimer `MEDIA_ROOT/cache/thumbs/`. |
| Redirection HTTPS en boucle | `SECURE_SSL_REDIRECT=False` dans `.env`, redémarrer. |

## 7. Points à surveiller

- **Spam** : les formulaires publics n'ont pas de captcha (champ piège et délai minimal de 3 s). Surveiller les demandes d'adhésion.
- **Sauvegardes** : vérifier de temps en temps `backup.log` et la présence de fichiers récents, et copier les sauvegardes hors du serveur.
- **Dette technique restante** : voir [AUDIT_DETTE_TECHNIQUE.md](AUDIT_DETTE_TECHNIQUE.md).

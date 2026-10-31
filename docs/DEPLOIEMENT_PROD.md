# Déploiement en production — liste de contrôle

Date : 31 octobre 2026
Périmètre : mise en production des évolutions faites depuis le premier commit (configuration par environnement, PostgreSQL partout,
formulaire d'adhésion, refonte du site public, backoffice, e-mails, publications programmées).

Ce document est une **liste de contrôle**, pas un script à exécuter aveuglément. Les valeurs entre `< >` sont à
remplacer. Il n'a pas été testé sur le serveur réel : les détails d'hébergement (chemins, gestionnaire de
processus, version de Python) sont à confirmer.

Principe : **rien ne doit modifier ou supprimer de données existantes**. Toute opération sur la base est précédée d'une sauvegarde.

---

## 1. Ce qui change en production

| Changement | Touche les données existantes ? |
|------------|---------------------------------|
| Migrations `site_web` 0003 à 0007, `users` 0003, `articles` 0011 | Non : elles **ajoutent** des tables, un champ (`backoffice_access`, faux par défaut) ou ne changent que des libellés. |
| Déploiement du code | Ne touche **pas** la base : seul `migrate` la modifie, et uniquement par ajouts. |
| Connexion réservée (admins, modérateurs, membres autorisés) | Les comptes « membre » existants ne pourront plus se connecter tant qu'on ne leur donne pas l'accès. |
| Réglages d'e-mail dans le `.env` (serveur, port, TLS, expéditeurs) | Le site **refuse de démarrer** si l'une de ces variables manque. |
| Miniatures de photos (`media/cache/thumbs/`) | Non : fichiers séparés, aucune base touchée, originaux intacts. |
| Réglages par variables d'environnement (`.env`) | Non, mais le site **refuse de démarrer** si une variable obligatoire manque. |
| `LANGUAGE_CODE = 'fr'` | Non : dates et administration en français. |
| Rôle « admin » automatique pour les superutilisateurs | Seulement à l'enregistrement d'un compte (voir 4.6). |
| Nouveaux gabarits, nouvelles URL (`/zabantu/adhesion/`, `/zabantu/evenements/<id>/calendrier.ics`…) | Non. |
| Ancienne page `/zabantu/guelekans/` | Redirige (302) vers `/zabantu/publications/?type=guelekan`. |

## 2. Avant de commencer

1. **Sauvegarder la base PostgreSQL** (obligatoire) :
   ```bash
   pg_dump -Fc -U <utilisateur> -h <hôte> <nom_base> > zabantu_avant_deploiement_$(date +%F).dump
   ```
   Vérifier que le fichier n'est pas vide et le conserver hors du serveur.
2. **Sauvegarder le dossier `media/`** (copie ou archive). Les miniatures n'y modifient rien, mais c'est la bonne pratique.
3. **Ne pas copier `db_v3.sqlite3`** sur le serveur : l'application n'utilise plus SQLite (PostgreSQL partout) ; ce fichier n'a rien à faire en ligne.
4. **Noter la version actuellement en ligne** (date, archive) pour pouvoir revenir en arrière.
5. **Code `articles` de la production** : il est déjà repris dans le dépôt (migrations `0008` à `0010`, champs et formulaire « ouvrage », voir
   `PLAN_IMPLEMENTATION.md` §5.1). Vérifier avant de déployer que le dossier `articles/` du serveur n'a **pas changé depuis** la copie faite le
   31 octobre 2026 (comparer `articles/migrations/` : mêmes fichiers `0001` à `0010`). Sinon, reprendre les nouveautés avant de continuer.
6. **Choisir qui garde l'accès à la connexion** : les comptes « membre » n'ont plus accès au backoffice par défaut. Cocher « Autoriser la connexion »
   sur les membres concernés après la mise en ligne (la copie locale ne comptait aucun membre ayant déjà utilisé la connexion).

## 3. Fichier `.env` de production

Créer ou compléter `.env` **sur le serveur** (jamais dans le dépôt). Avec `DEBUG=False`, ces variables sont obligatoires :

```
DEBUG=False
SECRET_KEY=<NOUVELLE clé longue et aléatoire, ≥ 50 caractères : celle du code actuel commence par « django-insecure- »>
ALLOWED_HOSTS=zabantu.net,www.zabantu.net
CSRF_TRUSTED_ORIGINS=https://zabantu.net,https://www.zabantu.net
SITE_URL=https://zabantu.net

DB_NAME=<base>
DB_USER=<utilisateur>
DB_PASSWORD=<mot de passe>
DB_HOST=localhost
DB_PORT=5432

# Valeurs actuellement écrites en dur dans le code de production : à reprendre telles quelles
CONTACT_EMAIL=info@zabantu.net

# Compte principal : réponses, accusés de réception, admissions
EMAIL_HOST=mail.zabantu.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER_MAIN=<adresse>
EMAIL_HOST_PASSWORD_MAIN=<mot de passe>
DEFAULT_FROM_EMAIL=Zabantu <info@zabantu.net>

# Compte de l'info-lettre : annonces de publications et campagnes
EMAIL_HOST_NEWS=mail.zabantu.net
EMAIL_PORT_NEWS=587
EMAIL_USE_TLS_NEWS=True
EMAIL_USE_SSL_NEWS=False
EMAIL_HOST_USER_NEWS=<adresse>
EMAIL_HOST_PASSWORD_NEWS=<mot de passe>
DEFAULT_FROM_EMAIL_NEWS=zabantu_newsletter@zabantu.net

# Chemins actuels de la production (auparavant écrits en dur dans le code). OBLIGATOIRES : le site refuse de démarrer sans eux.
# En développement : STATIC_ROOT=staticfiles et MEDIA_ROOT=media
STATIC_ROOT=/home/cp2594820p30/public_html/static
MEDIA_ROOT=/home/cp2594820p30/public_html/media
```

Points d'attention :
- Générer une clé : `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`.
- **`SECURE_SSL_REDIRECT`** : activé par défaut quand `DEBUG=False`. Si le certificat HTTPS n'est pas encore en place, ajouter
  `SECURE_SSL_REDIRECT=False` le temps de le configurer, sinon le site redirige en boucle ou devient inaccessible.
- Les identifiants e-mail existants sont à **renouveler** (ils ont circulé en clair dans l'archive d'origine) ; supprimer aussi les
  anciennes lignes commentées de l'ancien `.env`.
- Le fichier `.env.example` du dépôt liste toutes les variables.

## 4. Déploiement, dans l'ordre

### 4.1 Mettre le code à jour
Déployer le code (sans `.env`, sans `*.sqlite3`, sans `media/`). Installer les dépendances dans l'environnement du serveur :
```bash
pip install -r requirements.txt
```
Vérifier que **Pillow** est bien installé (nécessaire aux images et aux miniatures) et que `psycopg2-binary` est présent.

### 4.2 Vérifier l'historique de migrations (point critique)
L'ancien `.gitignore` excluait les dossiers `migrations/`. Avant toute migration, comparer ce que la base connaît et ce que le code contient :
```bash
python manage.py showmigrations
```
- Attendu : tout est `[X]` sauf `articles.0011_scheduled_status`, `site_web.0003` à `0007` et `users.0003_backoffice_access` (`[ ]`). Les migrations `articles` `0008` à `0010`
  sont déjà appliquées en production et présentes dans le dépôt.
- **Si d'autres migrations apparaissent non appliquées, ou si des migrations appliquées en base n'existent plus dans le code : s'arrêter**
  et analyser avant d'aller plus loin. Ne pas utiliser `--fake` sans comprendre pourquoi.
- **Ne jamais lancer `makemigrations` en production** : la bibliothèque `django_summernote` signale une modification de son propre schéma et
  essaierait d'écrire un fichier dans le dossier des paquets installés.

### 4.3 Appliquer les migrations
```bash
python manage.py migrate
```
Contrôler d'abord avec `python manage.py migrate --plan` : seules `articles.0011_scheduled_status`, `site_web.0003` à `0007` et
`users.0003_backoffice_access` doivent figurer. Aucune ne supprime de colonne ni de ligne.

### 4.4 Fichiers statiques
```bash
python manage.py collectstatic --noinput
```
Note : WhiteNoise est actif hors `DEBUG` (comme dans la production actuelle) et sert les fichiers de `STATIC_ROOT` avec des noms à empreinte.
`collectstatic` doit donc être relancé à **chaque** déploiement, sinon une page qui référence un fichier absent du manifeste échoue.

### 4.5 Miniatures de photos (optionnel mais recommandé)
S'assurer que l'utilisateur du serveur d'application **peut écrire** dans `MEDIA_ROOT` (le dossier `cache/thumbs/` y sera créé).
Pré-générer les miniatures pour éviter un premier affichage plus lent :
```bash
python manage.py generate_thumbnails
```
Sans cela, les miniatures se créent à la première visite. Si le dossier n'est pas accessible en écriture, les pages affichent les photos
d'origine (aucune erreur). **Retour arrière** : supprimer `MEDIA_ROOT/cache/thumbs/`.

### 4.6 Comptes administrateurs
Un superutilisateur créé par `createsuperuser` avait le rôle « membre » par défaut, ce qui bloquait la création de membres. Le correctif
met le rôle « admin » à l'enregistrement. Pour les comptes **déjà existants** en production :
```bash
python manage.py shell -c "
from users.models import CustomUser as U
for u in U.objects.filter(is_superuser=True, role='membre'): u.save(); print('corrigé :', u.username, u.role)"
```

### 4.7 Redémarrer l'application
Redémarrer le processus Django (gunicorn, Passenger ou équivalent). C'est obligatoire : les nouvelles bibliothèques de balises de gabarit
(`photo_tags`) ne sont détectées qu'au redémarrage.

### 4.8 Publications programmées (tâche cron)
Une publication ou un Gɛlɛkan « Programmé » est publié, puis annoncé aux abonnés, par une commande à lancer régulièrement.
Ajouter une tâche cron (toutes les 5 minutes suffisent), avec les chemins du serveur :
```cron
*/5 * * * * cd /chemin/vers/zabantu && /chemin/vers/.venv/bin/python manage.py publish_scheduled >> /chemin/vers/logs/publish_scheduled.log 2>&1
```
Tester à la main avant d'activer le cron : `python manage.py publish_scheduled` (affiche « 0 contenu(s) publié(s) » s'il n'y a rien à faire).
La commande peut être relancée sans risque : un contenu n'est publié et annoncé qu'une fois.

Les e-mails utilisent uniquement le `.env` : `SITE_URL` (liens des e-mails), le compte principal (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`,
`EMAIL_USE_SSL`, `EMAIL_HOST_USER_MAIN`, `EMAIL_HOST_PASSWORD_MAIN`, `DEFAULT_FROM_EMAIL`) et le compte de l'info-lettre (mêmes noms avec le suffixe
`_NEWS`). Tester avec `python manage.py shell -c "from django.core.mail import send_mail; send_mail('Test','Bonjour','<expéditeur>',['<destinataire>'])"`.

### 4.9 Protection des formulaires

Les formulaires de contact, d'adhésion et d'info-lettre ont un champ piège invisible et un délai minimal de 3 s (aucune limite
d'envois, aucune adresse IP). La connexion est bloquée après 5 échecs sur un même identifiant : 5 minutes, puis 10, 15… à chaque
nouveau blocage (remise à zéro après une connexion réussie). Les compteurs sont dans un cache fichier (aucune migration).

- `CACHE_DIR` (facultatif) : dossier inscriptible pour ces compteurs. Par défaut : le dossier temporaire du système.
- Pour débloquer quelqu'un tout de suite : supprimer le contenu de ce dossier (`rm -r <CACHE_DIR>/*`).

## 5. Vérifications après déploiement

Contrôle automatique :
```bash
python manage.py check --deploy
```
Aucun avertissement bloquant ne doit rester (la longueur de la clé est le plus fréquent).

Contrôle manuel, sur le site réel :
- [ ] Accueil, Publications, Événements, Galerie, À propos, Membres, Contact : les pages s'affichent (pas d'erreur 500).
- [ ] Menu : À propos (Qui sommes-nous, Membres), Publications avec sous-menus, Événements, Galerie, Contact.
- [ ] Publications : filtre « Séminaire Gɛlɛkan » ; l'ancienne URL `/zabantu/guelekans/` redirige.
- [ ] Formulaire d'adhésion : envoi d'une demande de test, page de remerciement, apparition dans le tableau de bord (badge du menu).
- [ ] Validation d'une demande de test : le compte membre est créé et apparaît dans la liste publique ; la révocation le retire.
      **Supprimer ensuite la demande et le membre de test.**
- [ ] Galerie : une galerie avec photos, ouverture du visualiseur (clic, plein écran, balayage sur téléphone).
- [ ] Événement : fiche d'un événement à venir (boutons d'agenda) et d'un événement passé (pas de lien de réunion).
- [ ] Connexion d'un administrateur, création d'un membre depuis le tableau de bord.
- [ ] Envoi d'un e-mail de test (réinitialisation de mot de passe) : les nouveaux identifiants SMTP fonctionnent.
- [ ] Pas de HTTPS cassé (cadenas, pas de contenu mixte) ; redirection HTTP vers HTTPS si activée.

## 6. Retour arrière

| Situation | Action |
|-----------|--------|
| Page en erreur après déploiement | Remettre l'ancienne version du code et redémarrer. Les migrations ajoutées n'empêchent pas l'ancien code de fonctionner (nouvelles tables/champs ignorés). |
| Problème de base de données | Restaurer le dump : `pg_restore -c -U <utilisateur> -d <base> <fichier>.dump` (en dernier recours : cela efface les données saisies depuis la sauvegarde). |
| Miniatures problématiques | Supprimer `MEDIA_ROOT/cache/thumbs/`. |
| Redirection HTTPS en boucle | `SECURE_SSL_REDIRECT=False` dans `.env`, redémarrer. |

## 7. Points à surveiller ensuite
- **Captcha du formulaire d'adhésion désactivé** (demande du client) : le formulaire public peut recevoir du spam. Surveiller les demandes ;
  la réactivation est une ligne de code (`site_web/forms.py`).
- **Données personnelles** : le formulaire d'adhésion collecte des coordonnées et une photo. Vérifier avec le client la mention d'information
  et la durée de conservation.
- **Audit de dette technique** (`docs/AUDIT_DETTE_TECHNIQUE.md`) : plusieurs points de sécurité de priorité 1 (contrôle des rôles,
  désabonnement newsletter, limitation des tentatives de connexion) ne sont **pas** traités par ce déploiement.
- Fichiers statiques et médias : confirmer qui les sert en production (serveur web ou application).

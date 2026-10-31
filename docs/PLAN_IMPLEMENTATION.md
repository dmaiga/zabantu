# Plan d'implémentation (fichier éphémère — à supprimer)

## 1. Ingénierie / configuration
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL` lus depuis `.env`.
- **PostgreSQL partout** (développement et production) : plus de branche SQLite dans `settings.py`. `DB_NAME`, `DB_USER`
  et `DB_PASSWORD` du `.env` sont obligatoires ; `DEBUG` ne choisit plus la base.
- Tests : `manage.py test` utilise `zabantu/settings_test.py` (SQLite en mémoire), car le rôle PostgreSQL de l'hébergeur ne peut
  pas créer de base de test. La suite a aussi été validée sur PostgreSQL 17 (199 tests).
- En production (`DEBUG=False`) : cookies sécurisés, HSTS, redirection SSL (pilotés par env), `SECRET_KEY` et `SITE_URL` obligatoires.
- **E-mail entièrement piloté par le `.env`** : serveur, port, TLS/SSL et adresses d'expéditeur des deux comptes (principal et
  info-lettre), plus `CONTACT_EMAIL`. Rien de propre au serveur n'est écrit dans le code. En SMTP, une variable manquante
  arrête le démarrage avec un message clair ; en développement les e-mails s'affichent dans la console.
- `seed_demo` refuse de s'exécuter dans une base qui contient déjà du vrai contenu (sauf `--force`).
- `.env.example` fourni, `.gitignore` corrigé (`.env`, `*.sqlite3`; migrations de nouveau versionnées), `requirements.txt` en UTF-8.

## 2. Formulaire d'adhésion (docs/input/Formulaire.docx)
- Modèle `MembershipApplication` (site_web) : infos personnelles, profil, centres d'intérêt,
  provenance (texte libre, sans suggestion — commentaire du client), contribution / apport carrière (≤ 100 mots),
  consentement obligatoire.
- Statuts : En attente → Validée / Refusée → Révoquée (avec date, auteur et motif).
- Page publique `/zabantu/adhesion/` + captcha, lien dans le menu.
- Back-office (admin Django) : liste filtrable, actions Valider / Refuser / Révoquer / Remettre en attente.

## 3. Affichage des publications
- Image de couverture entière (plus de rognage), ratio maîtrisé.
- Carte de texte compacte : interlignes et marges réduits.

## 4. Vérification
- `manage.py check`, migrations, tests du formulaire et des transitions de statut, lancement du serveur.

## 5. Branchement sur la base PostgreSQL et mise en production sans perte de données

Principe : **déployer du code ne remplace jamais la base**. Seule la commande `migrate` modifie le schéma, et uniquement par
ajouts (nouvelles tables, nouveaux champs avec valeur par défaut). Le plan réel, vérifié sur la copie de production restaurée en local :

| Migration | Effet sur la base |
|-----------|-------------------|
| `articles.0011_scheduled_status` | Aucun (choix d'un champ : pas de changement de colonne) |
| `site_web.0003` à `0005` | Création de la table des demandes d'adhésion et de ses champs |
| `site_web.0006_publicationnotice` | Création d'une table (annonces déjà envoyées) |
| `site_web.0007_infolettre_wording` | Aucun (libellés) |
| `users.0003_backoffice_access` | Ajout d'une colonne, **fausse par défaut** : seuls admins, modérateurs et superutilisateurs se connectent |

Vérification faite sur la copie locale : avant et après `migrate`, 14 comptes, 15 publications, 2 Gɛlɛkan, 4 événements,
33 abonnés, 20 messages, 31 photos, 7 intervenants : **aucune ligne perdue**.

Ordre de mise en ligne :
1. Sauvegarde `pg_dump -Fc` de la base de production et copie de `media/`.
2. Le code `articles` de la production est maintenant dans le dépôt (voir 5.1, **résolu**).
3. Déployer le code, compléter le `.env` (nouvelles variables d'e-mail, voir `.env.example`).
4. `python manage.py showmigrations`, puis `python manage.py migrate --plan` : ne doivent figurer que les migrations ci-dessus.
5. `python manage.py migrate`, `collectstatic`, redémarrage, cron `publish_scheduled`.
6. Contrôles du guide `DEPLOIEMENT_PROD.md`.

### 5.1 Code `articles` de la production : repris dans le dépôt (résolu)
La production était en avance sur le dépôt : trois migrations (`articles.0008_alter_article_article_type`,
`0009_article_page_count_article_publication_date_and_more`, `0010_alter_article_article_type`), quatre colonnes facultatives
(`page_count`, `publication_date`, `publication_place`, `publisher_book`) et un formulaire « ouvrage ». Le dossier `articles` de
production a été comparé fichier par fichier à l'état du dépôt avant ces travaux. Ont été repris :
- les trois migrations, **copiées telles quelles** ; ma migration est devenue `0011_scheduled_status` (dépend de `0010`) ;
- le modèle : les quatre champs, la liste de types de la production (« Zabantu » et « Analyse » ne sont plus dans les choix du modèle),
  `get_absolute_url`, `get_preview_text`, `get_cover` et la fusion des auteurs ;
- le formulaire `OuvrageForm` (maison d'édition et date de parution obligatoires, au moins un auteur) et son entrée dans le menu de création ;
- l'affichage des champs « ouvrage » dans la fiche de la publication, avec l'ouvrage réel de production comme cas de test.

Contrôles : `showmigrations` identique à la production (0001 à 0010) plus `0011` ; `makemigrations --check` sans changement ;
`migrate --plan` vide sur la copie locale ; l'ouvrage existant s'affiche et se modifie avec toutes ses valeurs.

Pour déployer, le dossier `articles/migrations/` du serveur doit être **remplacé** par celui du dépôt (mêmes fichiers `0001` à `0010`, plus `0011`).

### 5.2 Comparaison de tout le dossier de production (`data/site/`, 31 octobre 2026)
Chacun des 201 fichiers de production a été comparé à **toutes** les versions du dépôt : 110 sont identiques au dépôt actuel, 56 sont
identiques à une ancienne version (la production est simplement en retard : formulaire d'adhésion, refonte du site, backoffice), 4 sont
absents du dépôt et 30 ne correspondent à aucune version. Ces 30, examinés un par un, se réduisent à ce que la production a ajouté de son côté :

| Nouveauté de la production | Reprise dans le dépôt |
|---------------------------|-----------------------|
| Migrations `articles` 0008 à 0010, champs « ouvrage », `OuvrageForm`, liste de types | Oui (voir 5.1) |
| Affichage public des ouvrages (fiche : maison d'édition, lieu, pages, date ; liste : éditeur et date) | Oui, dans le nouveau design |
| Catégories publiques : « Zabantu » retiré, « académique » devient « Articles » ; menu public à plat | Oui (`CATEGORY_LABELS`, menu) |
| Icône du site (`zabantu_logo.jpg`) sur le site public et le backoffice | Oui |
| Administration des abonnés (`NewsletterSubscriber`) | Oui |
| Commande `seed_newsletter` (abonne les comptes actifs à l'info-lettre) | Oui, avec un avertissement : ces personnes n'ont pas donné leur accord |
| WhiteNoise (fichiers statiques) et stockage à empreintes | Oui, actif seulement hors `DEBUG` |
| `mysql-connector-python` dans `requirements.txt` | Non : la base est PostgreSQL |

Contrôles de mise en production : `collectstatic` sur le stockage de production (403 fichiers, manifeste généré) et 13 pages chargées avec `DEBUG=False`.

À corriger côté **serveur** (relevé dans le `settings.py` de production, à ne pas reproduire) :
- `SECRET_KEY` écrite en dur dans le code et commençant par `django-insecure-` : en générer une nouvelle et la mettre dans le `.env` (les sessions en cours seront fermées) ;
- `ALLOWED_HOSTS = ['*']` : remplacer par `zabantu.net,www.zabantu.net` ;
- chemins `/home/cp2594820p30/public_html/static` et `.../media` écrits en dur : désormais `STATIC_ROOT` et `MEDIA_ROOT` du `.env` ;
- serveur et adresses d'e-mail écrits en dur : désormais dans le `.env` (valeurs actuelles dans `DEPLOIEMENT_PROD.md`).


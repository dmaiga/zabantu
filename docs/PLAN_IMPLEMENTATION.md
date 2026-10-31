# Plan d'implémentation (fichier éphémère — à supprimer)

## 1. Ingénierie / configuration
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL` lus depuis `.env`.
- Base de données selon `DEBUG` : SQLite en debug, PostgreSQL en production (`DB_*` obligatoires).
- En production (`DEBUG=False`) : cookies sécurisés, HSTS, redirection SSL (pilotés par env), `SECRET_KEY` obligatoire.
- Identifiants e-mail uniquement via `.env`.
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

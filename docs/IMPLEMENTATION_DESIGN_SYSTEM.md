# Plan d'implémentation — migration vers le design system Zabantu

Date de rédaction : 30 octobre 2026
Statut : **à réaliser plus tard** (aucune ligne de code modifiée pour ce document).
Source : `docs/Design system Zabantu.html` (livrable de Claude Design), analysé le 30 octobre 2026.
Périmètre : site public (`site_web`) et pages d'authentification (`users/auth_base.html` et dérivées).
Hors périmètre : tableau de bord d'administration (`users/templates/base.html`), application mobile, mode sombre.

Les durées sont des ordres de grandeur pour un développeur. Les constats viennent de la lecture du design system et des
templates ; aucun rendu n'a été testé avec le thème appliqué.

---

## 1. Objectif et principes

Remplacer les styles dispersés dans chaque template (≈ 30 blocs `<style>`, trois `:root` dupliqués, palette sauge/bronze)
par **un thème unique** (`zabantu-theme.css`) alimenté par des **jetons** (`tokens.json`), tout en **gardant Bootstrap 5.3**.

Principes de la migration :
1. **Progressif** : le site reste fonctionnel à chaque étape ; on migre page par page.
2. **Un seul endroit pour une valeur** : plus aucune couleur, taille ou rayon en dur hors de `:root`.
3. **Bootstrap d'abord** : si un composant Bootstrap existe, on le thème par ses variables plutôt que de le réécrire.
4. **Composants maison préfixés `zb-`** : jamais de nom qui entre en collision avec Bootstrap.
5. **Rien de visuel n'est perdu en route** : captures avant/après pour chaque page (voir section 8).

## 2. État des lieux du design system reçu

### 2.1 Ce que le fichier contient
| Élément | Présent ? | Remarque |
|---------|-----------|----------|
| Jetons CSS `--zb-*` (couleurs, polices, tailles fluides, espacements, rayons, ombres) | Oui, dans le CSS de la page | À extraire. |
| Contrastes WCAG calculés | Oui (10 paires recalculées : toutes exactes) | Reste fiable. |
| Composants (boutons, navbar, cartes, champs, assistant, messages, pagination, tableau, états vides, remerciement, membre, galerie, pied de page) | Oui, comme **démonstration** dans la page | Noms non préfixés, à adapter. |
| Règles d'usage, accessibilité, logo, évolution | Oui, en texte | À reprendre dans un README. |
| `zabantu-theme.css` | **Non** | À produire. |
| `tokens.json` | **Non** (cité dans la page) | À produire. |
| Pont vers Bootstrap (`--bs-*`) | **Non** (annoncé, 0 occurrence) | À produire. |
| Mode sombre | Non (volontairement) | Hors périmètre. |

### 2.2 Écarts à corriger avant d'utiliser le CSS tel quel
1. **Collisions de noms avec Bootstrap** : `.btn`, `.btn-primary`, `.btn-sm`, `.btn-lg`, `.card`, `.nav`, `.row` sont redéfinis par la
   page de démonstration. Les classes utilitaires de la page (`.wrap`, `.grid`, `.panel`, `.hero`, `.sg-*`, `.mono`…) appartiennent au
   styleguide, **pas** au thème : ne pas les copier.
2. **Lettres « ɛ » et « ɔ » absentes de Source Serif 4** (vérifié sur les fichiers Google Fonts : ɛ, ɔ, Ɛ, Ɔ absents ; présents dans
   Source Sans 3). Voir 3.4 pour le correctif.
3. **Polices chargées depuis Google Fonts** : à héberger sur le site (connexion instable possible à Bamako, et pas d'appel tiers).
4. **Logo JPEG à fond blanc** : utilisable uniquement sur fond blanc. Pas de version blanche ni monochrome.
5. Aucune valeur d'orange/jaune confirmée sur le fichier source du logo.

## 3. Phase A — Fondations (≈ 1,5 à 2 jours)

### 3.1 Extraire les jetons
Le fichier est un paquet auto-extractible ; le contenu réel est dans les blocs `<script type="__bundler/...">`. Pour le relire
(sans exécuter de code), décoder le gabarit (JSON) et le manifeste (base64, gzip) :

```python
import re, json, base64, gzip
h = open('docs/Design system Zabantu.html', encoding='utf8').read()
block = lambda t: re.search(r'<script type="__bundler/%s">(.*?)</script>' % t, h, re.S).group(1)
template = json.loads(block('template'))          # HTML + CSS de la page (≈ 76 Ko)
manifest = json.loads(block('manifest'))          # logo (JPEG) et bibliothèques React
for uuid, asset in manifest.items():
    data = base64.b64decode(asset['data'])
    if asset.get('compressed'): data = gzip.decompress(data)
```
Les jetons sont dans le premier bloc `:root{...}` du `<style>` du gabarit (≈ 70 variables).

Livrables :
- `site_web/static/site_web/css/zabantu-tokens.css` : uniquement le bloc `:root` (couleurs, polices, tailles, espacements, rayons, ombres).
- `site_web/static/site_web/tokens/tokens.json` au format **W3C Design Tokens** (couleurs hex, tailles px, durées ms) — source unique pour
  l'application mobile (Style Dictionary → Swift/Kotlin/Dart). Les deux fichiers doivent rester synchrones : générer le CSS depuis le JSON
  ou, à défaut, contrôler leur cohérence par un test.

### 3.2 Thème Bootstrap (`zabantu-theme.css`)
Charger **après** `bootstrap.min.css`. Contenu, dans l'ordre :
1. **Pont de variables Bootstrap** (`:root`) :

| Variable Bootstrap | Valeur (jeton) |
|--------------------|----------------|
| `--bs-body-font-family` | `var(--zb-font-sans)` |
| `--bs-body-color` / `--bs-body-bg` | `--zb-color-text` / `--zb-color-bg-page` |
| `--bs-heading-color` | `--zb-color-brand` |
| `--bs-link-color` / `--bs-link-hover-color` | `--zb-color-action` / `--zb-color-action-hover` |
| `--bs-primary`, `--bs-primary-rgb` | `--zb-color-action` (+ valeur RGB) |
| `--bs-border-color` | `--zb-color-border` |
| `--bs-border-radius` (sm / base / lg / pill) | 6 px / 12 px selon usage / 999 px |
| `--bs-success`, `--bs-warning`, `--bs-danger`, `--bs-info` | états du design system |
| `--bs-focus-ring-color` | bleu focus `#0e5e83` |

2. **Boutons Bootstrap thématisés** (sans réécrire `.btn`) en redéfinissant les variables locales de Bootstrap 5.3 :
   `.btn-primary { --bs-btn-bg; --bs-btn-border-color; --bs-btn-hover-bg; --bs-btn-hover-border-color; --bs-btn-active-bg; --bs-btn-color … }`
   et idem pour `.btn-outline-primary`. Ajouter `.btn-accent` (jaune, texte brand) ; forme pilule ; `min-height: 2.75rem`.
3. **Typographie** : `h1–h4` en `--zb-font-serif`, tailles `--zb-text-*` avec `clamp()`, `text-wrap: balance`.
4. **Focus visible global** (`:focus-visible`, anneau 3 px, jaune sur fond sombre), **lien d'évitement**, `prefers-reduced-motion`.
5. **Utilitaires de lecture** : `.zb-prose` (68ch, interligne 1,65, police serif).

### 3.3 Polices hébergées
- Télécharger Source Serif 4 (400, 600, 700, italique 400) et Source Sans 3 (400, 600, 700) en `woff2`, sous-ensembles `latin` et `latin-ext`
  (licence SIL OFL : redistribution autorisée).
- Déclarer les `@font-face` (`font-display: swap`) dans `zabantu-fonts.css` ; précharger les 2 fichiers critiques
  (`<link rel="preload" as="font" crossorigin>`).
- Supprimer l'appel Google Fonts de `users/templates/users/auth_base.html` (page de connexion) au profit du thème.

### 3.4 Correctif « ɛ » et « ɔ »
Problème : dans un titre (Source Serif 4), « Gɛlɛkan » afficherait ɛ dans une police de secours.
Solutions, de la plus simple à la plus lourde :
1. **Recommandée** : ajouter une police de secours qui contient ces lettres, limitée à ces glyphes. Déclarer
   `@font-face { font-family: "Zb Africa"; src: url(...noto-serif-subset.woff2); unicode-range: U+0186, U+0190, U+0254, U+025B; }`
   (sous-ensemble de Noto Serif, quelques Ko) et l'insérer dans la pile : `"Source Serif 4", "Zb Africa", Georgia, serif`.
   Le navigateur n'utilise `Zb Africa` que pour ces quatre caractères.
2. Alternative : envelopper les occurrences dans un `<span class="zb-sans">` (Source Sans 3). Fragile, à éviter.
3. Alternative : changer de police serif pour une qui contient ces glyphes (à retester entièrement).
Contrôle : page de test avec « Gɛlɛkan ɔ Ɛ Ɔ » en h1, h2, corps de texte et dans les deux graisses.

### 3.5 Branchement
- Dans `site_web/templates/base_public.html` : charger `zabantu-fonts.css`, `zabantu-tokens.css`, `zabantu-theme.css` après Bootstrap ;
  supprimer le bloc `:root` et les styles d'en-tête/pied de page locaux (migrés en phase B).
- Dans `users/templates/users/auth_base.html` : mêmes fichiers ; supprimer les `:root` et Google Fonts.
- Utiliser `{% load static %}` et `{% static %}` (les chemins `/static/...` en dur actuels sont à remplacer).
- Mettre `STATIC_ROOT` / `collectstatic` à l'ordre du jour (voir `docs/DEPLOIEMENT_PROD.md`, section 4.4).

**Critères de réussite A** : le site s'affiche avec les nouvelles couleurs, polices et boutons sans toucher aux templates de pages ;
aucun bouton bleu Bootstrap n'apparaît ; « Gɛlɛkan » s'affiche correctement ; `collectstatic` fonctionne.

## 4. Phase B — Composants (≈ 4 à 6 jours)

Convention : classes `zb-*`, uniquement des variables `--zb-*`, états normal / survol / focus / désactivé / erreur, cible de 44 px,
aucune variante réservée à une seule page.

| Composant | Classe cible | Remplace (existant) | Remarques |
|-----------|--------------|---------------------|-----------|
| En-tête / navbar | `zb-header`, `zb-nav` | styles de `base_public.html` (`.zabantu-header`, `.nav-link`, sous-menus, `.admin-link`) | Fond blanc, filet brand 4 px. **Conserver** les sous-menus (survol / clic) ; réécrire leur CSS avec les jetons. |
| Pied de page | `zb-footer` | styles `.zabantu-footer`, `.footer-social` | Fond brand, texte `text-inverse`. Logo : voir risque R3. |
| Bandeau de titre | `zb-pagehead` | `.zabantu-banner` | Dégradé marque, fil d'Ariane intégré. |
| Carte de contenu | `zb-card` (+ `--horizontal`, `--vertical`) | `.pub-card` (liste publications), `.home-card` (accueil), `.ev-card` / `.ev-past` (événements), `.gal-card` (galeries), `.seminar-card`, `.member-card` | **Un seul composant** ; image en `object-fit: contain` sur `bg-media` pour les affiches/couvertures, `cover` réservé aux photos (variante `zb-card--photo`). |
| Étiquettes (types) | `zb-tag` + `--publication`, `--event`, `--seminar`, `--member` | `.badge-type`, `.home-card-badge`, `.ev-type`, `.pub-category`, `.gal-featured` | Couleurs et contrastes du design system. Toujours texte + icône. |
| Filtres en pilules | `zb-chips` | `.ev-filters`, `.page-filters`, filtres de `public_article_list.html` | Défilement horizontal sur mobile. |
| Boutons | `.btn` Bootstrap thématisé | surcharges locales `index.html` (bronze), `.btn-submit`, `.btn-wizard`, `.btn-zabantu` | Supprimer toutes les surcharges de pages. |
| Formulaires | `zb-field`, `zb-choice` (cartes de choix), `zb-file` | styles de `public_membership_form.html`, `public_contact.html`, `auth_base.html` | Erreur : texte + icône, `border-strong` sur les champs. |
| Assistant (stepper) | `zb-stepper` | `.stepper` (adhésion) | États actif / visité / erreur déjà présents ; reprendre les couleurs du design system. |
| Messages | `zb-alert` (+ succès / info / alerte / erreur) | `.alert-*` hétérogènes, `error-alert`, `notice-*` | Mapper `message.tags` : `error` → `danger`. |
| Pagination | `.pagination` Bootstrap thématisé | blocs « Précédent / Page X sur Y / Suivant » répétés | Extraire en `{% include %}` unique (`includes/pagination.html`). |
| États vides | `zb-empty` | `.ev-empty`, `.events-empty`, `.empty-state` | |
| Page de remerciement | `zb-thanks` | `public_membership_thanks.html` | |
| Fiche membre | `zb-member` | `.team-mini`, `.member-card`, `.team-initials` | Photo ronde (pilule), repli initiales. |
| Galerie | `zb-gallery` | `.photo-masonry`, `.photo-tile` | Garder la maçonnerie et PhotoSwipe ; seulement retokeniser. |
| Visionneuse | PhotoSwipe | `includes/photo_viewer_*.html` | Thème de la légende et boutons aux couleurs du système. |

Livraison conseillée de la phase B en trois lots : (1) en-tête, pied de page, boutons, bandeau ; (2) carte + étiquettes + filtres +
pagination ; (3) formulaires, assistant, messages, états vides.

**Critères de réussite B** : chaque composant n'existe qu'une fois dans le CSS ; aucune page n'utilise plus de style local pour ces
composants.

## 5. Phase C — Passage page par page (≈ 4 à 5 jours)

Inventaire actuel (lignes de template, blocs `<style>` à supprimer ou réduire) et travail attendu :

| Ordre | Page | Template | Lignes | Travail |
|------:|------|----------|-------:|---------|
| 1 | Accueil | `index.html` | 266 | Héros, publications (carte), événements, bandeau d'adhésion, chiffres, équipe, partenaires, newsletter. Retirer ~170 lignes de CSS. |
| 2 | Publications (liste) | `public_article_list.html` | 433 | Filtres latéraux, recherche, carte, pagination ; branche Gɛlɛkan. |
| 3 | Publication (détail) | `public_article_detail.html` | 213 | Typographie éditoriale (`zb-prose`, 68ch), couleurs hors palette (indigo/violet) à supprimer. |
| 4 | Événements (liste, détail) | `public_event_list.html`, `public_event_detail.html` | 129 / 630 | Carte, filtres, boutons d'agenda, intervenants. Détail = gros gabarit. |
| 5 | Galerie (4 pages) | `public_liste_galeries.html`, `public_detail_galerie.html`, `public_toutes_photos.html`, `public_detail_photo.html` | 69 / 61 / 63 / 72 | Carte galerie, maçonnerie, filtres, fiche photo. |
| 6 | Gɛlɛkan (détail) | `public_guelekan_detail.html` | 616 | Plus gros gabarit ; couleurs hors palette possibles. |
| 7 | À propos, Membres | `public_about.html`, `public_member_list.html`, `public_member_detail.html` | 548 / 187 / 223 | `.section-title`, `.identity-card`, `.team-grid`, fiche membre. |
| 8 | Contact, Adhésion, Remerciement | `public_contact.html`, `public_membership_form.html`, `public_membership_thanks.html` | 193 / 336 / 38 | Formulaires, assistant. |
| 9 | Connexion et réinitialisation | `users/auth_base.html`, `login.html`, `password_reset*.html` | 239 / 61 / … | Déjà mutualisé : changer la base suffit. E-mail HTML : harmoniser les couleurs (styles en ligne obligatoires). |
| 10 | Pages secondaires | `membre_articles.html`, `newsletter_unsubscribe_*.html`, `public_publications.html` (vide) | 418 / 23 / 21 / 0 | `membre_articles.html` semble peu utilisé : vérifier avant de migrer ou supprimer. |

Pour chaque page :
1. Capture « avant » (bureau 1280 px, mobile 375 px).
2. Remplacer les classes locales par les composants `zb-*` et classes Bootstrap thématisées.
3. Supprimer le bloc `<style>` devenu inutile (ou le réduire à la mise en page propre à la page).
4. Capture « après », contrôle clavier, contraste, textes longs, états vides.
5. Lancer la suite de tests (`python manage.py test`) : les 53 tests existants doivent rester verts.

## 6. Phase D — Accessibilité et contrôle (≈ 1,5 à 2 jours)

- Lien d'évitement en première position du `<body>` de `base_public.html` et `auth_base.html`.
- Un seul `h1` par page ; hiérarchie `h2/h3` cohérente (vérifier avec une extension d'audit).
- Parcours **clavier** complet : menu et sous-menus, filtres, assistant d'adhésion, visionneuse photo, formulaires.
- Contrastes : script qui lit `tokens.json` et vérifie les paires déclarées (≥ 4,5:1 texte, ≥ 3:1 composants).
- `prefers-reduced-motion` : désactiver transitions et `transform` au survol.
- Lighthouse (accessibilité, bonnes pratiques) sur accueil, publications, détail, événement, galerie, contact, adhésion ; objectif ≥ 95 en accessibilité.
- Test réel sur un téléphone Android d'entrée de gamme et en connexion lente (poids des polices, des images).

## 7. Décisions à prendre avant de démarrer

| # | Décision | Qui | Impact |
|---|----------|-----|--------|
| D1 | **Barre de navigation** : les 6 liens du design system ou nos 5 entrées actuelles (À propos ▾, Publications ▾, Événements, Galerie, Contact) ; bouton « Rejoindre Zabantu » dans la barre ou non (retiré à la demande du client) | Client | Phase B (en-tête). |
| D2 | Le client accepte-t-il le **vert d'action plus foncé** que celui du logo (`#3e6b24`) ? | Client | Aspect de tous les boutons et liens. |
| D3 | **Logo** : obtenir le SVG et un PNG transparent, versions blanche et monochrome | Client / graphiste | Pied de page, en-tête sur fond coloré. |
| D4 | Valeurs exactes de l'**orange** et du **jaune** du logo (relevées « à l'œil ») | Client | Étiquettes événements et accents. |
| D5 | Solution pour « ɛ » et « ɔ » (3.4) | Équipe | Titres contenant « Gɛlɛkan ». |
| D6 | Héberger les polices en local (recommandé) | Équipe | Performance, confidentialité. |
| D7 | Conserver ou non `membre_articles.html` | Équipe | Évite un travail inutile. |

## 8. Stratégie de test et de non-régression

- **Captures** : avant/après de chaque page en 1280 px et 375 px, rangées dans `docs/captures/` (hors dépôt si trop lourdes).
- **Tests automatiques** (Django) : conserver la suite existante ; ajouter des tests simples
  - le thème est chargé sur chaque page publique (présence de `zabantu-theme.css`) ;
  - aucune page publique ne contient de couleur de l'ancienne palette (`#6f826a`, `#bf9264`) ni d'indigo (`#6366f1`) ;
  - `tokens.json` est valide et cohérent avec `zabantu-tokens.css`.
- **Recherche de dette** : `grep` des couleurs hexadécimales dans `site_web/templates` et `users/templates` doit tendre vers zéro hors e-mails HTML.
- **Mise en production progressive** : déployer d'abord la phase A + lot B1 sur un environnement de recette, valider avec le client, puis le reste.

## 9. Risques

| # | Risque | Parade |
|---|--------|--------|
| R1 | Le CSS de démonstration entre en collision avec Bootstrap (`.btn`, `.card`, `.nav`, `.row`) | Ne jamais copier tel quel ; préfixer `zb-` ; thématiser Bootstrap par variables. |
| R2 | « ɛ » / « ɔ » mal affichés dans les titres | Correctif 3.4 + page de test. |
| R3 | Logo JPEG fond blanc sur en-tête ou pied de page sombres (rectangle blanc visible) | En-tête blanc ; pied de page sans logo tant que la version blanche n'existe pas. |
| R4 | Gros gabarits (Gɛlɛkan 616 lignes, événement 630, À propos 548) : régressions visuelles | Migration en dernier, captures avant/après, tests manuels. |
| R5 | Couleurs d'orange/jaune non confirmées | Les isoler dans les jetons ; remplaçables sans toucher aux pages. |
| R6 | E-mails HTML : styles en ligne, pas de variables CSS | Valeurs recopiées à la main depuis les jetons ; les noter dans le gabarit. |
| R7 | Estimation sensible au contenu réel (images, textes longs) | Valider sur de vraies données dès la phase A. |
| R8 | Cumul avec les changements non commités et la mise en production | Commit avant de démarrer ; une branche dédiée ; déployer par lots. |

## 10. Calendrier indicatif

| Étape | Durée | Cumul |
|-------|-------|-------|
| A — Fondations | 1,5 à 2 j | 2 j |
| B1 — En-tête, pied de page, boutons, bandeau | 1,5 j | 3,5 j |
| B2 — Carte, étiquettes, filtres, pagination | 1,5 à 2 j | 5,5 j |
| C1 — Accueil + Publications (liste et détail) | 1,5 j | 7 j |
| **Jalon 1 : ≈ 70 % de l'effet visuel livrable** | | **≈ 7 j** |
| B3 — Formulaires, assistant, messages, états vides | 1 à 1,5 j | 8,5 j |
| C2 — Événements, galerie, Gɛlɛkan | 2 à 2,5 j | 11 j |
| C3 — À propos, membres, contact, adhésion, connexion | 1,5 j | 12,5 j |
| D — Accessibilité et recette | 1,5 à 2 j | **≈ 14 j** |

(Fourchette globale : 11 à 15 jours, cf. analyse du 30 octobre 2026.)

## 11. Liste de contrôle de fin de migration

- [ ] `zabantu-theme.css`, `zabantu-tokens.css`, `tokens.json`, polices locales en place et chargés une seule fois.
- [ ] Aucun `:root` ni couleur en dur dans les templates publics (hors e-mails).
- [ ] Un seul composant carte, un seul style de bouton, un seul jeu d'étiquettes.
- [ ] Aucun bouton bleu Bootstrap, aucune couleur indigo/violet, aucun emoji d'interface.
- [ ] « Gɛlɛkan » correct dans toutes les graisses et tailles.
- [ ] Lien d'évitement, focus visible, navigation clavier complète, contrastes AA.
- [ ] Lighthouse accessibilité ≥ 95 sur les pages clés ; poids de page vérifié sur mobile.
- [ ] README du design system (chargement, variables, règles d'usage) dans le dépôt.
- [ ] Tests Django verts ; captures avant/après validées par le client.
- [ ] Documentation de déploiement mise à jour (`collectstatic`, nouveaux fichiers statiques).

# Analyse UI/UX du site public et proposition de charte graphique — Zabantu

Date : 30 octobre 2026
Périmètre : site public (`site_web/templates/base_public.html` et ses pages : accueil, à propos, publications, Gɛlɛkan,
événements, membres, galerie, contact, adhésion).
Nature du document : analyse et proposition. **Rien n'a été modifié dans le code** suite à ce document.

Méthode : lecture du code des templates, comptages automatiques (couleurs, polices, tailles, boutons), calcul des contrastes
WCAG et examen du logo. **Pas de test utilisateur ni de captures d'écran de toutes les pages** ; les constats visuels
(rendu réel, mobile) sont à confirmer en navigateur. Seules la page publications (capture du client) et l'adhésion ont été vues rendues.

---

## 1. Synthèse

Le site a une **identité reconnaissable** (palette vert sauge, bronze, fond crème ; typographie à empattement qui évoque
la recherche) et une structure claire. Son principal problème est l'**absence de système de design partagé** : chaque page
redéfinit ses propres styles, ce qui produit des écarts visibles (boutons bleus Bootstrap à côté de boutons verts, tailles de texte
différentes, quatre styles de cartes…) et des défauts d'accessibilité (contrastes insuffisants, police système imprévisible).

| # | Constat | Gravité |
|---|---------|---------|
| 1 | Police `Georgia` seule, sans hiérarchie typographique ni police de titre : rendu variable selon l'appareil | Haute |
| 2 | Boutons bleus Bootstrap par défaut sur la plupart des pages (le vert n'est redéfini que dans `index.html`) | Haute |
| 3 | Contrastes insuffisants : texte blanc sur vert primaire (4,14:1) et sur bronze (2,80:1) | Haute |
| 4 | Le logo (vert vif, bleu, orange) n'est pas relié à la palette du site (sauge, bronze) | Moyenne |
| 5 | Couleurs étrangères à la palette (indigo, violet, bleu Bootstrap) dans certaines pages | Moyenne |
| 6 | Pas d'échelle typographique ni d'espacements : 20 tailles de texte et 8 rayons de bordure différents | Moyenne |
| 7 | Styles dupliqués dans chaque template (≈ 14 000 lignes HTML, CSS en ligne) | Moyenne |
| 8 | Accessibilité : focus clavier, `h1` manquants, alternatives d'images, cibles tactiles | Moyenne |
| 9 | Navigation : 9 entrées + menu déroulant à 12 liens, appel à l'action « Adhésion » noyé | Moyenne |
| 10 | Pied de page et bandeau de titre peu hiérarchisés ; emojis comme icônes sur certaines pages | Basse |

---

## 2. État des lieux

### 2.1 Identité visuelle actuelle
- **Logo** : illustration (lianes vertes entrelaçant « Zabantu », livre ouvert bleu, loupe grise, fruits orange/jaune), avec la
  signature « Economy / Conflict / State ». Fichier JPEG avec fond blanc, placé sur un en-tête vert foncé : le rectangle blanc est
  visible. Il n'existe pas de version vectorielle ni à fond transparent.
- **Palette déclarée** (variables `--zabantu-*`, redéclarées dans 3 fichiers) :

| Rôle | Valeur | Usage actuel |
|------|--------|--------------|
| Primaire (sauge) | `#6f826a` | boutons, titres, bandeaux |
| Secondaire (bronze) | `#bf9264` | liseré d'en-tête, accents |
| Accent (vert clair) | `#bbd8a3` | liens du pied de page, survols |
| Clair (crème) | `#f0f1c5` | fonds de sections, séparateurs |
| Foncé (vert forêt) | `#2c3e2c` | en-tête, pied de page, titres |

  Le fond de page est `#f8f9fa` (gris très clair Bootstrap), non crème : la couleur « clair » et le fond réel sont différents.
- **Typographie** : `font-family: 'Georgia', serif` sur `body`, **une seule déclaration dans tout le site**. Aucune police
  web chargée. Titres, boutons, formulaires et navigation héritent de la même police (ou de la police système pour les
  contrôles de formulaire, selon Bootstrap). Navigation en gras (`font-weight: 700`).
- **Composants** : Bootstrap 5.3.0 et Font Awesome 6.4.0 chargés depuis des CDN.

### 2.2 Chiffres relevés dans les templates du site public
- 26 couleurs hexadécimales distinctes, dont plusieurs hors palette (voir 3.3).
- 20 tailles de police différentes (de 0,75 rem à 3 rem), sans échelle ; la même fonction (titre de carte, légende, méta) change de taille d'une page à l'autre.
- 8 rayons de bordure différents (2, 4, 6, 8, 10, 12, 20, 30 px).
- Boutons : 16 `btn-outline-primary`, 10 `btn-primary`, 8 `btn-outline-secondary`… mais la couleur de `btn-primary` n'est
  redéfinie que dans `index.html` (lignes ~98–113). Partout ailleurs, ces boutons s'affichent en **bleu Bootstrap `#0d6efd`**,
  ce qui rompt avec l'identité verte.
- Seulement 6 occurrences de chargement différé des images.

---

## 3. Analyse détaillée

### 3.1 Typographie (priorité haute)
Constats :
- Georgia est une police système : présente sur Windows et macOS, mais **absente sur beaucoup d'appareils Android/Linux**,
  où le navigateur la remplace par une autre police à empattement (rendu et largeurs différents, donc mises en page qui bougent).
- Une seule famille pour tout : pas de contraste entre titres, texte courant, interface (boutons, menus, formulaires).
  La navigation en gras Georgia est lourde et peu lisible à petite taille.
- Pas de hiérarchie : les `h1`/`h2`/`h3` reprennent les styles Bootstrap par défaut ; chaque page ajuste ses tailles.
- Chiffres : Georgia utilise des chiffres elzéviriens (anciens) qui s'alignent mal dans les dates, compteurs et tableaux.

Proposition : associer **une police à empattement pour les titres et les contenus éditoriaux** (identité « recherche ») à **une
sans-empattement pour l'interface** (navigation, boutons, formulaires, étiquettes). Voir la charte, section 4.2.

### 3.2 Couleurs et contrastes (priorité haute)
Contrastes calculés (WCAG 2.1 ; seuil AA : 4,5:1 pour le texte normal, 3:1 pour le grand texte et les composants) :

| Combinaison | Ratio | Verdict |
|-------------|-------|---------|
| Texte `#333` sur fond `#f8f9fa` | 12,0:1 | Très bon |
| Blanc sur vert forêt `#2c3e2c` (en-tête, pied de page) | 11,5:1 | Très bon |
| Accent `#bbd8a3` sur vert forêt | 7,4:1 | Très bon |
| Gris `#6c757d` sur blanc / sur `#f8f9fa` | 4,7 / 4,45:1 | Limite (échec sur fond gris) |
| **Blanc sur primaire `#6f826a`** (boutons, bandeau, filtres actifs) | **4,14:1** | **Insuffisant en texte normal** |
| Primaire `#6f826a` sur blanc (titres, liens) | 4,14:1 | **Insuffisant en texte normal** |
| **Blanc sur secondaire `#bf9264`** | **2,80:1** | **Échec** |
| Secondaire `#bf9264` sur blanc | 2,80:1 | **Échec** (pour du texte) |
| Primaire sur crème `#f0f1c5` | 3,56:1 | Insuffisant |

Conséquences : les boutons verts avec texte blanc (« Lire la suite », « Voir les détails », filtre actif) et le texte bronze
sont difficiles à lire, surtout sur mobile en plein soleil. C'est un point d'attention important pour un public universitaire
qui lit sur téléphone.

Proposition : **assombrir légèrement** le vert primaire pour les boutons et le texte (≈ `#566a52`, 5,7:1 avec du blanc) tout en
gardant la teinte sauge actuelle pour les fonds décoratifs, et utiliser un bronze plus foncé (≈ `#8a6238`) quand il sert de texte.

### 3.3 Cohérence des couleurs
- Couleurs hors palette trouvées : indigo `#6366f1`, violet `#8b5cf6`, `#4f46e5` dans `public_article_detail.html`, `event_detail.html`
  et les pages de réinitialisation de mot de passe ; bleus Bootstrap `#0d6efd`, `#007bff`, `#86b7fe` ; rouge Bootstrap.
- Les variables `--zabantu-*` sont **définies à trois endroits** (`base_public`, `public_about`, `public_contact`) avec les mêmes valeurs :
  une modification de la palette demande de toucher plusieurs fichiers.
- Le **logo contient du bleu, un vert vif et de l'orange** absents de la palette. La palette sauge/bronze est plus sobre que le logo,
  ce qui crée un décalage. Deux voies possibles : (a) conserver la palette sobre et traiter le logo comme une signature à part
  (version sur fond blanc), (b) introduire le bleu et l'orange du logo comme couleurs d'accent secondaires (voir 4.1).

### 3.4 Composants et cohérence visuelle
- **Boutons** : voir 2.2. Quatre variantes (`btn-primary`, `btn-outline-primary`, boutons maison `.read-more`, `.btn-submit`,
  `.btn-wizard`…) pour la même action. Le client a lui-même remarqué des incohérences d'affichage sur les cartes de publications.
- **Cartes** : au moins quatre styles (publications, événements, Gɛlɛkan, membres), avec des ombres, rayons et espacements différents.
  Le correctif récent des cartes de publications (couverture entière, textes compacts) n'a pas été répercuté sur les autres listes.
- **Images** : usage de `background-image` / `object-fit: cover` dans 11 templates publics ; risque de rognage des couvertures
  (déjà constaté par le client sur les publications). Il manque une règle unique (ratio, `contain` pour les documents/affiches,
  `cover` pour les photos).
- **Badges / étiquettes** : catégories, types, statuts (« Zabantu », « Académique », « Indépendant ») sans code couleur commun.
- **Icônes** : Font Awesome partout, mais quelques emojis (📰 🏢 📅 📭) pour les détails d'articles et les états vides : rendu
  différent selon les systèmes, et mélange de deux langages d'icônes.
- **Bandeau de titre** (`zabantu-banner`) : dégradé vert avec le titre en `h1` ; la page publications et plusieurs pages de liste n'ont
  pas d'autre `h1` visible. Les pages qui ne suivent pas ce gabarit (publications, événements, membres) ont zéro `h1` dans leur propre
  template (il vient du bandeau hérité : à vérifier page par page).

### 3.5 Navigation et parcours
- Barre principale : À propos, Publications (menu déroulant de 12 liens répartis en « Editorial » / « Scientifique »…),
  Events, Gɛlɛkan, Membres, Galerie, Adhésion, Contact + recherche + lien d'administration. C'est dense pour un site de cette taille.
- Mélange de langues dans les libellés : « Events » (anglais) à côté de « Galerie », « Membres », « A propos » (sans accent sur le « À »).
- Le **lien « Adhésion » est au même niveau que les autres** : alors que l'adhésion est un objectif principal du groupe, aucun
  appel à l'action distinct (bouton) ne la met en avant, ni sur l'accueil, ni dans l'en-tête.
- Le lien d'administration (« admin-link ») est visible pour tous les visiteurs dans l'en-tête.
- La recherche est un bouton qui déploie un champ : bonne idée mais le champ est masqué sans libellé accessible.
- L'accueil enchaîne : héros → événements à venir → publications → newsletter. Il manque : présentation courte des axes de recherche
  (Economy / Conflict / State, pourtant la signature du logo), chiffres clés, appel à rejoindre le groupe, partenaires.

### 3.6 Mobile et responsive
- 11 templates contiennent des règles `@media`, mais avec des seuils différents (576, 768, 992 px) définis page par page.
- Le menu déroulant de publications (12 liens) est long sur mobile.
- Points positifs : filtres de publications convertis en « pilules » horizontales défilantes ; formulaire d'adhésion pensé mobile.
- À vérifier en navigateur : taille des cibles tactiles (boutons de la barre de recherche 40 px < 44 px recommandés), tableaux et
  grilles des pages d'événements/Gɛlɛkan (616 et 604 lignes de HTML), lisibilité des méta-données sous les titres.

### 3.7 Accessibilité
- **Focus clavier** : aucun style `:focus-visible` défini ; le champ de recherche supprime l'outline (`outline: none`) sans remplacement.
- **Contrastes** : voir 3.2.
- **Titres** : quelques pages ont un seul `h1` (bien), d'autres 2 (`public_liste_galeries.html`) ou aucun dans leur propre contenu ;
  hiérarchie des `h2`/`h3` non garantie.
- **Images** : les images de couvertures affichées en `background-image` n'ont pas de texte alternatif ; plusieurs balises `img` sans
  attribut `alt` explicite sur les pages de détail à vérifier (accueil, Gɛlɛkan).
- **Liens d'évitement** (« Aller au contenu ») et rôles ARIA : absents.
- **Langue** : `lang="fr"` présent (bien). Les dates sortent en anglais (« 29 August 2026 ») à cause de `LANGUAGE_CODE = 'en-us'`.
- Animation : transformations au survol (cartes) sans prise en compte de `prefers-reduced-motion`.

### 3.8 Performance perçue (impact UI)
- Bootstrap et Font Awesome complets chargés depuis des CDN (≈ 300 Ko de CSS/JS/polices), alors qu'une partie seulement est utilisée.
- Une seule image de logo JPEG de taille élevée (l'image fait ≈ 1024 px de large pour s'afficher à 70 px de haut).
- Peu d'images en chargement différé ; couvertures chargées en pleine taille.

---

## 4. Proposition de charte graphique

> Les valeurs ci-dessous sont **des propositions à valider** avec le client. Les contrastes indiqués sont calculés.

### 4.1 Couleurs

**Principe** : conserver l'ADN actuel (sauge, bronze, crème, vert forêt), corriger les contrastes et définir des rôles clairs.

| Rôle | Nom | Valeur | Usage | Contraste |
|------|-----|--------|-------|-----------|
| Marque | Forêt | `#2c3e2c` | en-tête, pied de page, titres de niveau 1 | 11,5:1 avec blanc |
| Action | Sauge foncé | `#566a52` | boutons principaux, liens, filtre actif | 5,7:1 avec blanc |
| Marque (fond) | Sauge | `#6f826a` | fonds décoratifs, bandeaux, illustrations (jamais pour du petit texte) | — |
| Accent chaud | Bronze foncé | `#8a6238` | texte d'accent, étiquettes | 5,4:1 sur blanc |
| Accent chaud (fond) | Bronze | `#bf9264` | liserés, séparateurs, puces | décoratif |
| Accent clair | Vert tendre | `#bbd8a3` | survols sur fond sombre, surlignages | 7,4:1 sur Forêt |
| Fond doux | Crème | `#f0f1c5` | encadrés, sections alternées | — |
| Fond de page | Ivoire | `#f8f9f4` | fond du site (remplace `#f8f9fa`, légèrement chaud) | — |
| Texte | Encre | `#26302a` | texte courant | ≈ 13:1 sur ivoire |
| Texte secondaire | Gris sauge | `#5b6559` | méta-données, légendes | ≈ 5,6:1 sur ivoire |
| Bordures | Brume | `#d9ddd2` | cadres, séparateurs | — |

**États** : succès `#2f7a4b`, alerte `#9a6a00`, erreur `#b3261e`, information `#2a6f97` — à utiliser pour les messages, badges de statut
et validations de formulaires, à la place des bleus/rouges Bootstrap.

**Couleurs issues du logo (option)** : bleu du livre `#2a7fc4` et orange du fruit `#e8883a`, à n'utiliser que pour des
illustrations, des catégories (une couleur par axe de recherche : Economy / Conflict / State) ou des infographies, **jamais pour le texte courant**.

**À supprimer** : indigo/violet (`#6366f1`, `#8b5cf6`, `#4f46e5`) et bleus Bootstrap hors des messages d'information.

### 4.2 Typographie

**Recommandation (polices libres, Google Fonts, hébergeables localement)** :

| Usage | Police | Graisses | Justification |
|-------|--------|----------|---------------|
| Titres (h1–h3), citations, chiffres clés | **Source Serif 4** (ou *Lora* en alternative) | 600, 700 | empattements modernes très lisibles à l'écran, ton académique ; chiffres lisibles |
| Texte courant éditorial (articles) | **Source Serif 4** | 400, 400 italique | lecture longue confortable |
| Interface : navigation, boutons, formulaires, étiquettes, méta | **Inter** (ou *Source Sans 3*) | 400, 500, 600 | police d'interface neutre, excellente à petite taille, chiffres tabulaires |

Pile de secours : `"Source Serif 4", Georgia, "Times New Roman", serif` et `Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.
Chargement avec `font-display: swap` ; limiter à 2 familles et 5 fichiers de police pour rester léger (hébergement local recommandé
plutôt qu'un appel à Google Fonts, pour la performance et la confidentialité des visiteurs).

**Échelle typographique** (base 16 px, rapport ≈ 1,25 ; tailles fluides sur mobile) :

| Niveau | Police | Taille (bureau / mobile) | Graisse | Interligne |
|--------|--------|--------------------------|---------|------------|
| Titre de page (h1) | Serif | 2,5 rem / 1,9 rem | 700 | 1,2 |
| Titre de section (h2) | Serif | 1,9 rem / 1,5 rem | 700 | 1,25 |
| Sous-titre (h3) | Serif | 1,4 rem / 1,25 rem | 600 | 1,3 |
| Titre de carte (h4) | Serif | 1,2 rem | 600 | 1,3 |
| Texte courant | Serif (article) / Sans (interface) | 1,05 rem (article) – 1 rem | 400 | 1,6 |
| Texte secondaire / méta | Sans | 0,875 rem | 400–500 | 1,5 |
| Étiquette / badge | Sans | 0,75 rem | 600, capitales légères | 1 |
| Bouton | Sans | 1 rem | 600 | 1 |
| Navigation | Sans | 0,95 rem | 500 | 1 |

Règles : jamais moins de 14 px pour du texte lisible ; longueur de ligne de 60 à 75 caractères pour les articles ; texte aligné à gauche
(pas de justification) ; pas de gras pour toute la navigation.

### 4.3 Espacement, formes et élévation
- **Grille d'espacement** : multiples de 4 px (4, 8, 12, 16, 24, 32, 48, 64). Remplace les marges et paddings ad hoc.
- **Rayons** : 3 valeurs seulement — petit 6 px (champs, boutons), moyen 10 px (cartes), pilule 999 px (filtres, badges).
- **Ombres** : 2 niveaux — repos `0 1px 3px rgba(0,0,0,.08)`, survol/élévation `0 6px 16px rgba(0,0,0,.12)`.
- **Largeur de contenu** : conteneur 1140 px ; texte d'article 720 px.

### 4.4 Composants de référence
1. **Boutons** : *Principal* (fond Sauge foncé, texte blanc), *Secondaire* (contour Sauge foncé, fond transparent), *Accent* (Bronze foncé, pour
   l'adhésion), *Lien* (souligné au survol). Même hauteur minimale de 44 px, même rayon, même transition. Un seul style par action, quelle que soit la page.
2. **Cartes** : un composant unique « carte de contenu » (image au ratio fixe, étiquette, titre, méta, extrait, lien) décliné en
   horizontal (listes) et vertical (accueil). Image : `contain` + fond neutre pour les couvertures de documents, `cover` pour les photos.
3. **Étiquettes** : forme pilule, couleur selon le type (Zabantu = Sauge, Académique = Gris sauge, Indépendant = Bronze, Événement = Bleu logo).
4. **Formulaires** : étiquette au-dessus, aide en gris sauge, erreur en rouge `#b3261e` avec icône, hauteur de champ 46 px, focus visible 3 px.
5. **Bandeau de titre** : dégradé Forêt → Sauge, titre serif, fil d'Ariane, un seul `h1`.
6. **En-tête** : logo sur fond blanc dédié (ou version transparente), 6 entrées maximum, bouton « Rejoindre Zabantu » distinct,
   recherche avec libellé.
7. **Pied de page** : 3 colonnes (À propos / Navigation / Contact et réseaux), mentions légales, newsletter.
8. **Messages** : 4 états (succès, info, alerte, erreur) avec icône, couleur et texte (jamais la couleur seule).
9. **Icônes** : Font Awesome uniquement (ou jeu d'icônes SVG unique) ; suppression des emojis.

### 4.5 Logo et usages
- Demander au client les fichiers sources (vectoriel `.svg`/`.ai`/`.pdf`) ; sinon redessiner/détourer une version PNG transparente.
- Produire 3 versions : couleur (fond clair), monochrome vert forêt, blanche (fond sombre). Zone de protection autour du logo = hauteur de la lettre « Z ».
- Taille minimale : 40 px de haut à l'écran, 20 mm à l'impression. Supprimer le JPEG à fond blanc de l'en-tête sombre.
- Ajouter un favicon carré (liane/« Z ») et les icônes d'application (180 px, 512 px) ; l'actuel `favicon.ico` n'est pas dans les fichiers livrés avec le site (à vérifier).

### 4.6 Ton éditorial (rédactionnel)
- Libellés de navigation et boutons en **français** (« Événements » plutôt que « Events », « À propos » avec accent).
- Verbes d'action clairs : « Rejoindre Zabantu », « Lire la publication », « S'abonner ».
- Dates en français (« 29 août 2026 ») : nécessite `LANGUAGE_CODE = 'fr'` côté configuration.

---

## 5. Recommandations par priorité

### P1 — Fondations (impact élevé, risque faible)
1. Créer **un fichier CSS commun** avec les variables de la charte (couleurs, polices, tailles, espacements, rayons, ombres) et le charger dans `base_public.html` ; supprimer les trois déclarations `:root`.
2. Charger **les deux polices** (hébergées localement) et définir `body`, titres et interface.
3. Redéfinir `btn-primary` / `btn-outline-primary` globalement avec les variables Bootstrap (`--bs-primary`, etc.) pour supprimer les boutons bleus partout d'un coup.
4. Corriger les **contrastes** (vert d'action, bronze texte, gris secondaire) et ajouter un **focus visible** global.
5. Un seul `h1` par page, vérification des textes alternatifs, lien d'évitement.

### P2 — Cohérence des composants
6. Composant carte unique, appliqué aux publications, Gɛlɛkan, événements, membres ; règle de rognage des images partagée.
7. Badges/étiquettes, messages et formulaires harmonisés ; remplacement des emojis.
8. Simplifier la **navigation** (≤ 6 entrées + bouton d'adhésion) et traduire les libellés ; masquer le lien d'admin pour les visiteurs non connectés ou le déplacer dans le pied de page.
9. Retirer les couleurs hors palette (indigo, violet) dans les pages d'article, d'événement et de réinitialisation.

### P3 — Évolutions
10. Refonte de l'accueil : bloc « Nos 3 axes » (Economy / Conflict / State), appel à rejoindre, chiffres clés, partenaires.
11. Logo vectoriel et variantes ; optimisation des images (formats WebP, tailles adaptées, chargement différé).
12. Mode sombre (optionnel) et prise en compte de `prefers-reduced-motion`.
13. Documenter la charte dans une **page « guide de style »** interne (composants, couleurs, polices) pour les futures contributions.

### Estimation indicative (ordre de grandeur)
- P1 : 2–3 jours · P2 : 4–6 jours · P3 : 5+ jours. À valider une fois la charte approuvée par le client.

---

## 6. Points à valider avec le client
1. Maintenir la palette sobre sauge/bronze, ou intégrer le bleu et l'orange du logo en accents ?
2. Accord sur le couple de polices (Source Serif 4 + Inter) ou préférence pour d'autres (ex. Lora + Source Sans 3) ?
3. Disponibilité du logo en vectoriel et d'une version sans fond.
4. L'adhésion est-elle l'objectif n°1 du site (bouton d'en-tête) ?
5. Faut-il un mode bilingue (français/anglais) ? Le sous-titre « Economy | Conflict | State » est en anglais, et plusieurs libellés mélangent les deux.

## 7. Limites de cette analyse
- Pas de tests utilisateurs, d'analyse de trafic ni de mesure de performance réelle (Lighthouse) ; ces mesures compléteraient les constats 3.6 à 3.8.
- Pas de revue de l'interface d'administration (dashboard), hors périmètre « site public ».
- Les polices et couleurs proposées sont à tester sur les vraies pages (rendu, longueurs de titres, textes en caractères africains/latins étendus : les polices proposées
  couvrent le latin étendu, mais vérifier les caractères « ɛ » et « ɔ » utilisés dans « Gɛlɛkan »).

# Prompt — Design system Zabantu (à donner à Claude Design)

Joindre : `site_web/static/site_web/images/zabantu_logo.jpg` et une capture de la page des publications.

```
Tu es designer UI/design systems. Crée le design system du site web du Groupe de recherche ZABANTU
(Economy | Conflict | State), un groupe de chercheurs en sciences sociales basé au Mali. Le système doit
être SIMPLE, EXPLOITABLE tel quel par un développeur, et réutilisable plus tard pour une application mobile.

## 1. Contexte technique (contraintes fortes)
- Le site est en Django (templates HTML) avec BOOTSTRAP 5.3. On reste sur Bootstrap : ne propose pas Tailwind.
- Aucune étape de compilation : le livrable doit fonctionner avec de simples fichiers CSS chargés après Bootstrap.
- Le thème doit surcharger Bootstrap via ses variables CSS (--bs-primary, --bs-body-font-family,
  --bs-border-radius, --bs-link-color, etc.) pour que les composants Bootstrap existants (btn, card, badge,
  alert, navbar, form-control, pagination, dropdown) prennent le thème SANS modifier les templates.
- Icônes : Font Awesome 6 uniquement (pas d'emoji).
- Public : chercheurs, étudiants, institutions ; lecture surtout sur MOBILE. Approche mobile-first.
- Langue : français. Prévoir des libellés longs. Le texte contient des caractères « ɛ » et « ɔ » (ex. « Gɛlɛkan ») :
  les polices choisies doivent les afficher correctement (sinon propose une alternative et signale-le).

## 2. Identité à respecter : le logo (fichier joint : logo Zabantu)
Le logo est une illustration : lettres en lianes vertes, livre ouvert bleu, loupe grise, fruits orange et jaune,
signature « Economy / Conflict / State » en noir.
- Extrais les couleurs du logo et construis la palette de marque à partir d'elles (verts de la feuille et des lianes,
  bleu du livre, orange du fruit, jaune, noir/vert très foncé). Ces couleurs REMPLACENT l'ancien vert sauge (#6f826a)
  et le bronze (#bf9264) du site.
- Valeurs approximatives vues dans le logo (à affiner depuis l'image) : vert feuille ~#8ac04f, vert profond ~#28382d,
  bleu du livre ~#1b6d8a, orange du fruit, jaune du fruit.
- Garde l'esprit « recherche sérieuse mais vivante » : sobre, aéré, lisible, pas de style startup.
- Les couleurs vives du logo (vert feuille, orange, jaune) ont un contraste insuffisant avec le blanc : n'en fais
  JAMAIS un fond de bouton ou une couleur de texte courant. Dérive-en des versions foncées pour l'action et le texte.

## 3. Livrables attendus
A. Un fichier unique `zabantu-theme.css` : variables (:root) + surcharges Bootstrap + quelques composants maison.
   Commenté, organisé en sections, prêt à être chargé après bootstrap.min.css.
B. Un fichier `tokens.json` (format simple clé/valeur ou W3C Design Tokens) avec : couleurs, typographie, espacements,
   rayons, ombres, points de rupture, durées d'animation. C'est la source unique, réutilisable pour une future
   application mobile (iOS/Android/Flutter/React Native) : n'utilise donc que des valeurs portables (pas de classes CSS dans les tokens).
C. Une page `styleguide.html` autonome (HTML + zabantu-theme.css + Bootstrap en CDN) qui montre TOUS les composants, en
   clair et avec les états (normal, survol, focus, désactivé, erreur), consultable sur mobile et bureau.
D. Un court `README` (une page) : comment charger le thème, liste des variables, règles d'usage (« faire / ne pas faire »).

## 4. Contenu du système
1. COULEURS, avec un nom et un rôle pour chacune (pas de nuancier arbitraire) :
   - marque (vert profond pour en-tête/pied de page/titres), action (couleur des boutons et liens), accent(s)
     issus du logo (bleu, orange, jaune) pour les catégories et illustrations, fonds (page, carte, section alternée),
     texte (courant, secondaire, inversé), bordures,
   - 4 états : succès, alerte, erreur, information,
   - une échelle de 5 à 6 nuances pour les couleurs principales (50 → 900).
   Exigence : TOUT texte atteint un contraste WCAG AA (4,5:1 ; 3:1 pour le grand texte et les composants).
   Fournis un tableau des paires texte/fond avec le ratio calculé. Vérifie en particulier blanc sur couleur d'action.
2. TYPOGRAPHIE : 2 familles maximum, libres de droits (Google Fonts, hébergeables localement) :
   une police à empattement pour les titres et le texte éditorial (ton académique), une sans-empattement pour
   l'interface (navigation, boutons, formulaires, méta). Propose-moi tes choix avec justification
   (suggestions de départ : Source Serif 4 + Inter, ou Lora + Source Sans 3). Fournis :
   piles de secours, graisses utilisées, échelle de tailles h1–h4 / corps / méta / étiquette / bouton, valeurs bureau
   ET mobile (tailles fluides avec clamp()), interlignes, longueur de ligne maximale pour les articles (60–75 caractères).
3. ESPACEMENTS, RAYONS, OMBRES : grille de 4 px ; 3 rayons seulement (petit, moyen, pilule) ; 2 niveaux d'ombre ;
   largeur de conteneur ; largeur de colonne de texte.
4. COMPOSANTS (version Bootstrap surchargée ou classes préfixées `zb-`) :
   - boutons : principal, secondaire (contour), accent, lien ; tailles ; hauteur tactile minimale 44 px ;
   - navbar du site (logo, 6 liens maximum, menu déroulant, recherche rétractable, bouton « Rejoindre Zabantu » bien visible,
     version mobile avec menu replié) ;
   - bandeau de titre de page (dégradé de marque, h1, fil d'Ariane) ;
   - carte de contenu UNIQUE (publication, événement, séminaire, membre), en variantes horizontale (listes) et verticale (accueil) ;
     règle d'image : ratio fixe ; `object-fit: contain` + fond neutre pour les couvertures de documents, `cover` pour les photos ;
   - étiquettes/badges de type et de statut (couleur par type), filtres en « pilules » défilantes sur mobile,
   - formulaires : champ, sélection, cases à cocher et boutons radio en cartes, zone de fichier, aide, erreur, focus visible ;
   - assistant en plusieurs étapes (« stepper » numéroté, étape active / visitée / en erreur) pour le formulaire d'adhésion ;
   - messages (succès, info, alerte, erreur) avec icône + texte ; pagination ; tableau ; état vide ; page de remerciement ;
   - pied de page (3 colonnes, newsletter, réseaux sociaux), fiche membre (photo ronde, liens sociaux), galerie photo.
5. ACCESSIBILITÉ : focus visible partout (anneau 3 px), cibles tactiles ≥ 44 px, `prefers-reduced-motion` respecté,
   pas d'information portée par la couleur seule, lien d'évitement « Aller au contenu ».
6. MODE SOMBRE : optionnel, uniquement si cela reste simple (inversion par variables) ; sinon à signaler comme évolution.
7. LOGO : propose les règles d'usage (versions couleur / monochrome / blanche, zone de protection, taille minimale,
   fond conseillé) et signale que le fichier fourni est un JPEG à fond blanc, à remplacer par un vectoriel/PNG transparent.

## 5. Règles de conception
- Simplicité d'abord : peu de couleurs, peu de composants, noms parlants (--zb-color-action, --zb-space-4, pas de noms obscurs).
- Cohérence : un seul style par type d'action ; pas de variante « juste pour cette page ».
- Chaque valeur du CSS vient d'un token ; aucune valeur « en dur » en dehors de :root.
- Les noms de variables sont préfixés `--zb-` et doivent pouvoir devenir les noms de tokens de la future application.
- Prévois l'évolution : indique comment ajouter une couleur ou un composant sans casser le reste.

## 6. Format de réponse
Fournis d'abord (en 10 lignes) tes choix principaux : palette, polices, justification. Puis les 4 livrables complets.
Termine par la liste des points à faire valider par le client et par un tableau des contrastes.
```

## Après réception du design system
1. Placer `zabantu-theme.css` et `tokens.json` dans `site_web/static/site_web/`.
2. Charger le thème dans `base_public.html` après Bootstrap ; supprimer les trois blocs `:root` dupliqués.
3. Remplacer progressivement les styles par page par les composants du thème (publications d'abord, puis les autres listes).
4. Retirer les couleurs hors palette (indigo, violet, bleus Bootstrap) et les emojis.

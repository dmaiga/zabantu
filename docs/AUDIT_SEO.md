# Audit SEO restreint de Zabantu

Date : 10 novembre 2026  
Périmètre : corrections techniques discrètes, compatibles avec le fonctionnement actuel.  
Base de validation : dump et médias de production du 11 novembre 2026 restaurés en local.

## Décision de cadrage

Le propriétaire du projet a décidé de **restreindre volontairement l'audit SEO** afin que les améliorations restent simples, progressives et non contraignantes pour le client.

Le travail retenu ne doit pas :

- imposer la création de nouveaux contenus ;
- modifier l'organisation éditoriale ou scientifique de Zabantu ;
- demander aux modérateurs de reprendre les anciennes publications ;
- modifier les fichiers ou les données historiques importées ;
- entraîner une refonte importante des URL, des modèles ou des gabarits ;
- rouvrir les lots don, images et cache déjà terminés ;
- retarder les lots bilingue et formations prévus dans le `todo`.

L'objectif n'est donc pas de maximiser toutes les possibilités SEO, mais de corriger quelques signaux techniques sans casser l'existant.

## Vérifications effectuées sur les données de production

La base et les médias de production ont été restaurés localement avant cette validation.

| Contenu | Résultat |
|---|---:|
| Articles publiés | 19 |
| Articles antérieurs au 1er novembre 2026 | 15 |
| Articles sans date de publication | 0 |
| Articles publiés dans le futur | 0 |
| Gɛlɛkan publiés | 2 |
| Gɛlɛkan sans `publish_at` | 1 |
| Événements publiés | 4 |
| Galeries | 3 |
| Photos | 31 |
| Photos ayant un nom brut d'appareil comme titre | 31 |
| Membres publics actifs | 13 |
| Entrées produites par le sitemap actuel | 4 |

Tous les articles, Gɛlɛkan et événements publiés ont un identifiant ou un slug valide. Leurs URL publiques peuvent être générées sans erreur. Les migrations du dump sont compatibles avec l'état actuel du code.

Cette vérification ne met en évidence aucun risque lié aux anciennes données pour les changements limités ci-dessous.

## Points déjà satisfaisants

- Les pages sont rendues en HTML et restent accessibles sans JavaScript.
- Les brouillons et publications programmées ne sont pas exposés prématurément.
- Les pages possèdent déjà des balises Open Graph et Twitter Card.
- `robots.txt` existe et déclare le sitemap.
- Les publications disposent de titres, résumés, auteurs, dates et liens vers leurs documents quand ils existent.
- Les pages de membres sont reliées à leurs publications.
- Les miniatures, dimensions d'images et chargements différés du lot 2 améliorent les performances visuelles.
- Les optimisations et le cache du lot 3 ont déjà fortement réduit le temps serveur.
- Le bilingue FR/EN est déjà pris en charge par le lot 4 en cours.

## Périmètre technique retenu

### 1. Conserver `SEO_START_DATE` avec une date compatible

`SEO_START_DATE` a été introduite volontairement après la refonte afin de protéger les anciennes données. Cette sécurité est conservée.

La valeur du 1er novembre 2026 exclut toutefois 15 des 19 articles, les 4 événements et un Gɛlɛkan du sitemap. Le dump vérifié contient des contenus valides remontant à septembre 2025.

**Décision retenue :** utiliser le **1er janvier 2025** comme date de départ. Cette date :

- conserve le garde-fou souhaité ;
- inclut toutes les données de production actuellement connues ;
- ne modifie aucune ligne de la base ;
- agit seulement sur les canonical et le sitemap.

### 2. Gérer le Gɛlɛkan publié sans `publish_at`

Un Gɛlɛkan de production est publié sans date `publish_at`. La logique des métadonnées utilise déjà `created_at` comme valeur de repli, mais le sitemap l'exclut encore.

**Décision retenue :** utiliser `created_at` uniquement lorsque `publish_at` est absent. Cela aligne le sitemap sur le comportement existant, sans migration ni modification des données.

### 3. Compléter modérément le sitemap

Le sitemap doit rester simple. Il inclura seulement les URL publiques principales et les contenus déjà publiés :

- accueil canonique ;
- listes des publications, événements, membres et galeries ;
- page À propos ;
- articles, Gɛlɛkan et événements publiés admis par `SEO_START_DATE` ;
- profils des membres actifs ;
- galeries publiques.

Sont exclus : recherches internes, tris, formulaires de remerciement, désabonnements, zones privées et combinaisons arbitraires de paramètres.

Le sitemap ne change ni le contenu visible ni les droits d'accès.

### 4. Conserver `/zabantu/` comme accueil principal

Le routage actuel produit les URL suivantes :

- accueil français : `/zabantu/` ;
- publications : `/zabantu/publications/` ;
- accueil anglais : `/en/zabantu/`.

Le chemin `/` affiche aussi l'accueil, ce qui crée deux adresses pour le même contenu.

**Décision retenue :**

- conserver `/zabantu/` comme accueil canonique afin de respecter les liens générés par le site ;
- rediriger uniquement `/` vers `/zabantu/` avec une redirection permanente ;
- appliquer le même principe à `/en/` vers `/en/zabantu/` ;
- ne pas modifier les autres URL publiques.

Les favoris et anciens liens vers `/` continueront donc de fonctionner.

### 5. Améliorer le titre SEO des photos sans renommer les fichiers

Les 31 photos de production ont toutes un titre ressemblant à un nom brut d'appareil, de capture ou de messagerie. Le modèle possède déjà `display_title`, qui masque ces noms au public.

**Décision retenue :**

- titre descriptif disponible : `Titre de la photo – Nom de l'album | Zabantu` ;
- titre brut ou masqué avec album : `Nom de l'album – Photo | Zabantu` ;
- photo indépendante sans titre descriptif : `Photo – Zabantu`.

Aucun fichier ne sera renommé et aucune donnée ne sera réécrite.

### 6. Ne pas élargir le lot bilingue

Le lot 4 du `todo` contient déjà le sélecteur de langue, les adresses `/en/`, `hreflang` et le sitemap bilingue. Le SEO doit seulement accompagner ce travail, sans créer un nouveau chantier.

Les exigences restent limitées à :

- une valeur `<html lang>` correspondant à la langue affichée ;
- des liens FR/EN cohérents avec les URL existantes ;
- des canonical qui restent dans la même langue ;
- aucune obligation de traduire rétroactivement les contenus.

## Améliorations explicitement hors périmètre

Les recommandations suivantes ne font pas partie des travaux demandés. Elles ne constituent ni des anomalies ni des conditions de livraison.

### Travail éditorial ou institutionnel

- construire des pages thématiques ;
- enrichir ou réécrire les anciennes publications ;
- produire des résumés, mots-clés ou traductions supplémentaires ;
- développer l'autorité scientifique et rechercher des liens externes ;
- gérer ORCID, Google Scholar, LinkedIn ou les relations avec les partenaires ;
- définir une stratégie de contenu, de conversion ou de communication.

Ces décisions appartiennent à Zabantu et non au périmètre du développement actuel.

### Améliorations techniques facultatives

- ajouter une couverture complète de données structurées JSON-LD ;
- transformer les filtres en nouvelles URL propres ;
- revoir globalement tous les titres, H1 et descriptions ;
- mettre en place un nouveau système analytics ou un tableau mensuel ;
- optimiser davantage la pagination et les paramètres de recherche ;
- ajouter dès maintenant le balisage de la future application de cours.

Ces travaux pourront être réévalués plus tard si le client les demande. Ne pas les réaliser ne casse pas le SEO existant.

## Effort estimé

| Travail retenu | Effort indicatif |
|---|---:|
| Ajustement de `SEO_START_DATE` et repli du Gɛlɛkan | 0,25 j |
| Sitemap public limité | 0,25–0,5 j |
| Redirections exactes des deux accueils | 0,25 j |
| Titres des photos basés sur l'album | 0,25 j |
| Tests de non-régression FR/EN et données de production | 0,25–0,5 j |
| **Total estimé** | **1–1,5 j** |

## Validation attendue avant livraison

Les changements ne seront considérés comme terminés qu'après vérification des points suivants :

- `/` redirige vers `/zabantu/` et les autres pages gardent leur adresse ;
- `/en/` redirige vers `/en/zabantu/` sans boucle ;
- les 19 articles, 2 Gɛlɛkan et 4 événements restent accessibles ;
- le Gɛlɛkan sans `publish_at` n'entraîne aucune erreur ;
- le sitemap est un XML valide et ne contient que des URL publiques ;
- les contenus antérieurs au 1er novembre 2026 mais postérieurs au 1er janvier 2025 sont inclus ;
- les brouillons et contenus futurs restent exclus ;
- les photos avec un nom brut utilisent le titre de leur album sans modifier le fichier ;
- les tests existants et les tests SEO ciblés passent ;
- aucune migration de données n'est nécessaire.

## Conclusion

Le périmètre retenu est volontairement conservateur. Il améliore les signaux techniques les plus simples tout en préservant les données, les URL publiques, le travail des modérateurs et la feuille de route existante.

Les recommandations plus ambitieuses de l'audit initial sont reportées hors périmètre. Elles ne devront être reprises que sur demande explicite du client.

## Références techniques

- [Google — Consolidation des URL dupliquées](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Google — Créer et envoyer un sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Google — Versions localisées](https://developers.google.com/search/docs/specialty/international/localized-versions)

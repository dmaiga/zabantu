# Audit SEO et aperçu des liens partagés — Zabantu

Date : 1er novembre 2026  
Périmètre : code des pages publiques du dépôt. Le site de production et ses données n'ont pas été audités directement : la tentative d'accès au site a expiré. Aucun changement fonctionnel n'est inclus dans ce document.

## Objectif retenu

Zabantu est surtout découvert par l'envoi direct de liens. La priorité est donc **l'aperçu d'une nouvelle publication quand son URL est partagée**, puis la qualité des informations de la page. Le référencement naturel peut rester secondaire. Les publications déjà présentes et leurs URL doivent continuer à fonctionner normalement ; il n'est pas nécessaire de leur appliquer rétroactivement les nouvelles balises.

Le terme recherché est **Open Graph**. Ses balises `og:title`, `og:description`, `og:image`, `og:url` et `og:type` décrivent le titre, le texte, l'image, l'adresse et le type de contenu présentés lors du partage. Une carte pour X/Twitter peut aussi être précisée avec `twitter:card`, par exemple `summary_large_image`. Chaque réseau décide finalement de l'affichage et peut conserver un ancien aperçu en cache : les balises ne garantissent pas un rendu identique partout. Référence : [protocole Open Graph](https://ogp.me/).

## Constats vérifiés dans le dépôt

| Priorité pour Zabantu | Constat | Preuve dans le code | Effet possible |
|---|---|---|---|
| Haute | Le modèle public ne fournit aucun emplacement pour les métadonnées propres à une page. Il émet une description générique unique. | `site_web/templates/base_public.html`, lignes 7–8 | Une publication partagée peut afficher une description générique ou un extrait choisi par la plateforme. |
| Haute | Le détail Gɛlɛkan définit un bloc `meta` avec des balises Open Graph, mais `base_public.html` ne rend pas ce bloc. | `site_web/templates/site_web/public_guelekan_detail.html`, lignes 6–13 | Ces balises ne figurent pas dans le HTML final. |
| Haute | Les pages de détail des articles et événements ne définissent pas de balises Open Graph ni de carte X/Twitter. | `site_web/templates/site_web/public_article_detail.html` ; `site_web/templates/site_web/public_event_detail.html` | Le titre, le texte ou l'image de l'aperçu ne sont pas maîtrisés. |
| Moyenne | Les articles possèdent déjà `meta_title` et `meta_description`, mais la page publique ne les utilise pas. Gɛlɛkan possède aussi ces champs. | `articles/models.py` ; modèles de détail publics | Les données éditoriales SEO existantes ne servent pas à l'affichage public. |
| Basse dans le contexte actuel | Aucune URL canonique, aucun `/sitemap.xml` ni `/robots.txt` n'est défini dans les routes Django inspectées. Les listes créent des URL filtrées et paginées. | `zabantu/urls.py` ; `site_web/urls.py` ; `site_web/views.py` | La découverte et le regroupement des URL par les moteurs sont moins pilotés. À vérifier aussi côté serveur de production. |
| Basse | La hiérarchie des titres varie : le détail article affiche un H1 de bandeau puis un H1 d'article ; le détail événement affiche un H1 générique puis son titre en H2. | `site_web/templates/base_public.html` ; modèles de détail | Le sujet principal de certaines pages est moins clairement présenté. |

Les URL publiques existantes sont déclarées dans `site_web/urls.py`, incluses sous `/zabantu/` par `zabantu/urls.py`. Les pages de détail des articles et événements filtrent déjà les contenus sur le statut `published` dans `site_web/views.py`.

## Travail proposé lors d'une future implémentation

1. Prévoir dans le modèle HTML public un emplacement pour les balises de partage. Pour **une nouvelle publication éligible seulement**, renseigner un titre, une description, une URL absolue et une image publique ; utiliser une image par défaut adaptée au partage si la publication n'a pas de couverture. Inclure `og:image:alt` lorsque l'image a un texte descriptif. Prévoir `twitter:card` pour l'aperçu sur X.
2. Définir explicitement le critère « nouvelle publication » au moment du déploiement. Une date d'activation configurée peut éviter une migration de base. Le critère doit rester stable après redémarrage et s'appuyer sur la date de création ou sur une règle éditoriale clairement choisie. Il faut tester les publications créées juste avant et juste après cette date. Les anciens enregistrements ne sont pas réécrits.
3. Conserver les routes, slugs et liens existants. Aucune migration destructive ni redirection des anciennes publications n'est nécessaire pour les aperçus de partage. Les modifications du modèle commun doivent être conditionnelles pour que le HTML des anciennes publications reste identique sur ce point.
4. Vérifier avec la copie proche de la production : une ancienne URL d'article, de Gɛlɛkan et d'événement ; une nouvelle URL de chaque type ; le HTML de leurs balises ; le statut HTTP ; et le chargement des images depuis l'extérieur. Une image accessible uniquement après connexion ne peut pas servir correctement aux plateformes de partage.
5. Après déploiement, tester le partage réel sur les plateformes utilisées par Zabantu, notamment WhatsApp, Facebook, LinkedIn et X si pertinent. L'aperçu peut rester temporairement ancien à cause du cache de la plateforme.

La piste sitemap et URL canoniques peut être examinée plus tard, si la recherche naturelle devient un objectif. Si elle est retenue, elle devra préserver la disponibilité des anciennes URL et ne pas inclure de brouillons dans le sitemap. Un sitemap aide à la découverte, sans garantir l'indexation : [documentation Google](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview).

## Protection des données et limites

- Le présent audit n'a modifié ni base de données, ni modèle, ni route, ni page publique.
- Le plan de partage peut être réalisé par ajout conditionnel de balises dans le HTML, sans mise à jour des enregistrements déjà stockés et sans migration de schéma.
- Avant tout déploiement futur : sauvegarde vérifiée de la base et des médias, comparaison sur la copie proche de la production, puis contrôle des anciennes URL. Cela réduit le risque ; aucune modification logicielle ne fournit une garantie absolue sans ces vérifications.
- Les mesures de visibilité dans Google, l'indexation effective et les aperçus servis aujourd'hui par les réseaux sociaux restent **non vérifiés sur la production**.

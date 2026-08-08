# GeoEcon Pulse

**Dashboard interactif de veille géoéconomique mondiale** couvrant cinq zones stratégiques : Canada, États-Unis, Chine, Inde et Reste du monde. Conçu pour offrir une lecture rapide et rigoureuse des dynamiques macroéconomiques et géopolitiques en cours.

*Interactive global geoeconomic intelligence dashboard covering five strategic zones: Canada, United States, China, India and the World.*

![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Static Site](https://img.shields.io/badge/Stack-HTML%20%2F%20CSS%20%2F%20JS-orange?style=flat-square)

---

## Fonctionnalités

- **5 tableaux de bord régionaux** — Indicateurs macroéconomiques clés (PIB, inflation, taux directeur, taux de chômage, taux de change, indice boursier) avec tendances
- **Indicateur de sentiment** — Évaluation calculée par règles explicites à partir des indicateurs du jour (positif / neutre / négatif)
- **Actualités filtrées** — 8 titres par région, retenus par un filtre de pertinence géoéconomique et restreints à une liste d'éditeurs de référence
- **Résumés composés** — Synthèse de 3-4 phrases par région, dérivée des valeurs courantes plutôt que rédigée d'avance
- **Mini-graphiques de tendance** — Sparklines sur 12 mois pour un indicateur clé par région
- **Module Interconnexions** — Visualisation en réseau des liens économiques entre régions + chronologie des événements clés
- **Filtres thématiques** — Commerce, Politique monétaire, Énergie, Tech, Géopolitique
- **Bilingue FR/EN** — Bascule instantanée, avec des actualités lues dans la presse de chaque langue plutôt que traduites automatiquement
- **Méthodologie publique** — [Une page](methodologie.html) qui expose les sources, le filtre d'actualités et les seuils de fraîcheur
- **Responsive** — Optimisé pour desktop et mobile
- **Zéro dépendance de build** — Un seul fichier HTML, déployable en ouvrant le fichier

## Données et sources

Les données sont stockées dans `data/indicators.json` et rafraîchies automatiquement trois fois par jour par GitHub Actions.

Toutes les API listées ci-dessous sont publiques et ne demandent aucune clé. Aucun jeton n'est stocké dans le dépôt.

| Indicateur | Régions | Source lue automatiquement |
|---|---|---|
| Taux de chômage, variation de l'emploi | Canada, États-Unis | Statistique Canada (Web Data Service), Bureau of Labor Statistics |
| Inflation IPC | Canada | Banque du Canada (API Valet) |
| Inflation IPC | États-Unis, Chine, Inde | BLS, avec l'entrepôt SDMX de l'OCDE en source première pour la Chine et l'Inde et en repli pour les États-Unis |
| Taux directeur | Canada, États-Unis | Banque du Canada (API Valet), Fed de New York |
| Taux directeur | Chine, Inde | Banque des règlements internationaux (jeu WS_CBPOL) |
| Taux de change | Canada, Chine, Inde | Frankfurter / Banque centrale européenne |
| Indices boursiers et sparklines | toutes | Yahoo Finance, OCDE, Valet |

Ne restent saisies à la main que les prévisions annuelles de croissance et les agrégats mondiaux du FMI, révisés une ou deux fois l'an. Le pipeline surveille l'âge de chaque indicateur daté et ouvre une issue au-delà de 100 jours, sans interrompre la publication des données fraîches du même passage. La procédure est détaillée dans [MISE_A_JOUR_MANUELLE.md](MISE_A_JOUR_MANUELLE.md).

Trois sources ont été évaluées puis écartées, faute d'être à jour : DBnomics (miroir du BLS arrêté à janvier 2025), l'API DataMapper du FMI (bloquée par son réseau de diffusion) et l'entrepôt SDMX du FMI (millésime d'octobre 2025, antérieur au WEO d'avril 2026).

### Cadence

Les passages sont calés sur le calendrier des diffuseurs : Statistique Canada et le BLS publient à 8 h 30 heure de l'Est. Le workflow s'exécute à 12 h 50 et 13 h 50 UTC, ce qui couvre l'heure avancée comme l'heure normale, puis à 21 h 30 UTC après la clôture des marchés nord-américains.

## Méthodologie

### Sélection des indicateurs
Les indicateurs macroéconomiques (PIB, inflation, taux directeur, taux de chômage, taux de change, indice boursier) ont été retenus pour leur capacité à offrir une lecture rapide de la conjoncture économique d'une région. Ils couvrent les dimensions réelle, monétaire et financière.

### Sélection des actualités
Le filtre est implémenté dans `scripts/news_filter.py`. Un titre doit franchir quatre étapes :

1. **Veto catégoriel** — sport, faits divers, divertissement et curiosités scientifiques sont écartés quel que soit le reste du titre.
2. **Veto conditionnel** — météo, politique intérieure de procédure et rappels de produits ne passent que si un terme géoéconomique fort les accompagne.
3. **Score de pertinence** — un terme fort suffit (tarif, sanction, taux directeur, chaîne d'approvisionnement, terres rares…), sinon il faut deux termes moyens accompagnés d'une portée macro : un État, une institution ou un agrégat de marché. Un nom de dirigeant ne compte pour rien : c'est un acteur, pas un sujet.
4. **Crédibilité de l'éditeur** — les résultats de requête sont restreints à une liste d'agences, de quotidiens économiques et d'institutions de référence.

Les titres retenus sont ensuite dédupliqués par recouvrement de vocabulaire et plafonnés à trois par éditeur, pour éviter qu'un flux bavard n'occupe une région entière.

Jusqu'à trois des huit places sont réservées aux sources d'analyse (*Financial Times*, *The Economist*, Bloomberg, *WSJ*, *New York Times*, Peterson Institute, *Globe and Mail*, *Le Monde*, *Les Échos*, *La Presse*, *Le Devoir*, Nikkei Asia, SCMP). Sans cette réserve, un classement par pure fraîcheur laissait la dépêche du jour repousser systématiquement l'analyse de la veille.

`scripts/test_news_filter.py` rejoue 95 titres réellement parus, en français comme en anglais, dont ceux qui n'avaient rien à y faire. Le workflow refuse de publier si ce test échoue.

Les faux positifs se voient immédiatement, ils atterrissent en page d'accueil ; les faux négatifs sont invisibles par construction. `scripts/rapport_rejets.py` agrège chaque lundi les titres écartés de la semaine et met en avant ceux qui portaient un vocabulaire économique malgré leur rejet.

### Actualités en français

Le mode français ne traduit pas les titres anglais : il lit la presse francophone à la source, avec le même filtre. Faire réécrire par une machine un titre attribué nommément à son éditeur transformerait un contresens de traduction en citation fausse. Quand une zone ne rend pas assez de titres francophones, le lot anglais est servi plutôt qu'une section vide.

### Sentiment et résumés
Ni l'un ni l'autre n'est rédigé d'avance. Le résumé est composé à partir des valeurs du jour, et le sentiment découle de règles explicites : position de l'inflation dans la fourchette cible de la banque centrale concernée, sens de la variation de l'emploi et du chômage, niveau de croissance. Un paragraphe figé reste plausible longtemps après être devenu faux ; un paragraphe calculé ne peut pas contredire le tableau qu'il accompagne.

### Module Interconnexions
Les liens géoéconomiques sont identifiés à partir de l'analyse des canaux de transmission : commerce bilatéral, prix des matières premières, flux de capitaux, politique monétaire. Chaque interconnexion est documentée avec son mécanisme causal et son niveau d'impact.

## Stack technique

- **HTML / CSS / JS** — Fichier unique, aucun build nécessaire
- **Chart.js** (CDN) — Graphiques sparkline
- **Google Fonts** — DM Serif Display + DM Sans
- **Design** — Thème sombre inspiré du Financial Times, palette de couleurs par région
- **Python** (`requests`, `feedparser`) — Pipeline de collecte, exécuté par GitHub Actions
- **Aucun modèle de langage à l'exécution** — le filtre, les résumés et le sentiment sont déterministes, donc reproductibles et sans coût par exécution

### Structure

```
index.html                       dashboard complet (HTML + CSS + JS)
methodologie.html                page publique : sources, filtre, seuils
data/indicators.json             données consommées par la page
data/chronologie.json            chronologie des chocs, écrite à la main
data/analyse_provinciale.json    matrice d'impact provincial, écrite à la main
data/rejets.json                 titres écartés au dernier passage
scripts/update_data.py           collecte, calcul des résumés, contrôle de fraîcheur
scripts/news_filter.py           filtre de pertinence géoéconomique
scripts/test_news_filter.py      non-régression du filtre sur des cas réels
scripts/rapport_rejets.py        rapport hebdomadaire des titres écartés
scripts/corps_issue.py           corps de l'issue « indicateurs à rafraîchir »
MISE_A_JOUR_MANUELLE.md          ce qui reste sans source automatisable
.github/workflows/               mise à jour planifiée, rapport hebdomadaire, Pages
```

Le contenu éditorial vit dans ses propres fichiers : une mise à jour automatique ne peut donc pas écraser une analyse écrite à la main, et la frontière entre ce qui est calculé et ce qui est jugé reste lisible.

## Déploiement

Le dashboard est déployable sur GitHub Pages :

```bash
git clone https://github.com/ulrich-e-r-djidonou/geoecon-pulse.git
cd geoecon-pulse
# Ouvrir index.html dans un navigateur, ou :
npx serve .
```

## Auteur

**Ulrich Djidonou** — Économiste spécialisé en inférence causale et machine learning.

- [LinkedIn](https://www.linkedin.com/in/ulrich-djidonou/)
- [GitHub](https://github.com/ulrich-e-r-djidonou)

## Licence

MIT License — voir [LICENSE](LICENSE) pour les détails.

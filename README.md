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
- **Bilingue FR/EN** — Toggle instantané entre français et anglais
- **Responsive** — Optimisé pour desktop et mobile
- **Zéro dépendance de build** — Un seul fichier HTML, déployable en ouvrant le fichier

## Données et sources

Les données sont stockées dans `data/indicators.json` et rafraîchies automatiquement trois fois par jour par GitHub Actions.

| Indicateur | Régions | Source lue automatiquement |
|---|---|---|
| Taux directeur | Canada, États-Unis | Banque du Canada (API Valet), Fed de New York |
| Inflation IPC | Canada, États-Unis | Banque du Canada (API Valet), Bureau of Labor Statistics |
| Taux de chômage, variation de l'emploi | Canada, États-Unis | Statistique Canada (Web Data Service), BLS |
| Taux de change | Canada, Chine, Inde | Frankfurter / Banque centrale européenne |
| Indices boursiers et sparklines | toutes | Yahoo Finance, Frankfurter, Valet |

Cinq champs n'ont pas de source publique ouverte en fréquence mensuelle et restent saisis à la main : inflation et croissance de la Chine, inflation et taux directeur de l'Inde, agrégats mondiaux du FMI. Le pipeline surveille leur âge et fait échouer le workflow au-delà de 100 jours, ce qui déclenche une alerte par courriel. La procédure est détaillée dans [MISE_A_JOUR_MANUELLE.md](MISE_A_JOUR_MANUELLE.md).

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

`scripts/test_news_filter.py` rejoue soixante titres réellement parus sur le site, dont ceux qui n'avaient rien à y faire. Le workflow refuse de publier si ce test échoue.

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
index.html                     dashboard complet (HTML + CSS + JS)
data/indicators.json           données consommées par la page
scripts/update_data.py         collecte, calcul des résumés, contrôle de fraîcheur
scripts/news_filter.py         filtre de pertinence géoéconomique
scripts/test_news_filter.py    non-régression du filtre sur des cas réels
MISE_A_JOUR_MANUELLE.md        les cinq champs sans source automatisable
.github/workflows/             mise à jour planifiée et déploiement Pages
```

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

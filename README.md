# GeoEcon Pulse

**Dashboard interactif de veille géoéconomique mondiale** couvrant cinq zones stratégiques : Canada, États-Unis, Chine, Inde et Reste du monde. Conçu pour offrir une lecture rapide et rigoureuse des dynamiques macroéconomiques et géopolitiques en cours.

*Interactive global geoeconomic intelligence dashboard covering five strategic zones: Canada, United States, China, India and the World.*

![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-8B5CF6?style=flat-square)
![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Static Site](https://img.shields.io/badge/Stack-HTML%20%2F%20CSS%20%2F%20JS-orange?style=flat-square)

---

## Fonctionnalités

- **5 tableaux de bord régionaux** — Indicateurs macroéconomiques clés (PIB, inflation, taux directeur, taux de change, indice boursier) avec tendances
- **Indicateur de sentiment** — Évaluation synthétique de la conjoncture par région (positif / neutre / négatif)
- **Actualités sourcées** — 5 à 8 headlines récentes par région avec liens vers les sources originales, badges thématiques et indicateurs d'impact
- **Résumés hebdomadaires** — Synthèse analytique de 3-4 phrases par région
- **Mini-graphiques de tendance** — Sparklines sur 12 mois pour un indicateur clé par région
- **Module Interconnexions** — Visualisation en réseau des liens économiques entre régions + chronologie des événements clés
- **Filtres thématiques** — Commerce, Politique monétaire, Énergie, Tech, Géopolitique
- **Bilingue FR/EN** — Toggle instantané entre français et anglais
- **Responsive** — Optimisé pour desktop et mobile
- **Zéro dépendance de build** — Un seul fichier HTML, déployable en ouvrant le fichier

## Données et sources

Toutes les données sont **réelles et vérifiables** (mars 2026). Sources principales :

| Région | Sources |
|--------|---------|
| Canada | Banque du Canada, Statistique Canada, Bloomberg, Globe and Mail |
| États-Unis | Federal Reserve, BLS, CNBC, Yale Budget Lab |
| Chine | NBS, CNBC, SCMP, Goldman Sachs, Xinhua |
| Inde | RBI, Fitch Ratings, Business Standard, Bloomberg |
| Monde | FMI, WEF, Euronews, Al Jazeera, Chatham House |

Les données sont stockées dans `data/indicators.json` et peuvent être mises à jour manuellement.

## Méthodologie

### Sélection des indicateurs
Les 5 indicateurs macroéconomiques (PIB, inflation, taux directeur, taux de change, indice boursier) ont été retenus pour leur capacité à offrir une lecture rapide de la conjoncture économique d'une région. Ils couvrent les dimensions réelle, monétaire et financière.

### Sélection des actualités
Les headlines sont sélectionnées selon trois critères :
1. **Pertinence macroéconomique** — impact sur la croissance, l'inflation, la politique monétaire ou le commerce
2. **Récence** — événements des 2 dernières semaines
3. **Fiabilité des sources** — médias de référence, institutions officielles, think tanks reconnus

### Module Interconnexions
Les liens géoéconomiques sont identifiés à partir de l'analyse des canaux de transmission : commerce bilatéral, prix des matières premières, flux de capitaux, politique monétaire. Chaque interconnexion est documentée avec son mécanisme causal et son niveau d'impact.

## Stack technique

- **HTML / CSS / JS** — Fichier unique, aucun build nécessaire
- **Chart.js** (CDN) — Graphiques sparkline
- **Google Fonts** — DM Serif Display + DM Sans
- **Design** — Thème sombre inspiré du Financial Times, palette de couleurs par région

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

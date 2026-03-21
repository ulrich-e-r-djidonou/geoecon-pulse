# GeoEcon Pulse — Dashboard de veille géoéconomique mondiale

## Contexte du projet

**Auteur** : Économiste spécialisé en inférence causale et machine learning, basé au Québec.
**Objectif** : Créer un dashboard interactif de veille géoéconomique couvrant 5 zones géographiques (Canada, États-Unis, Chine, Inde, Reste du monde). Ce projet sert de pièce de portfolio pour des candidatures en économie, politiques publiques et modélisation.
**Public cible** : Recruteurs, professionnels en politiques publiques, économistes, réseau LinkedIn.
**Déploiement** : GitHub Pages (site statique) à `ulrich-e-r-djidonou.github.io/geoecon-pulse/`

---

## Architecture technique

### Stack
- **HTML / CSS / JavaScript** — fichier unique (comme le dashboard IA Québec)
- **Pas de React, pas de build, pas de npm** — doit fonctionner en ouvrant simplement le fichier `index.html`
- **API externe pour les news** : utiliser des flux RSS publics ou des APIs gratuites (ex: NewsAPI free tier, GNews API, ou RSS feeds de Reuters/BBC/Radio-Canada)
- **Pas d'API Claude intégrée** (coût) — les analyses sont pré-générées ou statiques avec possibilité de mise à jour manuelle
- **Charts** : Chart.js (CDN) ou D3.js (CDN)
- **Icônes** : Lucide Icons (CDN) ou Font Awesome
- **Fonts** : Google Fonts — utiliser des polices distinctives, PAS Inter/Roboto/Arial

### Structure des fichiers
```
geoecon-pulse/
├── index.html          # Fichier principal (tout-en-un : HTML + CSS + JS)
├── data/
│   └── indicators.json  # Données économiques par région (mise à jour manuelle)
├── assets/
│   └── og-image.png     # Image Open Graph pour partage LinkedIn
├── README.md            # Description du projet pour GitHub
├── CLAUDE.md            # Ce fichier
└── .gitignore
```

---

## Design et UX

### Direction esthétique
- **Tone** : Professionnel, éditorial, inspiré des dashboards du Financial Times ou The Economist
- **Thème** : Fond sombre (dark mode) avec accents de couleur par région
- **Typographie** : Police serif pour les titres (ex: Playfair Display, DM Serif Display), sans-serif pour le corps (ex: DM Sans, Source Sans Pro)
- **Palette de couleurs par région** :
  - 🇨🇦 Canada : Rouge (#E03C31)
  - 🇺🇸 États-Unis : Bleu (#3B5998)
  - 🇨🇳 Chine : Rouge-doré (#DE2910)
  - 🇮🇳 Inde : Orange safran (#FF9933)
  - 🌍 Monde : Vert (#2E8B57)
- **Background** : Gradient sombre (#0a0a0f → #1a1a2e) avec texture subtile (noise grain)
- **Cards** : Fond semi-transparent avec backdrop-filter: blur, bordures fines

### Layout
- **Header** : Titre "GeoEcon Pulse" + sous-titre + date de mise à jour + toggle FR/EN
- **Navigation** : 5 onglets régionaux (drapeaux + nom) + onglet "Interconnexions"
- **Filtres** : Par thème (Commerce, Politique monétaire, Énergie, Tech, Géopolitique)
- **Responsive** : Mobile-first, fonctionne bien sur téléphone et desktop

---

## Modules par région

Pour CHAQUE zone géographique (CA, US, CN, IN, Monde), afficher :

### 1. Indicateur de sentiment (haut de page)
- Visuel : Jauge ou badge coloré (Positif ▲ vert / Neutre ● jaune / Négatif ▼ rouge)
- Basé sur la tonalité générale des nouvelles de la semaine
- Valeur statique dans `indicators.json`, mise à jour manuellement

### 2. Indicateurs macroéconomiques clés
Afficher dans des cartes compactes :
| Indicateur | CA | US | CN | IN | Monde |
|---|---|---|---|---|---|
| Croissance PIB (%) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Inflation (%) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Taux directeur (%) | ✓ | ✓ | ✓ | ✓ | — |
| Taux de change vs USD | ✓ | — | ✓ | ✓ | — |
| Indice boursier principal | TSX | S&P500 | SSE | SENSEX | MSCI |

- Inclure une flèche ↑↓ et couleur pour la tendance
- Source : données hardcodées dans `indicators.json`

### 3. Headlines (5-8 par région)
- Titre cliquable (lien vers source originale)
- Badge de thème (Commerce, Énergie, etc.)
- Indicateur de temps ("2h", "1j", "3j")
- Indicateur d'impact (point rouge = fort, orange = moyen, gris = faible)

### 4. Résumé de la semaine (par région)
- 3-4 phrases synthétisant les tendances de la semaine
- Rédigé manuellement ou pré-généré
- Stocké dans `indicators.json`

### 5. Mini-graphique de tendance
- Sparkline ou area chart montrant l'évolution d'un indicateur clé sur 12 mois
- Ex: inflation pour CA, S&P500 pour US, Yuan/USD pour CN
- Données dans `indicators.json`

---

## Module spécial : Interconnexions

C'est **la valeur ajoutée d'économiste** — un onglet séparé qui montre :

### Carte des liens géoéconomiques
- Visualisation en réseau (nodes = régions, edges = relations économiques)
- Ou tableau croisé des impacts
- Exemples d'interconnexions à afficher :
  - "Tarifs US sur l'acier chinois → hausse des coûts manufacturiers CA"
  - "Hausse du taux Fed → pression sur la roupie indienne"
  - "Ralentissement chinois → baisse de la demande de matières premières CA"

### Timeline des événements clés
- Frise chronologique horizontale des 10 derniers événements majeurs
- Chaque événement tagué par région(s) affectée(s)

---

## Bilingue FR/EN

- Toggle en haut à droite
- Tous les textes statiques doivent avoir une version FR et EN
- Structure recommandée :
```javascript
const translations = {
  fr: {
    title: "GeoEcon Pulse",
    subtitle: "Veille géoéconomique mondiale",
    tabs: { CA: "Canada", US: "États-Unis", CN: "Chine", IN: "Inde", WORLD: "Monde", LINKS: "Interconnexions" },
    themes: ["Tous", "Commerce", "Politique monétaire", "Énergie", "Tech", "Géopolitique"],
    // ...
  },
  en: {
    title: "GeoEcon Pulse",
    subtitle: "Global Geoeconomic Intelligence",
    tabs: { CA: "Canada", US: "United States", CN: "China", IN: "India", WORLD: "World", LINKS: "Interconnections" },
    themes: ["All", "Trade", "Monetary Policy", "Energy", "Tech", "Geopolitics"],
    // ...
  }
};
```

---

## Données initiales à inclure

Pré-remplir avec des données réelles et récentes (mars 2026). Utiliser des sources fiables :

### Sources par région
- **Canada** : Banque du Canada, Statistique Canada, Radio-Canada, Globe and Mail
- **États-Unis** : Federal Reserve, BLS, Reuters, Bloomberg
- **Chine** : NBS China, SCMP, Reuters, Caixin
- **Inde** : RBI, Economic Times, Times of India, Reuters
- **Monde** : FMI, Banque mondiale, The Economist, BBC World

### Données à rechercher pour le lancement
- PIB, inflation, taux directeur actuels pour chaque région
- 5-8 headlines récentes par région
- Un résumé de 3-4 phrases par région
- 3-5 interconnexions économiques actuelles

---

## README.md pour GitHub

Générer un README professionnel incluant :
- Titre et description en 2 phrases
- Screenshot/GIF du dashboard
- Section "Fonctionnalités"
- Section "Données et sources"
- Section "Méthodologie" (expliquer la sélection des news et des indicateurs)
- Section "Auteur" avec lien LinkedIn
- Badge : "Built with Claude Code"
- Licence MIT

---

## Commandes suggérées pour Claude Code

```bash
# Étape 1 : Initialiser le projet
claude "Crée la structure du projet geoecon-pulse selon CLAUDE.md. Initialise git."

# Étape 2 : Construire le dashboard
claude "Construis index.html avec tout le CSS et JS intégrés. Suis les specs de design dans CLAUDE.md. Commence par la structure, puis ajoute chaque module."

# Étape 3 : Remplir les données
claude "Recherche les indicateurs économiques actuels (mars 2026) pour les 5 régions et remplis indicators.json. Ajoute 5-8 headlines récentes par région."

# Étape 4 : Interconnexions
claude "Crée le module Interconnexions avec une visualisation en réseau montrant les liens économiques entre les 5 régions. Utilise des exemples réels actuels."

# Étape 5 : Polish et déploiement
claude "Optimise le responsive, vérifie l'accessibilité, ajoute les animations d'entrée. Génère le README.md. Prépare pour GitHub Pages."

# Étape 6 : Git
claude "Fais un commit initial propre avec un message descriptif. Configure pour GitHub Pages."
```

---

## Critères de qualité

- [ ] Le dashboard s'ouvre en un seul fichier HTML (pas de build)
- [ ] Les 5 régions sont couvertes avec tous les modules
- [ ] Le module Interconnexions fonctionne
- [ ] Le toggle FR/EN fonctionne
- [ ] Le responsive fonctionne (mobile + desktop)
- [ ] Le design est professionnel et distinctif (PAS générique)
- [ ] Les données sont réelles et sourcées
- [ ] Le README est complet
- [ ] Git est initialisé avec des commits propres
- [ ] Déployable sur GitHub Pages

---

## Style et ton

- Professionnel mais accessible
- Données sourcées et vérifiables
- Design digne du Financial Times, pas d'un projet étudiant
- Les analyses dans les résumés doivent refléter une compréhension économique réelle

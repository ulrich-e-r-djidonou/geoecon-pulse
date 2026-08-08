# Mise à jour manuelle — ce qui reste à faire à la main

Tout ce qui peut être lu à une source publique sans clé d'API l'est
automatiquement, trois fois par jour. Ce document couvre le reste.

Il n'y a plus de série mensuelle à saisir. Ne restent que des **prévisions
annuelles**, révisées une ou deux fois l'an par leurs émetteurs, et des blocs
d'**analyse** qui relèvent du jugement plutôt que de la donnée.

Quand un indicateur daté dépasse 100 jours d'âge, qu'un écart suspect
apparaît entre deux sources indépendantes, ou qu'un flux RSS ne répond plus
depuis six passages, le workflow **ouvre une issue** intitulée
« Anomalies à vérifier » sur le dépôt plutôt que d'échouer : une croix rouge
permanente dans l'onglet Actions d'un dépôt public dessert le projet alors
que rien n'est cassé. L'issue est réécrite à chaque passage et se referme
d'elle-même une fois les trois familles d'anomalies revenues à zéro.

**Rythme conseillé : une passe par trimestre** pour les prévisions, et une
revue de l'analyse quand un choc majeur change la donne.

---

## Ce qui est automatique

| Indicateur | Régions | Source | Fréquence réelle |
|---|---|---|---|
| Taux de chômage | CA, US | Statistique Canada (WDS), BLS | mensuelle |
| Variation de l'emploi | CA, US | Statistique Canada (WDS), BLS | mensuelle |
| Inflation IPC | CA | Banque du Canada (Valet) | mensuelle |
| Inflation IPC | US | BLS, OCDE en repli | mensuelle |
| Inflation IPC | CN, IN | OCDE (entrepôt SDMX) | mensuelle |
| Taux directeur | CA, US | Banque du Canada (Valet), Fed de New York | à chaque décision |
| Taux directeur | CN, IN | Banque des règlements internationaux (WS_CBPOL) | quotidienne |
| Taux de change | CA, CN, IN | Frankfurter / BCE | quotidienne |
| Indices boursiers | toutes | Yahoo Finance | quotidienne |
| Sparklines | toutes | Valet, OCDE, Yahoo | quotidienne |
| Actualités FR et EN | toutes | flux d'éditeurs + Google News filtré | 3 fois par jour |
| Résumés et sentiment | toutes | calculés depuis les indicateurs ci-dessus | 3 fois par jour |
| Cours du Brent, du huard et de la roupie cités dans l'analyse provinciale et les interconnexions | CA, IN | substitués à chaque passage | 3 fois par jour |
| Contrôle de cohérence (seconde source ou borne de plausibilité) | toutes | OCDE, BRI, Yahoo Finance | 3 fois par jour |
| Santé des flux RSS (échecs consécutifs) | toutes | interne au pipeline | 3 fois par jour |

L'inflation et les taux directeurs de la Chine et de l'Inde étaient saisis à
la main jusqu'au 8 août 2026. Ils dérivaient : l'IPC indien affiché datait de
janvier et annonçait 2,7 % quand la série de l'OCDE donnait 4,76 % pour juin.

---

## Ce qui reste manuel

Modifier `data/indicators.json`, puis committer. Mettre à jour **la valeur et
la période** ensemble : c'est la période affichée qui rend le chiffre honnête.

### Prévisions de croissance — `regions.*.indicators.gdp`

Quatre émetteurs différents, ce qui est assumé mais limite la comparabilité
entre zones. La carte affiche la source pour cette raison.

| Zone | Source | Dernière relecture | Libellé de période | Rythme |
|---|---|---|---|---|
| CA | Banque du Canada, *Rapport sur la politique monétaire* | 15 juillet 2026 (0,7 %) | `2026F` | trimestriel |
| US | Federal Reserve, *Summary of Economic Projections* | 17 juin 2026 (2,2 %) | `2026F` | trimestriel |
| CN | Cible annoncée à l'Assemblée nationale populaire | 5 mars 2026 (4,5-5 %) | `2026 cible` | annuel (mars) |
| IN | Fitch Ratings | — | `FY26F` | révisions ponctuelles |

- Banque du Canada : <https://www.bankofcanada.ca/publications/mpr/>
- Federal Reserve : <https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm>

### Agrégats mondiaux — `regions.WORLD.indicators.gdp` et `.inflation`

Source : FMI, *World Economic Outlook*, deux fois par an (avril et octobre)
avec des mises à jour en janvier et juillet.
<https://www.imf.org/en/Publications/WEO>

Ces chiffres ne sont pas automatisables : l'API DataMapper du FMI est bloquée
par son réseau de diffusion, et son entrepôt SDMX ne publie que le millésime
d'octobre 2025, antérieur à l'édition d'avril 2026. Les relever dans le
tableau 1 du communiqué.

Dernière relecture : mise à jour de juillet 2026 (3,0 % de croissance
mondiale, 4,7 % d'inflation), <https://www.imf.org/en/publications/weo/issues/2026/07/08/world-economic-outlook-update-july-2026>.
La page du FMI bloque la récupération automatique (même 403 que le
DataMapper) : ces deux chiffres ont été relevés par recherche, à recouper
au prochain passage si une lecture directe de la page redevient possible.

Garder le libellé `2026F` tant qu'il s'agit d'une prévision : le contrôle de
fraîcheur ignore les libellés de prévision, puisqu'ils n'ont pas d'âge à
mesurer.

---

## Contenu d'analyse

Ces blocs relèvent du jugement. Ils vivent dans leurs propres fichiers pour
qu'une mise à jour automatique ne puisse pas les écraser.

### `data/chronologie.json`

La chronologie des chocs. Chaque événement porte un champ `source` avec l'URL
consultée : **ne rien ajouter qui ne soit pas daté et attribuable**. Le champ
`source` n'est pas publié sur le site, il sert à rendre chaque ligne
vérifiable dans le dépôt.

### `data/analyse_provinciale.json`

La matrice d'impact provincial et son texte. Le corps de l'analyse est
structurel (parts de PIB, parts d'exportation) et ne bouge pas souvent. Les
chiffres conjoncturels sont des marqueurs `{{brent}}`, `{{brentEn}}`,
`{{cad}}` et `{{cadEn}}`, substitués à chaque passage par les valeurs du jour.

**Ne pas écrire de cours ni de taux en dur dans ce fichier.** Une version
antérieure annonçait « Brent à 90 $ » et « 1,38 CAD/USD » plusieurs mois après
que ces deux chiffres soient devenus faux. Si un nouveau chiffre vivant doit
apparaître dans le texte, ajouter un marqueur et l'alimenter dans
`poser_contenu_editorial()`.

### `data/interconnexions.json`

Les canaux de transmission entre régions, recopiés dans
`regions.interconnections` de `data/indicators.json` à chaque passage. Chaque
lien porte un champ `source` (non publié, sert à le vérifier dans le dépôt) et
peut citer les mêmes marqueurs `{{brent}}`/`{{cad}}`/`{{inr}}` que la matrice
provinciale. À revoir quand un choc majeur change la structure des liens, pas
à date fixe : une version antérieure décrivait encore le détroit d'Ormuz comme
fermé sans interruption, plusieurs mois après sa réouverture puis sa
refermeture.

---

## Vérifier avant de committer

```bash
python scripts/test_news_filter.py     # le filtre ne laisse pas repasser de hors-sujet
python scripts/update_data.py          # recharge tout et recalcule les résumés
python scripts/rapport_rejets.py       # ce que le filtre a écarté, et pourquoi
```

Un code de sortie 2 signifie « données publiées, mais quelque chose demande
une vérification humaine » (champ manuel périmé, écart suspect entre deux
sources, ou flux RSS en panne : voir `data/coherence.json` et
`data/sante_flux.json`). Un code 1 signifie que le script a réellement échoué.

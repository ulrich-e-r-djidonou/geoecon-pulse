# Mise à jour manuelle — ce qui reste à faire à la main

Tout ce qui peut être lu à une source publique sans clé d'API l'est
automatiquement, trois fois par jour. Ce document couvre le reste : cinq
champs pour lesquels aucune source ouverte ne publie la donnée en fréquence
mensuelle dans un format exploitable.

Le workflow GitHub Actions **échoue volontairement** quand l'un de ces champs
dépasse 100 jours d'âge. L'échec déclenche un courriel de GitHub : c'est le
rappel. Les données fraîches sont publiées avant cet échec, donc le site n'est
jamais bloqué par une alerte.

**Rythme conseillé : une passe toutes les deux semaines**, le temps de faire
le tour est d'environ dix minutes.

---

## Ce qui est automatique

| Indicateur | Régions | Source | Fréquence réelle |
|---|---|---|---|
| Taux directeur | CA, US | Banque du Canada (Valet), Fed de New York | à chaque décision |
| Inflation IPC | CA, US | Banque du Canada (Valet), BLS | mensuelle |
| Taux de chômage | CA, US | Statistique Canada (WDS), BLS | mensuelle |
| Variation de l'emploi | CA, US | Statistique Canada (WDS), BLS | mensuelle |
| Taux de change | CA, CN, IN | Frankfurter / BCE | quotidienne |
| Indices boursiers | toutes | Yahoo Finance | quotidienne |
| Sparklines | toutes | Valet, Frankfurter, Yahoo | quotidienne |
| Actualités | toutes | flux d'éditeurs + Google News filtré | 3 fois par jour |
| Résumés et sentiment | toutes | calculés depuis les indicateurs ci-dessus | 3 fois par jour |

---

## Ce qui reste manuel

Modifier `data/indicators.json`, puis committer. Mettre à jour **la valeur et
la période** ensemble : c'est la période affichée qui rend le chiffre honnête.

### 1. Inflation Chine — `regions.CN.indicators.inflation`

Source : Bureau national des statistiques de Chine, communiqué mensuel sur
l'indice des prix à la consommation.
<https://www.stats.gov.cn/english/PressRelease/>

Relever la variation sur douze mois de l'IPC national. Période au format
`Juill. 2026`.

### 2. Croissance Chine — `regions.CN.indicators.gdp`

Cible annuelle annoncée à la session de l'Assemblée nationale populaire (mars),
ou dernier chiffre trimestriel publié par le NBS. Garder le libellé
`2026 cible` pour une cible, `T2 2026` pour un trimestre réalisé.

### 3. Inflation Inde — `regions.IN.indicators.inflation`

Source : Ministry of Statistics and Programme Implementation, communiqué
mensuel sur l'IPC combiné.
<https://www.mospi.gov.in/cpi>

### 4. Taux directeur Inde — `regions.IN.indicators.rate`

Source : Reserve Bank of India, taux repo à l'issue de chaque réunion de
politique monétaire (environ toutes les six semaines).
<https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx>

### 5. Agrégats mondiaux — `regions.WORLD.indicators.gdp` et `.inflation`

Source : FMI, *World Economic Outlook*, deux fois par an (avril et octobre)
avec des mises à jour en janvier et juillet.
<https://www.imf.org/en/Publications/WEO>

Garder le libellé `2026F` tant qu'il s'agit d'une prévision : le contrôle de
fraîcheur ignore les libellés de prévision, puisqu'ils n'ont pas d'âge à
mesurer.

---

## Autres champs rédigés à la main

Ces blocs ne sont pas couverts par le contrôle de fraîcheur parce qu'ils
relèvent de l'analyse, pas de la donnée. Les revoir à la même occasion.

- `interconnections` — les canaux de transmission entre régions
- `timeline` — la chronologie des événements marquants
- `regions.CA.provincialAnalysis` — la matrice d'impact provincial

---

## Vérifier avant de committer

```bash
python scripts/test_news_filter.py     # le filtre ne laisse pas repasser de hors-sujet
python scripts/update_data.py          # recharge tout et recalcule les résumés
```

Un code de sortie 2 signifie « données publiées, mais des champs manuels sont
périmés ». Un code 1 signifie que le script a réellement échoué.

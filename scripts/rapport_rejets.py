#!/usr/bin/env python3
"""Rapport hebdomadaire des titres ecartes par le filtre d'actualites.

Pourquoi ce rapport existe. Le filtre coupe entre soixante et cent titres
par region et par passage pour en retenir huit. Tant que personne ne regarde
ce qu'il coupe, ses faux negatifs sont invisibles : une regle trop large
peut ecarter une depeche importante pendant des mois sans qu'aucun signal ne
le revele. Un filtre muet finit par etre un filtre qu'on ne peut plus
defendre, ce qui est exactement le contraire du but recherche.

Le rapport agrege les instantanes data/rejets.json des sept derniers jours,
releves dans l'historique Git, et classe les motifs par frequence. Il met en
avant les rejets suspects : ceux dont le motif est generique alors que le
titre porte un vocabulaire economique.

Ecrit sur stdout, en UTF-8 quel que soit l'encodage de la console.
"""

import io
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from news_filter import MOTIF_FORT, MOTIF_MOYEN, normaliser  # noqa: E402

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

RACINE = Path(__file__).resolve().parent.parent
REJETS = RACINE / "data" / "rejets.json"
JOURS = 7

# Un rejet pour « source hors liste » est un choix editorial assume, pas une
# erreur de classement : on le compte sans le signaler.
MOTIFS_ATTENDUS = ("source hors liste", "titre trop court")


def instantanes_recents():
    """Les versions de data/rejets.json des sept derniers jours.

    On passe par l'historique Git plutot que par un fichier cumulatif : le
    depot garde deja chaque etat, et un journal qui grossit indefiniment
    finirait par alourdir chaque clone.
    """
    depuis = (datetime.now() - timedelta(days=JOURS)).strftime("%Y-%m-%d")
    try:
        sortie = subprocess.run(
            ["git", "log", f"--since={depuis}", "--format=%H",
             "--", str(REJETS.relative_to(RACINE))],
            cwd=RACINE, capture_output=True, text=True, timeout=60, check=True)
    except Exception as e:
        print(f"Historique Git illisible ({e}), lecture du seul fichier "
              f"courant.\n")
        return [charger_courant()]

    versions = []
    for commit in [c for c in sortie.stdout.split() if c]:
        try:
            brut = subprocess.run(
                ["git", "show", f"{commit}:data/rejets.json"],
                cwd=RACINE, capture_output=True, timeout=60, check=True)
            versions.append(json.loads(brut.stdout.decode("utf-8")))
        except Exception:
            continue

    courant = charger_courant()
    if courant and (not versions or courant != versions[0]):
        versions.insert(0, courant)
    return versions


def charger_courant():
    try:
        with open(REJETS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def suspect(titre, motif):
    """Vrai si le titre porte un vocabulaire economique malgre son rejet.

    Un titre ecarte pour « aucun signal geoeconomique suffisant » alors qu'il
    contient un terme fort est la signature d'un veto trop large : c'est
    exactement le faux negatif qu'on cherche.
    """
    if any(motif.startswith(m) for m in MOTIFS_ATTENDUS):
        return False
    t = normaliser(titre)
    return bool(MOTIF_FORT.search(t)) or len(set(MOTIF_MOYEN.findall(t))) >= 2


def principal():
    versions = [v for v in instantanes_recents() if v]
    if not versions:
        print("Aucun instantane de rejets disponible.")
        return 0

    vus, rejets = set(), []
    for version in versions:
        for r in version.get("rejets", []):
            cle = (r.get("region"), r.get("titre"))
            if cle in vus:
                continue
            vus.add(cle)
            rejets.append(r)

    dates = sorted({v.get("date", "?") for v in versions})
    print(f"# Titres écartés — {dates[0]} au {dates[-1]}")
    print()
    print(f"{len(rejets)} titres distincts écartés sur {len(versions)} "
          f"passage(s) du pipeline.")
    print()

    par_motif = Counter()
    for r in rejets:
        motif = r["motif"].split(" :")[0]
        par_motif[motif] += 1

    print("## Motifs de rejet")
    print()
    print("| Motif | Titres |")
    print("|---|---:|")
    for motif, n in par_motif.most_common(12):
        print(f"| {motif} | {n} |")
    print()

    par_langue = Counter(r.get("langue", "?") for r in rejets)
    par_region = defaultdict(Counter)
    for r in rejets:
        par_region[r.get("region", "?")][r.get("langue", "?")] += 1
    print("## Répartition")
    print()
    print("| Zone | Anglais | Français |")
    print("|---|---:|---:|")
    for region in ("CA", "US", "CN", "IN", "WORLD"):
        c = par_region.get(region, Counter())
        print(f"| {region} | {c.get('en', 0)} | {c.get('fr', 0)} |")
    print(f"| **Total** | **{par_langue.get('en', 0)}** | "
          f"**{par_langue.get('fr', 0)}** |")
    print()

    suspects = [r for r in rejets if suspect(r["titre"], r["motif"])]
    print("## À relire")
    print()
    if not suspects:
        print("Aucun rejet ne porte de vocabulaire économique inattendu.")
    else:
        print(f"{len(suspects)} titre(s) écarté(s) alors qu'ils portent un "
              f"vocabulaire économique. Ce sont les faux négatifs candidats : "
              f"si l'un mérite d'être retenu, l'ajouter à "
              f"`scripts/test_news_filter.py` plutôt que d'élargir les listes "
              f"à l'aveugle.")
        print()
        for r in suspects[:25]:
            print(f"- `{r.get('region')}/{r.get('langue')}` "
                  f"{r['titre'][:110]}")
            print(f"  motif : {r['motif']}")
        if len(suspects) > 25:
            print(f"- … et {len(suspects) - 25} autres.")
    print()
    print("---")
    print()
    print("Rapport produit par `scripts/rapport_rejets.py`. Le filtre lui-même "
          "est documenté dans [METHODOLOGIE.md](../blob/master/METHODOLOGIE.md).")
    return 0


if __name__ == "__main__":
    sys.exit(principal())

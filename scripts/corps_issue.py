#!/usr/bin/env python3
"""Compose le corps de l'issue qui rappelle ce qui demande une intervention.

Appelé par le workflow quand `update_data.py` sort en 2, ce qui couvre trois
familles de problèmes distinctes : un indicateur manuel périmé, un écart
suspect entre deux sources, un flux qui ne répond plus. Écrit sur stdout, en
UTF-8 quel que soit l'encodage de la console.
"""

import io
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "indicators.json"
COHERENCE_FILE = BASE_DIR / "data" / "coherence.json"
SANTE_FLUX_FILE = BASE_DIR / "data" / "sante_flux.json"
SEUIL_FLUX_EN_PANNE = 6

with open(DATA_FILE, encoding="utf-8") as f:
    donnees = json.load(f)

perimes = donnees.get("staleIndicators", [])
mise_a_jour = donnees.get("lastUpdated", "")

try:
    with open(COHERENCE_FILE, encoding="utf-8") as f:
        incoherences = [c for c in json.load(f).get("controles", []) if c.get("suspect")]
except Exception:
    incoherences = []

try:
    with open(SANTE_FLUX_FILE, encoding="utf-8") as f:
        sante = json.load(f)
    en_panne = [{"nom": e.get("nom") or url, **e} for url, e in sante.items()
               if e.get("echecsConsecutifs", 0) >= SEUIL_FLUX_EN_PANNE]
except Exception:
    en_panne = []

lignes = [f"Dernière exécution du pipeline : {mise_a_jour}.", ""]

lignes.append("### Indicateurs manuels périmés")
lignes.append("")
if perimes:
    lignes.append("Ces indicateurs n'ont pas de source publique automatisable et ont "
                  "dépassé le seuil de 100 jours :")
    lignes.append("")
    lignes += [f"- `{p}`" for p in perimes]
    lignes.append("")
    lignes.append("La marche à suivre, source par source, est dans "
                  "[MISE_A_JOUR_MANUELLE.md](../blob/master/MISE_A_JOUR_MANUELLE.md).")
else:
    lignes.append("Aucun.")
lignes.append("")

lignes.append("### Écarts suspects entre deux sources")
lignes.append("")
if incoherences:
    lignes.append("Le contrôle de cohérence compare chaque indicateur qui a une "
                  "seconde source publique indépendante. Ces écarts dépassent le seuil :")
    lignes.append("")
    for c in incoherences:
        if c["type"] == "source_double":
            lignes.append(f"- `{c['indicateur']}` : {c['sourceA']} = {c['valeurA']}, "
                          f"{c['sourceB']} = {c['valeurB']} (écart {c['ecart']})")
        else:
            lignes.append(f"- `{c['indicateur']}` : {c['sourceA']} = {c['valeurA']}, "
                          f"hors de la plage attendue {c['valeurB']}")
    lignes.append("")
    lignes.append("Un écart ne signifie pas forcément une erreur : les deux sources "
                  "peuvent viser une date de référence légèrement différente. Vérifier "
                  "la valeur avant de la corriger.")
else:
    lignes.append("Aucun.")
lignes.append("")

lignes.append("### Flux d'actualités en panne")
lignes.append("")
if en_panne:
    lignes.append(f"Ces flux n'ont pas répondu depuis {SEUIL_FLUX_EN_PANNE} passages "
                  "ou plus (environ deux jours) :")
    lignes.append("")
    for e in en_panne:
        lignes.append(f"- `{e['nom']}` : {e['echecsConsecutifs']} échecs consécutifs, "
                      f"dernier succès le {e.get('dernierSucces') or 'jamais'}")
    lignes.append("")
    lignes.append("Vérifier si l'URL a changé ou si le flux RSS a été fermé, et mettre "
                  "à jour `RSS_FEEDS`/`RSS_FEEDS_FR` dans `scripts/update_data.py` en "
                  "conséquence.")
else:
    lignes.append("Aucun.")
lignes.append("")

lignes.append("Cette issue est réécrite à chaque exécution et se referme automatiquement "
              "une fois les trois sections vides.")

sys.stdout.write("\n".join(lignes) + "\n")

#!/usr/bin/env python3
"""Compose le corps de l'issue qui rappelle les indicateurs à rafraîchir.

Appelé par le workflow quand `update_data.py` sort en 2. Écrit sur stdout,
en UTF-8 quel que soit l'encodage de la console.
"""

import io
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "indicators.json"

with open(DATA_FILE, encoding="utf-8") as f:
    donnees = json.load(f)

perimes = donnees.get("staleIndicators", [])
mise_a_jour = donnees.get("lastUpdated", "")

lignes = [
    "Ces indicateurs n'ont pas de source publique automatisable et ont "
    "dépassé le seuil de 100 jours :",
    "",
]
lignes += [f"- `{p}`" for p in perimes] or ["- (aucun)"]
lignes += [
    "",
    "La marche à suivre, source par source, est dans "
    "[MISE_A_JOUR_MANUELLE.md](../blob/master/MISE_A_JOUR_MANUELLE.md). "
    "Compter une dizaine de minutes.",
    "",
    f"Dernière exécution du pipeline : {mise_a_jour}.",
    "",
    "Cette issue est réécrite à chaque exécution. La refermer une fois les "
    "valeurs et leurs périodes corrigées.",
]

sys.stdout.write("\n".join(lignes) + "\n")

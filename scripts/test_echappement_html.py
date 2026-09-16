#!/usr/bin/env python3
"""
Non-regression de l'echappement HTML du tableau de bord.

Les manchettes, resumes et titres d'evenements viennent de flux RSS tiers,
dont news.google.com, ou le titre est ecrit par l'editeur qui publie. Avant
septembre 2026 ils entraient tels quels dans innerHTML : un titre contenant
<img src=x onerror=...> s'executait sur djidonou.com, meme origine que tout
le reste du site.

Le correctif fait passer chaque donnee par esc() ou safeUrl(). Ce test
verifie que personne n'ajoute une interpolation qui contourne ces deux
fonctions. Il lit index.html sans navigateur ni dependance.

    python scripts/test_echappement_html.py
"""

import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

RACINE = Path(__file__).resolve().parent.parent
INDEX = RACINE / "index.html"

# Fonctions qui composent du HTML a partir de indicators.json.
FONCTIONS = [
    "buildHeadlines",
    "buildAllPanels",
    "buildInterconnections",
    "buildTimeline",
    "buildIndicatorCards",
    "drawNetwork",
]

# Expressions dont la valeur ne vient pas du JSON : libelles d'interface
# traduits en dur, variables locales calculees, coordonnees numeriques,
# fragments de HTML deja echappes par la fonction qui les a construits.
# Toute nouveaute doit etre justifiee ici plutot qu'ajoutee sans reflexion.
SURES = {
    # libelles d'interface, definis dans l'objet T du fichier
    "lang", "theme", "region", "key", "regionKey",
    # couleurs et geometrie, issues de constantes locales
    "color", "opacity", "width", "x1", "x2", "y1", "y2",
    "node.x", "node.y", "node.y + 5", "node.y + 50",
    "node.color", "from.color",
    # classes CSS derivees d'une table locale
    "impactClass", "badgeClass",
    # fragments deja composes par une fonction de cette liste
    "headlines", "indCards", "tags", "provTags",
    "matrixRows", "scoreRow", "thCells",
    # signe du delta, calcule sur un nombre deja valide
    "ind.change > 0 ? '+' : ''",
}

MOTIF_SUR = re.compile(r"^(esc|safeUrl)\(")
MOTIF_T = re.compile(r"^T\[lang\]\.")
MOTIF_TERNAIRE_VIDE = re.compile(r"\?\s*[^:]*:\s*''\s*$")


def segment(source: str, nom: str) -> str:
    """Retourne le corps approximatif d'une fonction, accolades comprises."""
    debut = source.find("function " + nom)
    if debut < 0:
        raise SystemExit(f"ECHEC : fonction {nom} introuvable dans index.html")
    i = source.find("{", debut)
    profondeur = 0
    for j in range(i, len(source)):
        if source[j] == "{":
            profondeur += 1
        elif source[j] == "}":
            profondeur -= 1
            if profondeur == 0:
                return source[debut:j + 1]
    raise SystemExit(f"ECHEC : accolades desequilibrees dans {nom}")


def main() -> int:
    source = INDEX.read_text(encoding="utf-8")

    if "function esc(" not in source or "function safeUrl(" not in source:
        print("ECHEC : esc() ou safeUrl() a disparu de index.html")
        return 1

    # safeUrl ne doit laisser passer que http(s).
    if "^https?:" not in source:
        print("ECHEC : safeUrl n'impose plus le schema http(s)")
        return 1

    fautes = []
    total = 0
    for nom in FONCTIONS:
        corps = segment(source, nom)
        for expr in sorted(set(re.findall(r"\$\{([^}]*)\}", corps))):
            total += 1
            e = expr.strip()
            if MOTIF_SUR.match(e) or MOTIF_T.match(e) or e in SURES:
                continue
            if MOTIF_TERNAIRE_VIDE.search(e) and ("esc(" in e or "build" in e):
                continue
            fautes.append((nom, e))

    print(f"{total} interpolations examinees dans {len(FONCTIONS)} fonctions.")

    if fautes:
        print(f"\nECHEC : {len(fautes)} interpolation(s) sans esc() ni safeUrl().")
        print("Une donnee de indicators.json rendue sans echappement rouvre")
        print("l'injection HTML par les flux RSS. Enveloppez la valeur dans")
        print("esc(), ou dans safeUrl() s'il s'agit d'une URL. Si la valeur ne")
        print("vient vraiment pas du JSON, ajoutez-la a SURES en expliquant")
        print("d'ou elle vient.\n")
        for nom, e in fautes:
            print(f"  {nom} : ${{{e}}}")
        return 1

    print("Echappement complet : aucune donnee du JSON n'entre brute dans le DOM.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

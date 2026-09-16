#!/usr/bin/env python3
"""
Non-regression de l'echappement HTML du tableau de bord.

Les manchettes, resumes et titres d'evenements viennent de flux RSS tiers,
dont news.google.com, ou le titre est ecrit par l'editeur qui publie. Avant
septembre 2026 ils entraient tels quels dans innerHTML : un titre contenant
<img src=x onerror=...> s'executait sur djidonou.com, meme origine que tout
le reste du site.

Le correctif fait passer chaque donnee par esc() ou safeUrl(). Ce test
verifie que personne n'ajoute une valeur qui contourne ces deux fonctions.
Il lit index.html sans navigateur ni dependance.

Deux surfaces sont controlees, parce que le fichier compose son HTML de
deux manieres :
  - les gabarits, ou les donnees arrivent par des interpolations ${...} ;
  - buildProvincialAnalysis, qui concatene des chaines et n'a donc aucune
    interpolation a inspecter.

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

# Fonctions qui composent du HTML par gabarit.
FONCTIONS = [
    "buildHeadlines",
    "buildAllPanels",
    "buildInterconnections",
    "buildTimeline",
    "buildIndicatorCards",
    "drawNetwork",
]

# Fonctions qui composent du HTML par concatenation de chaines.
CONCATENATION = ["buildProvincialAnalysis"]

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
    # ternaires dont la branche non vide est deja traitee : l'une appelle une
    # fonction auditee par ce test, l'autre enveloppe sa valeur dans esc()
    "key === 'CA' && r.provincialAnalysis ? buildProvincialAnalysis(r.provincialAnalysis) : ''",
    "unit ? ' ' + esc(unit) : ''",
}

# Operandes surs des concatenations, avec leur provenance.
SURES_CONCAT = {
    # fragments deja composes plus haut dans la meme fonction
    "thCells", "matrixRows", "scoreRow", "cells", "provTags",
    "strengthsList", "weaknessesList", "groups",
    # libelles d'interface traduits en dur dans l'objet T
    "t.strengths_label", "t.weaknesses_label", "t.provincial_title",
    "t.provincial_subtitle", "t.matrix_title", "t.groups_title",
    "t.reading_note", "scoreLabel",
    # valeurs numeriques ou classes CSS calculees localement
    "score", "cls", "val", "(score > 0 ?",
}

MOTIF_SUR = re.compile(r"^(esc|safeUrl|encodeURIComponent|Number|String)\(")
MOTIF_T = re.compile(r"^T\[lang\]\.")

# Litteral de chaine simple, apostrophes echappees comprises.
LITTERAL = r"'(?:\\.|[^'\\])*'"

# Jetons de syntaxe qui subsistent apres retrait des litteraux et ne designent
# aucune valeur : ils ne peuvent pas porter de HTML.
MOTS_CLES_JS = {"join", "map", "function", "return", "var", "let", "const"}


def interpolations(segment):
    """Rend les expressions ${...} de premier niveau, accolades equilibrees.

    Une interpolation peut en contenir d'autres. Une expression reguliere en
    [^}]* s'arrete au premier } et tronque l'expression, ce qui fait echouer
    le test sur du code pourtant correct.
    """
    i = 0
    while True:
        i = segment.find("${", i)
        if i < 0:
            return
        profondeur = 0
        for j in range(i + 1, len(segment)):
            if segment[j] == "{":
                profondeur += 1
            elif segment[j] == "}":
                profondeur -= 1
                if profondeur == 0:
                    yield segment[i + 2:j]
                    i = j + 1
                    break
        else:
            return


def sure(expr):
    """Rend None si l'expression est sure, sinon la sous-expression fautive.

    Une expression composite est sure quand toutes ses interpolations internes
    le sont : le texte litteral autour d'elles est du HTML ecrit par l'auteur,
    pas une donnee du JSON.
    """
    e = expr.strip()
    if MOTIF_SUR.match(e) or MOTIF_T.match(e) or e in SURES:
        return None
    internes = list(interpolations(e))
    if internes:
        for interne in internes:
            faute = sure(interne)
            if faute is not None:
                return faute
        return None
    return e


def segment(source, nom):
    """Rend le corps d'une fonction, accolades comprises."""
    debut = source.find("function " + nom)
    if debut < 0:
        raise SystemExit("ECHEC : fonction {} introuvable dans index.html".format(nom))
    i = source.find("{", debut)
    profondeur = 0
    for j in range(i, len(source)):
        if source[j] == "{":
            profondeur += 1
        elif source[j] == "}":
            profondeur -= 1
            if profondeur == 0:
                return source[debut:j + 1]
    raise SystemExit("ECHEC : accolades desequilibrees dans {}".format(nom))


def operandes_concat(corps):
    """Rend les operandes non litteraux des lignes qui produisent du HTML.

    Le controle se fait ligne par ligne : cette fonction concatene une balise
    par ligne. Decouper le corps entier sur + melangerait du code sans rapport
    avec le HTML produit et ferait echouer le test sur du bruit.

    Une ligne est retenue quand un de ses litteraux contient un chevron
    ouvrant, donc du balisage. Les operandes sont ce qui reste une fois les
    litteraux remplaces par un marqueur.
    """
    marqueur = ""
    for ligne in corps.split("\n"):
        if ligne.strip().startswith("//"):
            continue
        if not any("<" in lit for lit in re.findall(LITTERAL, ligne)):
            continue
        sans = re.sub(LITTERAL, marqueur, ligne)
        for morceau in sans.split("+"):
            m = morceau.strip().rstrip(";,").strip()
            m = m.replace(marqueur, "").strip()
            if not m or m in ("(", ")", "{", "}", "return"):
                continue
            if m.startswith(("return", "var ", "}", "{", ".join")):
                continue
            yield m


def main():
    source = INDEX.read_text(encoding="utf-8")

    if "function esc(" not in source or "function safeUrl(" not in source:
        print("ECHEC : esc() ou safeUrl() a disparu de index.html")
        return 1

    if "^https?:" not in source:
        print("ECHEC : safeUrl n'impose plus le schema http(s)")
        return 1

    fautes = []

    total = 0
    for nom in FONCTIONS:
        corps = segment(source, nom)
        for expr in sorted(set(interpolations(corps))):
            total += 1
            faute = sure(expr)
            if faute is not None:
                fautes.append((nom, faute))

    nb_concat = 0
    for nom in CONCATENATION:
        corps = segment(source, nom)
        for op in sorted(set(operandes_concat(corps))):
            nb_concat += 1
            if MOTIF_SUR.match(op) or op in SURES_CONCAT:
                continue
            # Une fois les litteraux retires, il reste souvent de la ponctuation
            # de ternaire ou de fermeture. On juge sur les identifiants : si
            # tous sont connus comme surs, l'operande l'est.
            identifiants = [
                i for i in re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", op)
                if i not in MOTS_CLES_JS
            ]
            if identifiants and all(i in SURES_CONCAT for i in identifiants):
                continue
            if not identifiants:
                continue
            fautes.append((nom, op))

    print("{} interpolations et {} operandes de concatenation examines "
          "dans {} fonctions.".format(total, nb_concat,
                                      len(FONCTIONS) + len(CONCATENATION)))

    if fautes:
        print("\nECHEC : {} valeur(s) sans echappement.".format(len(fautes)))
        print("Une donnee de indicators.json rendue brute rouvre l'injection")
        print("HTML par les flux RSS. Enveloppez la valeur dans esc(), dans")
        print("safeUrl() s'il s'agit d'une URL, ou dans Number() si elle doit")
        print("etre numerique. Si la valeur ne vient vraiment pas du JSON,")
        print("ajoutez-la a SURES ou SURES_CONCAT en expliquant d'ou elle vient.\n")
        for nom, faute in fautes:
            print("  {} : {}".format(nom, faute))
        return 1

    print("Echappement complet : aucune donnee du JSON n'entre brute dans le DOM.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

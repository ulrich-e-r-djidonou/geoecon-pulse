#!/usr/bin/env python3
"""
Non-regression du filtre d'actualites.

Les cas REJETS sont des titres reellement affiches par le tableau de bord le
8 aout 2026. Les cas ACCEPTES sont des titres du meme lot qui devaient rester.
Un filtre qui echoue ici remet du hors-sujet en ligne.

    python scripts/test_news_filter.py
"""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from news_filter import evaluer, nettoyer_titre  # noqa: E402

# ------------------------------------------------------------
# Doivent etre REJETES
# ------------------------------------------------------------
REJETS = [
    # Les deux exemples signales explicitement.
    "L'homme arrêté sur un golf de Trump accusé de possession illégale d'arme à feu",
    "Félix Auger-Aliassime se retire de l'Omnium Banque Nationale",
    # Sport passe par « banque » ou par un nom propre.
    "Joao Fonseca brille face à Casper Ruud et passe en huitièmes de l'Omnium Banque Nationale",
    "Sai Sudharsan ruled out of Sri Lanka Test series",
    "Which stars need to shine this season: Real Madrid, Barcelona, Atletico?",
    "Is football AI-proof? Why tech investors wanted a slice of the game",
    # Faits divers et justice.
    "Thai PM vows to introduce stricter gun laws after eight killed in shooting",
    "Trump's ex-lawyer Todd Blanche narrowly confirmed as US attorney general",
    "Trump ally Blanche confirmed as US attorney general",
    "La justice bloque à nouveau la salle de bal de Trump, qui va s'adresser à la Cour suprême",
    # Politique interieure de procedure.
    "Hawaii primary tests Democrats' leftward shift",
    "Trump-backed voting bill stalls as Senate heads home",
    # Meteo et catastrophes sans angle economique.
    "Typhoon Dolphin causes flight chaos in China, with Shanghai set to enter danger zone",
    "Typhoon Dolphin hits Japan, heads towards China",
    "Un feu de forêt violent force de nouvelles évacuations en Colombie-Britannique",
    # Curiosites scientifiques.
    "What is a glueball? Chinese-led team finds rare particle made entirely of force",
    "China's lunar research station could be guarded by robot watchdogs, space scientists say",
    "Chinese scientists find some Yangtze flood controls may do more harm than good",
    # Rappels alimentaires et sante.
    "Cyclospora fears lead consumers to lose their appetite for salad",
    "Rappel de soufflés et grignotines de maïs cheddar à base de fromage",
    # Societe et divertissement.
    "A new youth agitation grips an Indian state after 'cockroach' protests",
    "Woman screams in fear as Ukraine war recruiters pounce on man",
    "India's youth are its biggest strength: Rahul",
    "Pierre-Luc Brillant défendra de nouveau les couleurs du PQ dans Chauveau",
    # Agregats et rubriques.
    "Ottawa's trade concessions with U.S., unemployment rate hits two-year low and the "
    "100 best cities for renters: Must-read business and investing stories",
    # Cas limite assume : une amende sur un geant du numerique est de la
    # regulation, mais « child safety » releve du fait de societe. Le filtre
    # tranche pour la stricte pertinence geoeconomique.
    "Meta fined $567m in largest child safety ruling against social media",
    # Divers hors sujet.
    "Savers Value Village thrift store launches new AI tool to price items",
    "My adult kids are big earners. Should I do a Roth conversion now?",
    "Taiwan's William Lai rehearses late-night emergency escape during military drill",
    # ------------------------------------------------------------
    # Flux francophones, ajoutes avec le mode FR du site. Ces titres sont
    # parus tels quels chez Radio-Canada, Les Affaires, Le Monde, RFI et
    # La Presse. Le meme bruit qu'en anglais, dans une autre langue : le
    # filtre doit le couper sans qu'on ait deux jeux de regles a maintenir.
    # ------------------------------------------------------------
    "Un feu de forêt violent force de nouvelles évacuations en Colombie-Britannique",
    "Un suspect armé arrêté à Bedford, le confinement est levé à Halifax",
    "L'Omnium Banque Nationale fonce contre vents et marées vers un record d'assistance",
    "Rappel de soufflés et grignotines de maïs cheddar à base de plantes de marque PC Biologique",
    "Le gouvernement du Canada accorde un soutien financier au Festival AfroMonde",
    "La Société Canadian Tire soutient les initiatives de secours liées aux feux de forêt au Canada",
    "Trottinettes électriques à Paris : casque et gilet réfléchissant sont désormais obligatoires",
    "Le business de la nostalgie: comment le passé est devenu un marché extrêmement rentable",
    "Michaël Boumendil, l'homme qui donne une voix aux marques",
    "Coût de la vie | Le prix du burrito fait débat au parti de Trump",
    "ÉTAMPES (91) - Conférence : L'Inde, future troisième grande puissance",
    "Les régulateurs de vol de Jazz ratifient la convention collective",
    "Sécheresse et canicules : les agriculteurs face à une catastrophe climatique inédite",
    "Les déboires du leader européen du vélo Accell entraînent Cycles Lapierre dans sa chute",
    # Cas limite assume, pendant francais de l'amende Meta ci-dessus : une
    # analyse de geographie economique reste un sujet de magazine tant qu'elle
    # ne porte ni chiffre ni decision. Ecarte au profit de la stricte
    # pertinence, comme le veut la regle du projet.
    "Chine : ces dix provinces qui concentrent la croissance de l'atelier du monde",
]

# ------------------------------------------------------------
# Doivent etre ACCEPTES
# ------------------------------------------------------------
ACCEPTES = [
    ("Canadian economy adds 75,100 jobs in July, U.S. sheds 23,000 positions", "monetary"),
    ("Trump imposes 15% tariff on key chip material to counter China", "trade"),
    ("Canada prepared to halt booze bans, meet other U.S. demands in exchange for tariff relief", "trade"),
    ("India's $40bn Russian lifeline faces tariff threat", "trade"),
    ("'US hurting itself; India insulated on new tariffs'", "trade"),
    ("US judge blocks Pentagon's 'Chinese military' label for WuXi AppTec", None),
    ("Surprise fall in US jobs last month as slow summer continues", None),
    ("Here are three key takeaways from the disappointing July jobs report", "monetary"),
    ("US announces $400m investment in Australian rare earth mine", "tech"),
    ("Trump administration to pay German firm $1.2bn to halt US wind projects", None),
    ("China faces new AI bottleneck as it runs out of Chinese-language data", "tech"),
    ("Iran targeted tanker, says UAE, as Tehran says Hormuz deal within reach", "energy"),
    ("China's New Export Engine: Supplying the Factories of the World", "trade"),
    ("Japan's top 3 banks boost foreign currency liquidity buffers", None),
    ("United Kingdom launches safeguard investigation on polyethylene imports", None),
    ("US pledges $1bn support to Colombia as Trump-backed president sworn in", None),
    ("Canada must avoid concessions in U.S. trade talks, dairy farmers warn", "trade"),
    ("U.S. Senate passes Russia sanctions bill that seeks 100% tariffs", None),
    ("Posthaste: China helped save the world from an even worse oil shock", "energy"),
    ("Delhivery Q1 Results: Net profit tumbles 65% YoY to Rs 32 crore", None),
    # Faux negatifs releves sur la premiere execution reelle du pipeline.
    ("Private companies added just 44,000 workers in July, below expectations", "monetary"),
    ("What a divided Fed means for investors", "monetary"),
    ("Kevin Warsh has homed in on three key phrases. How Fed watchers read them", "monetary"),
    ("Brazil initiates dispute regarding additional duties imposed by the United States", "trade"),
    ("Publication: Summary of Deliberations", "monetary"),
    ("IP protection, FTA utilisation, contractual safeguards in focus", None),
    ("Why is transit in goods free but trade is not?", "trade"),
    ("Lithuania gives EUR 30,000 to help developing economies join trade talks", None),
    ("Consumer prices rose 3.5% annually in June, less than expected", "monetary"),
    ("Wholesale prices unexpectedly declined 0.3% in June on big drop in energy", None),
    # ------------------------------------------------------------
    # Flux francophones. Ces titres doivent passer avec le meme jeu de regles
    # que l'anglais, sans liste de mots-cles parallele a entretenir.
    # ------------------------------------------------------------
    ("Quelles sont les répercussions des tarifs douaniers sur l'engrais russe, 4 ans plus tard?", "trade"),
    ("Le taux de chômage a un peu baissé en juillet, mais le marché du travail n'est pas encore solide", "monetary"),
    ("Démystifier l'économie | Trump pourrait-il simplement se retirer de l'ACEUM ?", "trade"),
    ("L'emploi a bondi en juillet, mais la Banque du Canada devrait maintenir ses taux inchangés", "monetary"),
    ("Les exportations de la Chine ont battu les attentes en juillet, portées par la tech", None),
    ("Chine : les exportations et importations solides en juillet", None),
    ("Le Sénat des États-Unis adopte une nouvelle série de sanctions contre Moscou", None),
    ("Ouverture du détroit d'Ormuz : l'Iran se dit très proche d'un accord avec Oman", "energy"),
    ("Le Pentagone va investir 400 millions de dollars dans une mine australienne de terres rares", "tech"),
    ("Attaques de gazoduc, centrales hors service : l'Ukraine menacée de pénurie d'énergie", "energy"),
    ("La roupie indienne stagne, l'intervention de la banque centrale tempère les inquiétudes", "monetary"),
    ("Le Canada envisage plusieurs nouvelles concessions pour éviter les tarifs douaniers américains", "trade"),
    ("La semaine à venir à Wall Street : les chiffres de l'inflation mettront à l'épreuve les actions", "monetary"),
    # Lacune reelle du filtre, presente aussi en anglais : la liste connaissait
    # le controle et l'interdiction des exportations, mais pas la restriction.
    ("La Chine annonce des restrictions sur les exportations de pièces de drones vers les Etats-Unis", "trade"),
]

# ------------------------------------------------------------
# Nettoyage des suffixes Google News
# ------------------------------------------------------------
SUFFIXES = [
    ("Canada must avoid concessions in U.S. trade talks, dairy farmers warn - Global News",
     "Global News",
     "Canada must avoid concessions in U.S. trade talks, dairy farmers warn"),
    ("China's economy gains steam amid rising global uncertainty - North Bay Nugget",
     "North Bay Nugget",
     "China's economy gains steam amid rising global uncertainty"),
]


def principal():
    echecs = []

    print("=" * 72)
    print("REJETS ATTENDUS")
    print("=" * 72)
    for titre in REJETS:
        r = evaluer(titre)
        ok = not r["accepte"]
        marque = "ok  " if ok else "ECHEC"
        print(f"  {marque} {titre[:58]:<58} {r['motif'][:40]}")
        if not ok:
            echecs.append(("faux positif", titre, r["motif"]))

    print()
    print("=" * 72)
    print("ACCEPTATIONS ATTENDUES")
    print("=" * 72)
    for titre, theme_attendu in ACCEPTES:
        r = evaluer(titre)
        ok = r["accepte"]
        marque = "ok  " if ok else "ECHEC"
        print(f"  {marque} {titre[:52]:<52} "
              f"[{str(r['theme']):<11}] score {r['score']:>2}")
        if not ok:
            echecs.append(("faux negatif", titre, r["motif"]))
        elif theme_attendu and r["theme"] != theme_attendu:
            echecs.append(("theme", titre,
                           f"attendu {theme_attendu}, obtenu {r['theme']}"))

    print()
    print("=" * 72)
    print("NETTOYAGE DES SUFFIXES")
    print("=" * 72)
    for brut, source, attendu in SUFFIXES:
        obtenu = nettoyer_titre(brut, source)
        ok = obtenu == attendu
        print(f"  {'ok  ' if ok else 'ECHEC'} {obtenu[:62]}")
        if not ok:
            echecs.append(("suffixe", brut, f"obtenu « {obtenu} »"))

    print()
    print("=" * 72)
    total = len(REJETS) + len(ACCEPTES) + len(SUFFIXES)
    if echecs:
        print(f"{len(echecs)} echec(s) sur {total} cas")
        for genre, titre, detail in echecs:
            print(f"  [{genre}] {titre[:60]}")
            print(f"           {detail}")
        return 1
    print(f"{total} cas, aucun echec")
    return 0


if __name__ == "__main__":
    sys.exit(principal())

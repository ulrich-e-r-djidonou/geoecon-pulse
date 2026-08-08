#!/usr/bin/env python3
"""
GeoEcon Pulse — Filtre de pertinence geoeconomique des actualites.

Pourquoi ce module existe
-------------------------
La version precedente acceptait un titre des qu'un seul mot d'une longue liste
apparaissait dedans. Deux consequences observees en production :

  « Felix Auger-Aliassime se retire de l'Omnium Banque Nationale »
      accepte parce que « banque » figurait dans la liste economique.

  « L'homme arrete sur un golf de Trump accuse de possession illegale d'arme
    a feu »
      accepte parce que « trump » figurait dans la liste economique.

Aucun des deux n'a de contenu geoeconomique. Le filtre est donc reconstruit
autour de trois idees :

1. Un veto dur : sport, faits divers, divertissement, curiosites scientifiques
   ne passent jamais, quel que soit le reste du titre.
2. Un veto conditionnel : meteo, politique interieure de procedure et rappels
   de produits ne passent que si un terme geoeconomique fort accompagne.
3. Un score : un terme fort suffit, sinon il en faut deux moyens. Un nom de
   dirigeant (Trump, Xi, Modi, Carney) ne compte pour rien : ce n'est pas un
   sujet economique, c'est un acteur.

Le module est autonome et sans reseau pour rester testable :
`python scripts/test_news_filter.py` rejoue les cas reels observes.
"""

import re
import unicodedata

# ============================================================
# OUTILLAGE
# ============================================================


def normaliser(texte):
    """Minuscules sans accents : « Felix » et « Félix » se comparent pareil."""
    decompose = unicodedata.normalize("NFD", texte)
    sans_accent = "".join(c for c in decompose if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", sans_accent).lower()


def _avec_pluriel(terme):
    """Rend un terme tolerant au pluriel, mot par mot.

    « central bank » ne reconnaissait pas « central banks » : le lookahead
    (?!\\w) bute sur le s final. Le defaut etait systematique et silencieux,
    il touchait chaque terme dont le pluriel n'avait pas ete liste a la main.
    Il a ete trouve sur un titre de The Economist, « How—and how much—should
    central banks talk? », ecarte faute de signal alors qu'il en portait un.

    Le s optionnel est pose sur chaque mot d'au moins quatre lettres, ce qui
    couvre aussi l'accord francais : « banque centrale » attrape « banques
    centrales ». Les mots courts et les sigles sont laisses tels quels, pour
    ne pas transformer « g7 » en « g7s ».
    """
    morceaux = []
    for mot in terme.split(" "):
        echappe = re.escape(mot)
        noyau = mot.replace("'", "").replace("-", "").replace(".", "")
        if noyau.isalpha() and len(noyau) >= 4 and not mot.endswith("s"):
            echappe += "s?"
        morceaux.append(echappe)
    return " ".join(morceaux)


def compiler(termes):
    """Alternance ancree sur des frontieres de mot, tolerante au pluriel.

    Les lookarounds remplacent \\b : ils fonctionnent aussi pour les termes qui
    finissent par un caractere non alphanumerique (« u.s. », « e. coli »).
    Le tri par longueur decroissante fait gagner l'expression la plus longue.
    """
    parts = sorted((_avec_pluriel(t) for t in termes), key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)")


def occurrences(motif, texte):
    return set(motif.findall(texte))


# ============================================================
# VETO DUR — rejet quel que soit le reste du titre
# ============================================================

SPORT = [
    # ligues et instances
    "nhl", "lnh", "nba", "nfl", "mlb", "mls", "fifa", "uefa", "ufc", "ipl",
    "atp", "wta", "pga", "ncaa", "formula 1", "formule 1", "grand prix",
    # competitions (« omnium » : le piege Banque Nationale)
    "omnium", "coupe stanley", "stanley cup", "super bowl", "world cup",
    "coupe du monde", "grand chelem", "grand slam", "wimbledon",
    "roland-garros", "us open", "australian open", "french open",
    "champions league", "ligue des champions", "tournoi", "tournament",
    "championnat", "championship", "playoff", "playoffs", "eliminatoires",
    "huitiemes", "quarts de finale", "demi-finale", "demi-finales",
    "mi-temps", "test series", "odi", "t20", "wicket", "innings",
    # disciplines
    "hockey", "soccer", "football", "basketball", "baseball", "tennis",
    "golf", "cricket", "rugby", "boxe", "boxing", "athletisme", "natation",
    "olympic", "olympics", "olympique", "olympiques", "marathon",
    "gymnastique", "patinage", "ski alpin", "curling",
    # vocabulaire de match
    "entraineur", "quarterback", "batsman", "touchdown", "home run",
    "penalty shootout", "hat-trick", "mvp",
]

FAITS_DIVERS = [
    "arrested", "arrete", "arretee", "arrestation", "detained",
    "charged with", "accuse de", "accusee de", "indicted", "inculpe",
    "murder", "meurtre", "homicide", "manslaughter",
    "shooting", "fusillade", "shot dead", "stabbing", "poignarde",
    "assault", "agression", "rape", "viol", "sexual abuse",
    "kidnap", "kidnapped", "enlevement", "abducted",
    "arme a feu", "firearm", "gun charge", "gun laws", "handgun",
    "manhunt", "missing person", "disparition inquietante",
    "guilty plea", "plaidoyer de culpabilite", "pleads guilty",
    "sentenced to", "condamne a", "jailed", "prison sentence",
    "car crash", "hit-and-run", "delit de fuite", "drunk driving",
    "drug bust", "saisie de drogue", "cartel arrest",
]

DIVERTISSEMENT = [
    "celebrity", "celebrite", "actor", "acteur", "actrice", "actress",
    "singer", "chanteur", "chanteuse", "rapper", "album", "concert",
    "box office", "netflix series", "tv show", "reality show",
    "red carpet", "tapis rouge", "oscars", "grammy", "emmy",
    "festival de cannes", "met gala", "royal family", "famille royale",
    "prince harry", "princess", "duchess", "obituary", "necrologie",
    "horoscope", "zodiac", "lottery", "loterie", "viral video",
    "recipe", "recette", "restaurant review", "fashion week",
]

CURIOSITES = [
    "glueball", "particle physics", "dinosaur", "dinosaure", "fossil",
    "fossile", "archaeolog", "archeolog", "astronomy", "astronomie",
    "telescope", "black hole", "trou noir", "comet", "comete",
    "new species", "nouvelle espece", "whale", "baleine", "panda",
    "zoo", "aquarium", "ufo", "ovni", "mummy", "momie",
]

# Titres qui ne sont pas une nouvelle mais un index de nouvelles.
AGREGATS = [
    "must-read", "must read", "top stories", "roundup", "briefing",
    "newsletter", "podcast", "watch live", "live updates", "en direct",
    "en images", "en cartes", "in pictures", "photos of the week", "quiz",
]

VETO_DUR = compiler(SPORT + FAITS_DIVERS + DIVERTISSEMENT + CURIOSITES + AGREGATS)

# Commandite sportive : « Omnium Banque Nationale », « Coupe Rogers ».
# Deuxieme ligne de defense, independante du mot « omnium ».
VETO_COMMANDITE = re.compile(
    r"(?<!\w)(omnium|coupe|tournoi|classique|championnat|trophee)\s+"
    r"(?:\w+\s+){0,2}(banque|bank|rogers|bell|telus|desjardins)(?!\w)"
)

# ============================================================
# VETO CONDITIONNEL — rejet sauf si un terme fort accompagne
# ============================================================

METEO = [
    "typhoon", "typhon", "hurricane", "ouragan", "tornado", "tornade",
    "earthquake", "seisme", "tremblement de terre", "tsunami",
    "wildfire", "feu de foret", "feux de foret", "flood", "flooding",
    "inondation", "inondations", "heat wave", "canicule", "blizzard",
    "snowstorm", "tempete de neige", "evacuation", "evacuations",
    "landslide", "glissement de terrain", "volcano", "volcan",
]

POLITIQUE_PROCEDURALE = [
    "primary", "primaries", "caucus", "ballot", "gerrymander",
    "campaign rally", "rassemblement partisan", "stump speech",
    "poll numbers", "sondage", "approval rating", "cote de popularite",
    "confirmed as", "confirmation hearing", "cabinet reshuffle",
    "remaniement", "swearing-in", "assermentation", "voting bill",
    "attorney general", "supreme court nominee", "impeachment",
    "leadership race", "course a la direction", "by-election",
    "election partielle", "candidat", "candidate for",
]

SANTE_ET_RAPPELS = [
    "food recall", "rappel de produit", "rappel alimentaire", "salmonella",
    "salmonelle", "listeria", "e. coli", "cyclospora", "contamination",
    "food poisoning", "intoxication alimentaire", "cancer diagnosis",
    "symptoms", "symptomes", "vaccine side effect", "measles", "rougeole",
]

VETO_CONDITIONNEL = compiler(METEO + POLITIQUE_PROCEDURALE + SANTE_ET_RAPPELS)

# ============================================================
# SIGNAL FORT — un seul suffit
# ============================================================

FORT_COMMERCE = [
    "tariff", "tariffs", "tarif", "tarifs", "tarifaire", "droits de douane",
    "customs duty", "surtaxe", "dumping", "antidumping", "countervailing",
    "trade deal", "trade talks", "trade agreement", "accord commercial",
    "negociations commerciales", "free trade", "libre-echange",
    "trade war", "guerre commerciale", "trade dispute", "differend commercial",
    "cusma", "usmca", "aceum", "nafta", "alena", "wto", "omc",
    "trade surplus", "excedent commercial", "trade deficit",
    "deficit commercial", "trade barrier", "barriere commerciale",
    "export control", "export controls", "controle des exportations",
    "export ban", "embargo", "entity list", "quota d'importation",
    # « La Chine annonce des restrictions sur les exportations de pieces de
    # drones » etait ecarte : la liste connaissait le controle et l'interdiction
    # des exportations, mais pas la restriction. Lacune presente aussi en
    # anglais, decouverte en passant les flux francophones dans le filtre.
    "export restriction", "export restrictions", "import restriction",
    "import restrictions", "restrictions sur les exportations",
    "restriction des exportations", "restrictions a l'exportation",
    "restrictions sur les importations", "restrictions a l'importation",
    "safeguard investigation", "safeguard measure", "trade remedy",
    "enquete de sauvegarde", "mesure de sauvegarde",
    "duties", "additional duties", "droits additionnels",
    "dispute settlement", "reglement des differends", "goods trade",
    "supply chain", "supply chains", "chaine d'approvisionnement",
    "chaines d'approvisionnement", "reshoring", "relocalisation",
    "decoupling", "decouplage", "friendshoring", "chokepoint",
]

FORT_MONETAIRE = [
    "policy rate", "taux directeur", "interest rate decision", "rate cut",
    "rate cuts", "rate hike", "baisse de taux", "hausse de taux",
    "central bank", "banque centrale", "federal reserve", "bank of canada",
    "banque du canada", "pboc", "reserve bank of india", "european central bank",
    "monetary policy", "politique monetaire", "quantitative easing",
    "monetary policy report", "rapport sur la politique monetaire",
    "summary of deliberations", "resume des deliberations", "deliberations",
    "rate decision", "decision de taux",
    "inflation", "disinflation", "deflation", "consumer price index",
    "indice des prix a la consommation", "core inflation", "inflation sous-jacente",
    "consumer prices", "producer prices", "wholesale prices",
    "prix a la consommation", "prix de gros", "food prices", "prix alimentaires",
    "bond yield", "bond yields", "rendement obligataire", "treasury yield",
    "sovereign debt", "dette souveraine", "credit rating", "note de credit",
    "exchange rate", "taux de change", "currency", "devise", "devises",
    "yuan", "renminbi", "rupee", "roupie", "loonie", "huard",
    "devaluation", "devaluation monetaire",
    # « African countries are souring on the dollar » (The Economist) etait
    # ecarte : les listes connaissaient « currency » et « devise », mais
    # aucune monnaie de reserve par son nom, ni le vocabulaire du systeme
    # monetaire international.
    "the dollar", "le dollar", "greenback", "reserve currency",
    "monnaie de reserve", "dedollarisation", "de-dollarisation",
    "de-dollarization", "currency peg", "ancrage monetaire",
    "capital flight", "fuite des capitaux", "currency swap",
    "accord de swap", "foreign reserves", "reserves de change",
    # « China's property bust is spilling across its borders » (PIIE) etait
    # ecarte de la meme facon : l'immobilier, canal de transmission majeur
    # d'une crise, n'apparaissait nulle part.
    "housing market", "property market", "marche immobilier", "immobilier",
    "real estate", "property bust", "housing bubble", "bulle immobiliere",
    "krach immobilier", "mortgage rate", "taux hypothecaire",
    "construction starts", "mises en chantier",
]

FORT_ACTIVITE = [
    "gdp", "pib", "gross domestic product", "produit interieur brut",
    "recession", "stagflation", "economic growth", "croissance economique",
    "unemployment", "unemployment rate", "chomage", "taux de chomage",
    "jobs", "job", "employment", "emplois", "hiring", "embauche",
    "jobs report", "payrolls", "nonfarm payrolls", "labour force survey",
    "enquete sur la population active", "layoffs", "mises a pied",
    "job losses", "pertes d'emplois", "job gains", "creation d'emplois",
    "hiring freeze", "productivity", "productivite",
    "budget deficit", "deficit budgetaire", "fiscal policy",
    "politique budgetaire", "stimulus", "plan de relance", "austerity",
    "austerite", "subsidy", "subsidies", "subvention", "subventions",
    "carbon tax", "taxe carbone", "corporate tax", "impot des societes",
]

FORT_ENERGIE = [
    "opec", "opep", "brent", "wti", "crude oil", "petrole brut",
    "oil prices", "prix du petrole", "oil output", "production petroliere",
    "oil shock", "choc petrolier", "oil supply", "oil market",
    # « Iran's oil exports stall » etait classe en geopolitique faute que
    # l'exportation de brut figure parmi les termes energetiques.
    "oil export", "crude export", "exportations de petrole",
    "oil terminal", "terminal petrolier", "oil embargo", "embargo petrolier",
    "lng", "gnl", "pipeline", "oleoduc", "gazoduc", "refinery", "raffinerie",
    "hormuz", "ormuz", "strait of hormuz", "detroit d'ormuz",
    "red sea", "mer rouge",
    "suez canal", "canal de suez", "panama canal", "canal de panama",
    "energy transition", "transition energetique", "power grid",
    "reseau electrique", "uranium", "nuclear plant", "centrale nucleaire",
]

FORT_TECH = [
    "semiconductor", "semiconductors", "semi-conducteur", "semi-conducteurs",
    "chipmaker", "chip export", "chip curbs", "puce electronique",
    "rare earth", "rare earths", "terres rares", "critical minerals",
    "mineraux critiques", "lithium", "cobalt", "graphite",
    "data center", "data centre", "centre de donnees", "cloud infrastructure",
    "artificial intelligence", "intelligence artificielle",
    "tech sovereignty", "souverainete numerique", "chip act", "chips act",
    "5g", "6g", "quantum computing", "informatique quantique",
    "cyberattack", "cyberattaque", "digital services tax", "taxe numerique",
]

FORT_GEOPOLITIQUE = [
    "sanction", "sanctions", "sanctionne", "nato", "otan",
    "defence spending", "defense spending", "depenses militaires",
    "military alliance", "arms deal", "contrat d'armement",
    "nationalisation", "nationalization", "expropriation",
    "foreign investment", "investissement etranger", "screening mechanism",
    "sovereign wealth fund", "fonds souverain", "capital controls",
    "controle des capitaux", "geopolitical risk", "risque geopolitique",
    "blockade", "blocus", "trade route", "route commerciale",
    "belt and road", "nouvelles routes de la soie", "brics", "g7", "g20",
]

FORT_ENTREPRISE = [
    "antitrust", "monopole", "merger", "fusion-acquisition", "acquisition",
    "takeover bid", "offre publique d'achat", "ipo",
    "introduction en bourse", "bankruptcy", "faillite", "bailout",
    "sauvetage financier", "nationalise", "delisting", "radiation",
    "net profit", "quarterly results", "q1 results", "q2 results",
    "q3 results", "q4 results", "earnings report", "resultats trimestriels",
]

THEMES_FORTS = {
    "trade": FORT_COMMERCE,
    "monetary": FORT_MONETAIRE + FORT_ACTIVITE,
    "energy": FORT_ENERGIE,
    "tech": FORT_TECH,
    "geopolitics": FORT_GEOPOLITIQUE,
}

TOUS_FORTS = (
    FORT_COMMERCE + FORT_MONETAIRE + FORT_ACTIVITE + FORT_ENERGIE
    + FORT_TECH + FORT_GEOPOLITIQUE + FORT_ENTREPRISE
)
MOTIF_FORT = compiler(TOUS_FORTS)
MOTIFS_THEME_FORT = {t: compiler(l) for t, l in THEMES_FORTS.items()}

# ============================================================
# SIGNAL MOYEN — il en faut deux
# ============================================================

MOYEN = {
    "trade": [
        "trade", "commerce", "commercial", "export", "exports", "exportation",
        "exportations", "import", "imports", "importation", "importations",
        "manufacturing", "manufacturier", "factory", "factories", "usine",
        "usines", "industry", "industrie", "industriel", "shipping",
        "freight", "fret", "port", "ports", "logistics", "logistique",
        "customs", "douane", "tanker", "petrolier", "cargo", "container",
        "conteneur", "supplier", "fournisseur", "goods", "marchandises",
        "shipment", "shipments", "expedition", "warehouse", "entrepot",
    ],
    "monetary": [
        "bank", "banque", "banks", "banques", "lender", "market", "markets",
        "marche", "marches", "stock", "stocks", "bourse", "shares", "actions",
        "index", "indice", "dollar", "euro", "yen", "bond", "bonds",
        "obligation", "obligations", "investor", "investors", "investisseur",
        "investisseurs", "fund", "funds", "fonds", "capital", "credit",
        "price", "prices", "prix", "cost", "costs", "cout", "couts",
        "tax", "taxes", "impot", "impots", "revenue", "revenu", "profit",
        "profits", "benefice", "benefices", "earnings", "resultats",
        "billion", "billions", "milliard", "milliards", "trillion", "crore",
        "economy", "economie", "economic", "economique", "growth",
        "croissance", "demand", "demande", "production", "productivity",
        "wages", "salaires", "workers", "travailleurs", "investment",
        "investissement", "investissements", "spending", "depenses",
        "aid", "aide", "loan", "pret", "grant", "financing", "financement",
        "funding", "pledge", "pledges", "promet",
    ],
    "energy": [
        "oil", "petrole", "gas", "gaz", "energy", "energie", "energetique",
        "electricity", "electricite", "power", "fuel", "carburant",
        "barrel", "baril", "coal", "charbon", "solar", "solaire",
        "wind", "eolien", "eolienne", "renewable", "renouvelable",
        "nuclear", "nucleaire", "hydrogen", "hydrogene", "emissions",
        "carbon", "carbone", "climate", "climat", "mine", "mining",
        "miniere", "drilling", "forage",
    ],
    "tech": [
        "tech", "technology", "technologie", "technologique", "chip", "chips",
        "software", "logiciel", "hardware", "startup", "cloud", "cyber",
        "quantum", "quantique", "robot", "robotique", "automation",
        "automatisation", "digital", "numerique", "platform", "plateforme",
        "innovation", "patent", "brevet", "biotech", "pharma", "data",
        "donnees", "algorithm", "algorithme", "telecom",
    ],
    "geopolitics": [
        "war", "guerre", "conflict", "conflit", "military", "militaire",
        "defence", "defense", "security", "securite", "troops", "troupes",
        "missile", "drone", "alliance", "treaty", "traite", "diplomacy",
        "diplomatie", "summit", "sommet", "talks", "pourparlers",
        "government", "gouvernement", "policy", "politique", "regulation",
        "reglementation", "law", "loi", "bill", "projet de loi",
        "pentagon", "white house", "maison blanche", "congress", "senate",
        "senat", "parliament", "parlement", "ministry", "ministere",
        "regulator", "commission", "administration", "envoy", "ambassador",
        "ambassadeur", "blacklist", "liste noire", "fine", "fined", "amende",
        "penalty", "ruling", "lawsuit", "poursuite", "probe", "enquete",
    ],
}

MOTIFS_THEME_MOYEN = {t: compiler(l) for t, l in MOYEN.items()}
MOTIF_MOYEN = compiler([m for liste in MOYEN.values() for m in liste])

# Acronymes forts, a casse significative : « Fed » compte, pas le « fed » de
# « fed up » ; « IPO » compte, pas « ipo ».
MOTIF_ACRONYMES_FORTS = re.compile(
    r"(?<!\w)(?:GDP|PIB|CPI|IPC|OPEC|OPEP|WTO|OMC|NATO|OTAN|FDI|IDE|"
    r"LNG|GNL|RBI|PBoC|ECB|BCE|BoC|IPO|M&A|Fed|FTA|FTAs|USMCA|CUSMA)(?!\w)"
)

# Rattachement thematique des acronymes : sans cela, un titre dont le seul
# signal est « Fed » ou « WTO » tombe dans le theme par defaut.
ACRONYMES_PAR_THEME = {
    "monetary": ["GDP", "PIB", "CPI", "IPC", "ECB", "BCE", "BoC", "RBI",
                 "PBoC", "Fed", "IPO", "M&A"],
    "trade": ["WTO", "OMC", "FTA", "FTAs", "USMCA", "CUSMA", "FDI", "IDE"],
    "energy": ["OPEC", "OPEP", "LNG", "GNL"],
    "tech": ["AI", "IA", "EV", "EVs", "5G", "6G"],
    "geopolitics": ["NATO", "OTAN"],
}
MOTIFS_THEME_ACRONYME = {
    t: re.compile(r"(?<!\w)(?:" + "|".join(re.escape(a) for a in liste) + r")(?!\w)")
    for t, liste in ACRONYMES_PAR_THEME.items()
}

# « 44 000 workers », « 75,100 jobs », « 23 000 postes » : un effectif chiffre
# est un chiffre du marche du travail, meme sans autre mot-cle.
MOTIF_EMPLOI_CHIFFRE = re.compile(
    r"\d[\d\s,.]*\s?(?:workers|jobs|positions|employees|emplois|postes|"
    r"travailleurs|salaries)(?!\w)",
    re.IGNORECASE,
)

# Acronymes moyens : « AI » est un sujet trop large pour valoir a lui seul.
# La casse evite que le « ai » de « j'ai » compte comme intelligence
# artificielle.
MOTIF_ACRONYMES_MOYENS = re.compile(r"(?<!\w)(?:AI|IA|EV|EVs|5G|6G)(?!\w)")

# Montants : « $1.2bn », « 400 million », « Rs 32 crore ». Un ordre de
# grandeur chiffre est un signal moyen d'enjeu economique.
MOTIF_MONTANT = re.compile(
    r"[$£€¥]\s?\d|(?:EUR|USD|CAD|GBP|INR|CNY|RMB|Rs)\s?\d|"
    r"\d\s?(?:bn|tn|billion|million|trillion|crore|lakh|milliard|millions?)"
    r"(?!\w)",
    re.IGNORECASE,
)

# ============================================================
# PORTEE — l'axe qui separe le macro du fait divers d'entreprise
# ============================================================
#
# Deux termes moyens ne suffisent pas : « thrift store launches AI tool to
# price items » en aligne deux (AI, price) sans rien avoir de geoeconomique.
# Il faut en plus qu'un Etat, une institution ou un agregat de marche soit en
# jeu. Les noms de pays vivent ici plutot que dans les signaux : ils situent
# une nouvelle, ils ne la qualifient pas.

PORTEE = [
    "canada", "canadian", "canadien", "canadienne", "ottawa", "quebec",
    "united states", "america", "american", "americain", "americaine",
    "washington", "china", "chinese", "chine", "chinois", "chinoise",
    "beijing", "pekin", "india", "indian", "inde", "indien", "indienne",
    "delhi", "mumbai", "japan", "japanese", "japon", "japonais",
    "europe", "european", "europeen", "europeenne", "brussels", "bruxelles",
    "germany", "german", "allemagne", "allemand", "france", "french",
    "britain", "british", "royaume-uni", "london", "londres",
    "russia", "russian", "russie", "russe", "ukraine", "ukrainian",
    "iran", "iranian", "iranien", "israel", "taiwan", "taiwanese",
    "korea", "coree", "mexico", "mexique", "brazil", "bresil",
    "colombia", "colombie", "australia", "australie", "australian",
    "saudi", "arabie", "emirates", "turkey", "turquie", "vietnam",
    "euro", "eurozone", "zone euro", "spain", "espagne", "italy", "italie",
    "africa", "afrique", "asia", "asie", "global", "mondial", "mondiale",
    "world", "monde", "international", "national", "nationwide",
    # institutions
    "federal reserve", "central bank", "banque centrale", "imf", "fmi",
    "world bank", "banque mondiale", "government", "gouvernement",
    "parliament", "parlement", "congress", "senate", "senat", "ministry",
    "ministere", "pentagon", "white house", "maison blanche", "treasury",
    "regulator", "commission", "g7", "g20", "brics",
    # agregats
    "economy", "economie", "economic", "economique", "market", "markets",
    "marche", "marches", "industry", "industrie", "sector", "secteur",
    "trade", "commerce", "exports", "imports", "inflation", "nationale",
]

MOTIF_PORTEE = compiler(PORTEE)
MOTIF_PORTEE_ACRONYMES = re.compile(r"(?<!\w)(?:US|U\.S\.|UK|U\.K\.|EU|UAE|UN)(?!\w)")

# Noms de dirigeants : acteurs, pas sujets. Volontairement absents de toutes
# les listes — repertories ici pour documenter l'intention. « Trump » dans un
# titre ne rend pas ce titre economique.
NON_COMPTABILISES = [
    "trump", "biden", "xi", "modi", "carney", "poilievre", "putin", "poutine",
    "macron", "starmer", "netanyahu", "powell", "lula", "milei",
]


# ============================================================
# EVALUATION
# ============================================================


def evaluer(titre):
    """Decide si un titre merite sa place dans le tableau de bord.

    Retourne un dict : accepte (bool), theme (str), score (int),
    motif (str, la raison lisible du verdict).
    """
    if not titre or len(titre.strip()) < 15:
        return {"accepte": False, "theme": None, "score": 0,
                "motif": "titre trop court"}

    texte = normaliser(titre)

    veto = occurrences(VETO_DUR, texte)
    if veto:
        return {"accepte": False, "theme": None, "score": 0,
                "motif": f"veto dur : {', '.join(sorted(veto)[:3])}"}

    if VETO_COMMANDITE.search(texte):
        return {"accepte": False, "theme": None, "score": 0,
                "motif": "veto : commandite sportive"}

    forts = occurrences(MOTIF_FORT, texte)
    forts |= occurrences(MOTIF_ACRONYMES_FORTS, titre)  # casse d'origine
    if MOTIF_EMPLOI_CHIFFRE.search(titre):
        forts.add("effectif chiffre")

    conditionnel = occurrences(VETO_CONDITIONNEL, texte)
    if conditionnel and not forts:
        return {"accepte": False, "theme": None, "score": 0,
                "motif": f"veto conditionnel sans signal fort : "
                         f"{', '.join(sorted(conditionnel)[:2])}"}

    moyens = occurrences(MOTIF_MOYEN, texte)
    moyens |= occurrences(MOTIF_ACRONYMES_MOYENS, titre)
    if MOTIF_MONTANT.search(titre):
        moyens.add("montant")

    portee = occurrences(MOTIF_PORTEE, texte)
    portee |= occurrences(MOTIF_PORTEE_ACRONYMES, titre)

    score = 3 * len(forts) + len(moyens) + len(portee)

    if forts:
        return {"accepte": True, "theme": choisir_theme(texte, titre), "score": score,
                "motif": f"signal fort : {', '.join(sorted(forts)[:3])}"}

    if len(moyens) >= 2 and portee:
        return {"accepte": True, "theme": choisir_theme(texte, titre), "score": score,
                "motif": f"signaux moyens ({', '.join(sorted(moyens)[:3])}) "
                         f"et portee ({sorted(portee)[0]})"}

    if len(moyens) >= 2:
        return {"accepte": False, "theme": None, "score": score,
                "motif": "signaux economiques sans portee macro"}

    return {"accepte": False, "theme": None, "score": score,
            "motif": "aucun signal geoeconomique suffisant"}


def choisir_theme(texte, titre=""):
    """Theme le mieux etaye : un terme fort pese trois fois un terme moyen."""
    scores = {}
    for theme in MOYEN:
        fort = len(occurrences(MOTIFS_THEME_FORT[theme], texte))
        fort += len(occurrences(MOTIFS_THEME_ACRONYME[theme], titre))
        moyen = len(occurrences(MOTIFS_THEME_MOYEN[theme], texte))
        total = 3 * fort + moyen
        if total:
            scores[theme] = total
    if not scores:
        return "trade"
    return max(scores, key=scores.get)


# ============================================================
# CREDIBILITE DES SOURCES
# ============================================================
#
# Google News apporte le volume et la pertinence, mais aussi n'importe quel
# editeur : BeInCrypto, CryptoRank, Florida Politics et WKRN News 2 sont
# remontes des la premiere execution. Sur une piece de portfolio, une source
# faible coute aussi cher qu'un hors-sujet. Les rubriques d'editeurs choisies
# a la main sont approuvees d'office ; tout ce qui vient d'une requete est
# confronte a cette liste.

SOURCES_FIABLES = [
    # agences et quotidiens economiques de reference
    "reuters", "bloomberg", "financial times", "the economist",
    "wall street journal", "wsj", "the new york times", "new york times",
    "washington post", "associated press", "ap news", "agence france-presse",
    "afp", "barron's", "marketwatch", "fortune", "forbes",
    # Canada
    "the globe and mail", "globe and mail", "cbc", "radio-canada",
    "financial post", "national post", "toronto star", "la presse",
    "les affaires", "le devoir", "bnn bloomberg", "canadian press",
    # Royaume-Uni et Europe
    "bbc", "the guardian", "the telegraph", "the times", "sky news",
    "politico", "euronews", "deutsche welle", "dw", "france 24",
    "le monde", "les echos", "handelsblatt", "el pais", "der spiegel",
    # Etats-Unis
    "cnbc", "cnn", "npr", "abc news", "nbc news", "cbs news", "axios",
    "the hill", "foreign policy", "foreign affairs", "the atlantic",
    # Asie
    "south china morning post", "scmp", "nikkei", "nikkei asia", "caixin",
    "the straits times", "japan times", "korea herald", "the diplomat",
    # Inde
    "the economic times", "economic times", "business standard", "mint",
    "livemint", "the hindu", "hindu businessline", "the indian express",
    "indian express", "moneycontrol", "business today",
    # Moyen-Orient et international
    "al jazeera", "the national", "gulf news", "arab news",
    # presse francophone — ajoutee avec les flux FR, qui alimentent le mode
    # francais du site. Meme exigence que pour l'anglais : l'editeur doit etre
    # identifiable, sinon le titre ne passe pas.
    "la tribune", "le figaro", "l'opinion", "challenges", "l'express",
    "l'usine nouvelle", "le point", "liberation", "la croix", "le temps",
    "l'echo", "rtbf", "rfi", "france info", "franceinfo", "boursorama",
    "la presse canadienne", "ici radio-canada", "le journal de montreal",
    "le soleil", "les echos investir", "l'agefi", "le nouvel economiste",
    # recherche economique des banques et instituts prives. Aucune de ces
    # equipes n'expose de flux RSS : Desjardins ne propose qu'un abonnement
    # par courriel, BMO, la Banque Nationale, Credit Agricole et BNP Paribas
    # renvoient 404 ou un flux vide. Elles ne peuvent donc entrer que citees
    # par un agregateur, d'ou leur presence ici plutot que dans RSS_FEEDS.
    "desjardins", "etudes economiques desjardins", "mouvement desjardins",
    "banque nationale", "national bank of canada", "bmo", "bmo economics",
    "rbc economics", "scotiabank", "cibc", "td economics", "td bank",
    "oxford economics", "capital economics", "conference board",
    "moody's analytics", "s&p global", "fitch ratings", "morningstar",
    # institutions et think tanks
    "imf", "international monetary fund", "world bank", "wto",
    "world trade organization", "oecd", "bank of canada", "banque du canada",
    "statistics canada", "statistique canada", "federal reserve",
    "european central bank", "bis", "chatham house", "brookings",
    "peterson institute", "csis", "bruegel", "council on foreign relations",
]


def source_fiable(nom):
    """Vrai si l'editeur figure parmi les sources de reference.

    La comparaison porte sur le nom entier normalise : « the times » ne
    reconnait pas « Taipei Times », et « ap news » ne reconnait pas
    « Springfield News-Sun ».
    """
    if not nom:
        return False
    normalise = normaliser(nom).strip()
    for reference in SOURCES_FIABLES:
        if normalise == reference:
            return True
        if re.search(r"(?<!\w)" + re.escape(reference) + r"(?!\w)", normalise):
            return True
    return False


def nettoyer_titre(titre, source=None):
    """Retire le suffixe « - Editeur » que Google News ajoute a ses titres."""
    if not titre:
        return titre
    titre = titre.strip()
    if source:
        suffixe = f" - {source}"
        if titre.endswith(suffixe):
            return titre[: -len(suffixe)].strip()
    # Sans source connue : couper un dernier segment court apres « - ».
    if " - " in titre:
        tete, queue = titre.rsplit(" - ", 1)
        if len(queue) <= 40 and len(tete) >= 25:
            return tete.strip()
    return titre

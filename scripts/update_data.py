#!/usr/bin/env python3
"""
GeoEcon Pulse — Mise a jour des donnees.

Ce script rafraichit data/indicators.json a partir de sources publiques sans
cle d'API. Trois choix de conception meritent d'etre expliques.

1. Tout ce qui peut etre lu a la source l'est.
   Le tableau affichait des chiffres saisis a la main qui vieillissaient sans
   que rien ne le signale : le 8 aout 2026, le resume du Canada annoncait
   encore « perte surprise de 83 900 emplois en fevrier » alors que juillet
   affichait un gain de 75 100 emplois et un chomage a 6,4 %. Les indicateurs
   d'emploi, d'inflation et de taux sont desormais lus chez Statistique
   Canada, la Banque du Canada, le BLS et la Fed de New York.

2. Les resumes et le sentiment sont calcules, jamais rediges d'avance.
   Un paragraphe fige est un mensonge a retardement : il reste plausible
   longtemps apres etre devenu faux. Les resumes sont composes a partir des
   valeurs du jour, donc ils ne peuvent pas contredire le tableau.

3. Ce qui reste saisi a la main est signale comme tel.
   L'inflation et les taux directeurs de la Chine et de l'Inde sont desormais
   lus chez l'OCDE et la BRI, deux entrepots SDMX publics et sans cle. Il ne
   reste a la main que les previsions annuelles de croissance et les agregats
   du FMI. Ces champs portent "manual": true, leur periode reste affichee, et
   le controle de fraicheur ouvre une issue quand ils depassent leur seuil,
   au lieu de les laisser vieillir en silence.
"""

import csv
import io
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Windows envoie stdout en cp1252 : sans ce reglage, un simple log accentue
# fait planter le script. Le contenu ecrit dans le JSON est en UTF-8 et n'est
# jamais concerne — on corrige l'affichage, pas les donnees.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8",
                                  line_buffering=True)

import requests
import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from news_filter import (evaluer, nettoyer_titre, source_fiable, normaliser,  # noqa: E402
                         zone_mentionnee)

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "indicators.json"
REJETS_FILE = BASE_DIR / "data" / "rejets.json"

# Contenu editorial : ce que le pipeline ne peut pas deduire. Il vit dans ses
# propres fichiers plutot que dans indicators.json, pour qu'une mise a jour
# automatique ne puisse pas ecraser une analyse ecrite a la main, et pour
# qu'on voie d'un coup d'oeil ce qui est juge par un humain.
CHRONO_FILE = BASE_DIR / "data" / "chronologie.json"
ANALYSE_FILE = BASE_DIR / "data" / "analyse_provinciale.json"
INTERCO_FILE = BASE_DIR / "data" / "interconnexions.json"

# Controle de coherence (chaque valeur face a une seconde source) et sante
# des flux (alerte quand un flux cesse de repondre). Voir les sections plus
# bas ; l'un compare, l'autre persiste d'un passage a l'autre.
COHERENCE_FILE = BASE_DIR / "data" / "coherence.json"
SANTE_FLUX_FILE = BASE_DIR / "data" / "sante_flux.json"

TIMEOUT = 15
UA = {"User-Agent": "Mozilla/5.0 (compatible; GeoEconPulse/1.0)"}

EXCHANGE_RATES_URL = "https://api.frankfurter.app/latest?from=USD&to=CAD,CNY,INR"

STOCK_SYMBOLS = {
    "CA": "^GSPTSE",
    "US": "^GSPC",
    "CN": "000001.SS",
    "IN": "^BSESN",
    "WORLD": "ACWI",
}

# Flux RSS par region.
#
# Les trois flux feeds.reuters.com utilises jusqu'ici sont morts : Reuters a
# ferme ses RSS publics, et le script les interrogeait chaque jour en vain.
# Le vivier reel etait donc bien plus etroit que prevu, ce qui poussait le
# filtre a racler le fond de flux generalistes — d'ou le sport et les faits
# divers en page d'accueil.
#
# Deux familles de sources les remplacent : les rubriques economie des
# editeurs (URL propre, editeur connu) et des requetes Google News ciblees,
# qui garantissent le volume sur des sujets precis.
RSS_FEEDS = {
    "CA": [
        ("https://www.bankofcanada.ca/feed/", "Banque du Canada"),
        ("https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/business/", "Globe and Mail"),
        ("https://www.cbc.ca/webfeed/rss/rss-business", "CBC Business"),
        ("https://financialpost.com/category/news/economy/feed", "Financial Post"),
        ("https://news.google.com/rss/search?q=Canada+(tariffs+OR+trade+OR+%22Bank+of+Canada%22+OR+economy+OR+exports)+when:4d&hl=en-CA&gl=CA&ceid=CA:en", None),
    ],
    "US": [
        ("https://www.cnbc.com/id/20910258/device/rss/rss.html", "CNBC Economy"),
        ("https://www.cnbc.com/id/19832390/device/rss/rss.html", "CNBC International"),
        ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC Business"),
        ("https://www.federalreserve.gov/feeds/press_all.xml", "Federal Reserve"),
        ("https://www.ft.com/global-economy?format=rss", "Financial Times"),
        ("https://news.google.com/rss/search?q=(%22United+States%22+OR+Fed)+(tariffs+OR+trade+OR+inflation+OR+%22interest+rates%22+OR+sanctions)+when:4d&hl=en-US&gl=US&ceid=US:en", None),
    ],
    "CN": [
        ("https://www.scmp.com/rss/5/feed", "SCMP Economy"),
        ("https://www.scmp.com/rss/92/feed", "SCMP Business"),
        ("https://www.scmp.com/rss/36/feed", "SCMP Tech"),
        ("https://asia.nikkei.com/rss/feed/nar", "Nikkei Asia"),
        ("https://news.google.com/rss/search?q=China+(economy+OR+exports+OR+yuan+OR+tariffs+OR+semiconductors+OR+%22rare+earth%22)+when:4d&hl=en&gl=US&ceid=US:en", None),
    ],
    "IN": [
        ("https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms", "Economic Times"),
        ("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "ET Markets"),
        ("https://www.business-standard.com/rss/economy-102.rss", "Business Standard"),
        ("https://www.livemint.com/rss/economy", "Mint"),
        ("https://news.google.com/rss/search?q=India+(economy+OR+RBI+OR+rupee+OR+tariffs+OR+exports+OR+trade)+when:4d&hl=en-IN&gl=IN&ceid=IN:en", None),
    ],
    "WORLD": [
        ("https://www.wto.org/library/rss/latest_news_e.xml", "OMC"),
        ("https://www.ecb.europa.eu/rss/press.html", "BCE"),
        ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC Business"),
        # La presse economique de reference figurait dans la liste blanche
        # mais n'avait aucun flux direct : elle n'arrivait que par ricochet
        # via Google News, et le FT comme The Economist n'apparaissaient
        # jamais. Ces trois flux sont publics et repondent.
        ("https://www.ft.com/global-economy?format=rss", "Financial Times"),
        ("https://www.economist.com/finance-and-economics/rss.xml", "The Economist"),
        ("https://www.piie.com/rss/update.xml", "Peterson Institute"),
        ("https://news.google.com/rss/search?q=(tariffs+OR+%22trade+war%22+OR+sanctions+OR+%22supply+chain%22+OR+OPEC+OR+%22export+controls%22)+when:3d&hl=en&gl=US&ceid=US:en", None),
    ],
}

# Le site se dit bilingue mais servait les memes titres anglais dans les deux
# langues. Traduire automatiquement aurait demande une cle d'API et, surtout,
# aurait fait reecrire par une machine des titres de presse attribues nommement
# a leur editeur : un contresens de traduction devient alors une citation
# fausse. On lit donc la presse francophone a la source.
#
# Les flux ci-dessous ont ete testes un par un. Radio-Canada International
# (404), Les Echos (403) et France 24 (boucle de redirections) ne repondent
# pas et ne sont pas cables : c'est la lecon des flux Reuters morts, qui
# faisaient racler le fond de flux generalistes.
RSS_FEEDS_FR = {
    "CA": [
        ("https://ici.radio-canada.ca/rss/4159", "Radio-Canada"),
        ("https://www.ledevoir.com/rss/section/economie.xml", "Le Devoir"),
        ("https://www.lapresse.ca/affaires/rss", "La Presse"),
        ("https://news.google.com/rss/search?q=Canada+(tarifs+OR+commerce+OR+%22Banque+du+Canada%22+OR+economie+OR+exportations)+when:4d&hl=fr&gl=CA&ceid=CA:fr", None),
    ],
    "US": [
        ("https://www.lemonde.fr/economie/rss_full.xml", "Le Monde"),
        ("https://www.latribune.fr/feed.xml", "La Tribune"),
        ("https://news.google.com/rss/search?q=(Etats-Unis+OR+Fed)+(tarifs+OR+inflation+OR+commerce+OR+sanctions)+when:4d&hl=fr&gl=FR&ceid=FR:fr", None),
    ],
    "CN": [
        ("https://news.google.com/rss/search?q=Chine+(economie+OR+exportations+OR+yuan+OR+semi-conducteurs+OR+%22terres+rares%22)+when:4d&hl=fr&gl=FR&ceid=FR:fr", None),
        ("https://www.rfi.fr/fr/economie/rss", "RFI"),
    ],
    "IN": [
        ("https://news.google.com/rss/search?q=Inde+(economie+OR+roupie+OR+commerce+OR+exportations+OR+%22banque+centrale%22)+when:4d&hl=fr&gl=FR&ceid=FR:fr", None),
        # Une seule requete ne rendait qu'un titre retenu sur trente-huit : la
        # presse francophone couvre peu l'Inde. Un second angle, sur les
        # droits de douane et la croissance, elargit le vivier.
        ("https://news.google.com/rss/search?q=(Inde+OR+%22New+Delhi%22)+(%22droits+de+douane%22+OR+tarifs+OR+importations+OR+croissance+OR+inflation+OR+investissement)+when:7d&hl=fr&gl=FR&ceid=FR:fr", None),
    ],
    "WORLD": [
        ("https://www.latribune.fr/feed.xml", "La Tribune"),
        ("https://www.rfi.fr/fr/economie/rss", "RFI"),
        ("https://news.google.com/rss/search?q=(tarifs+douaniers+OR+%22guerre+commerciale%22+OR+sanctions+OR+OPEP+OR+%22chaine+d%27approvisionnement%22)+when:3d&hl=fr&gl=FR&ceid=FR:fr", None),
    ],
}

# Flux exemptes de la preuve de zone (voir zone_mentionnee, news_filter.py) :
# l'institution propre a une region parle d'elle par construction, inutile
# de lui demander de se citer elle-meme.
FLUX_EXEMPTS_ZONE = {
    "https://www.bankofcanada.ca/feed/",
    "https://www.federalreserve.gov/feeds/press_all.xml",
}

# Tout ce que le filtre ecarte, avec le motif. Ecrit dans data/rejets.json a
# la fin du passage et repris par le rapport hebdomadaire.
JOURNAL_REJETS = []

# Sante des flux : combien d'echecs consecutifs, sur combien de passages.
# Charge depuis data/sante_flux.json au debut du passage, mis a jour flux par
# flux, sauvegarde a la fin. Contrairement a JOURNAL_REJETS, cet etat doit
# survivre d'un passage a l'autre pour compter des echecs *consecutifs*.
SANTE_FLUX = {}
SEUIL_FLUX_EN_PANNE = 6  # ~2 jours a trois passages quotidiens

MAX_HEADLINES = 8

# Sources d'analyse : celles dont on veut la lecture meme quand elle date de
# la veille, par opposition au fil d'agence. Elles se disputent jusqu'a trois
# des huit places, a l'anciennete zero pres.
SOURCES_ANALYSE = {
    "financial times", "the economist", "bloomberg",
    "wall street journal", "wsj", "the new york times",
    "peterson institute", "the globe and mail", "le monde", "les echos",
    "nikkei asia", "south china morning post", "foreign policy",
    "foreign affairs", "la presse", "le devoir",
}
PLACES_ANALYSE = 3

# Sans plafond par editeur, un flux bavard occupe la moitie d'une region :
# ET Markets a fourni quatre des huit nouvelles indiennes du premier essai,
# dont deux resultats trimestriels de petites capitalisations.
MAX_PAR_SOURCE = 3

# Google News renvoie parfois un domaine plutot qu'un nom de publication.
NOMS_EDITEURS = {
    "bloomberg.com": "Bloomberg", "cnbc.com": "CNBC", "wsj.com": "The Wall Street Journal",
    "dw.com": "Deutsche Welle", "axios.com": "Axios", "reuters.com": "Reuters",
    "ft.com": "Financial Times", "nytimes.com": "The New York Times",
    "washingtonpost.com": "The Washington Post", "theguardian.com": "The Guardian",
    "bbc.com": "BBC", "bbc.co.uk": "BBC", "cbc.ca": "CBC",
    "scmp.com": "South China Morning Post", "aljazeera.com": "Al Jazeera",
    "economictimes.indiatimes.com": "The Economic Times",
    "thehindu.com": "The Hindu", "livemint.com": "Mint",
    "business-standard.com": "Business Standard", "nikkei.com": "Nikkei Asia",
    "thetimes.com": "The Times", "telegraph.co.uk": "The Telegraph",
}


# Un meme editeur arrivait sous plusieurs libelles selon le flux d'origine :
# « SCMP Economy », « SCMP Business », « SCMP Tech » et « South China Morning
# Post » comptaient pour quatre. Le plafond de trois titres par editeur, qui
# existe pour qu'une seule redaction n'occupe pas une zone entiere, etait donc
# contournable sans le vouloir.
ALIAS_EDITEURS = {
    "scmp economy": "South China Morning Post",
    "scmp business": "South China Morning Post",
    "scmp tech": "South China Morning Post",
    "scmp": "South China Morning Post",
    "globe and mail": "The Globe and Mail",
    "cbc business": "CBC",
    "cnbc economy": "CNBC",
    "cnbc international": "CNBC",
    "bbc business": "BBC",
    "et markets": "Economic Times",
    "the economic times": "Economic Times",
    "livemint": "Mint",
    "le monde.fr": "Le Monde",
    "investir les echos": "Les Echos",
    "the wall street journal": "WSJ",
    "new york times": "The New York Times",
    "ft": "Financial Times",
    "ici radio-canada": "Radio-Canada",
}


def joli_editeur(nom):
    """« bloomberg.com » devient « Bloomberg », « SCMP Tech » devient le SCMP."""
    if not nom:
        return nom
    cle = nom.strip().lower()
    if cle in ALIAS_EDITEURS:
        return ALIAS_EDITEURS[cle]
    if cle in NOMS_EDITEURS:
        return NOMS_EDITEURS[cle]
    if cle.endswith((".com", ".org", ".net", ".ca", ".co.uk", ".in")):
        racine = cle.rsplit(".", 2)[0].replace("www.", "")
        propre = racine.replace("-", " ").title()
        return ALIAS_EDITEURS.get(propre.lower(), propre)
    return nom.strip()

# ============================================================
# INDICATEURS MACRO — sources officielles sans cle
# ============================================================

# Banque du Canada, API Valet.
BDC_TAUX_DIRECTEUR = "V39079"
BDC_IPC_INDICE = "V41690973"
VALET_URL = "https://www.bankofcanada.ca/valet/observations/{series}/json?recent={n}"

# Fed de New York, taux de reference.
NYFED_EFFR_URL = "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/1.json"

# Bureau of Labor Statistics, API publique v1.
#
# DBnomics a ete evalue comme source de repli pour le BLS et comme source
# automatisable pour l'IPC de la Chine et de l'Inde : son miroir du BLS
# s'arretait a janvier 2025 et ses series FMI a juillet 2025, soit plus d'un
# an de retard sur les sources d'origine. Ecarte pour cette raison.
BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/{serie}"
BLS_IPC = "CUUR0000SA0"
BLS_CHOMAGE = "LNS14000000"
BLS_EMPLOI = "CES0000000001"

# Statistique Canada, Web Data Service. Enquete sur la population active,
# donnees desaisonnalisees, 15 ans et plus.
STATCAN_WDS = ("https://www150.statcan.gc.ca/t1/wds/rest/"
               "getDataFromVectorsAndLatestNPeriods")
STATCAN_CHOMAGE = 2062815   # taux de chomage, %
STATCAN_EMPLOI = 2062811    # emploi, milliers

# OCDE, entrepot SDMX public. Le jeu DF_PRICES_ALL couvre les non-membres,
# dont la Chine et l'Inde : c'est ce qui permet de sortir leur inflation de la
# saisie manuelle. La cle est REF_AREA.M.N.CPI.PA._T.N.GY, soit indice des
# prix a la consommation, tous postes, glissement annuel.
OCDE_PRIX = ("https://sdmx.oecd.org/public/rest/data/"
             "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/"
             "{pays}.M.N.CPI.PA._T.N.GY"
             "?lastNObservations={n}&format=csv")

# Banque des reglements internationaux, portail v2. WS_CBPOL rassemble les
# taux directeurs officiels d'une quarantaine de banques centrales, dont la
# PBoC (taux preferentiel a un an) et la RBI (taux de prise en pension).
# La serie quotidienne est plus fraiche que la mensuelle ; on garde la
# mensuelle en repli.
BRI_TAUX = ("https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/"
            "{freq}.{pays}?lastNObservations={n}&format=csv")

MOIS_FR = [
    "Janv.", "Fév.", "Mars", "Avril", "Mai", "Juin",
    "Juill.", "Août", "Sept.", "Oct.", "Nov.", "Déc.",
]
MOIS_FR_LONG = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]
MOIS_EN = [
    "Jan.", "Feb.", "Mar.", "Apr.", "May", "June",
    "July", "Aug.", "Sep.", "Oct.", "Nov.", "Dec.",
]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def obtenir(url, methode="get", tentatives=3, **kwargs):
    """Requete HTTP avec quelques reprises sur panne passagere.

    Le BLS renvoie regulierement un 503 « Temporarily Down for Maintenance »
    de quelques minutes. Sans reprise, une seule seconde mal tombee prive le
    tableau des chiffres d'emploi americains jusqu'au passage suivant.
    Les erreurs 4xx ne sont pas reessayees : elles ne guerissent pas d'
    elles-memes.
    """
    kwargs.setdefault("headers", UA)
    kwargs.setdefault("timeout", TIMEOUT)
    derniere = None
    for essai in range(tentatives):
        try:
            resp = getattr(requests, methode)(url, **kwargs)
            if resp.status_code < 400:
                return resp
            derniere = requests.HTTPError(
                f"{resp.status_code} pour {url}", response=resp)
            if resp.status_code < 500:
                break
        except requests.RequestException as e:
            derniere = e
        if essai < tentatives - 1:
            time.sleep(2 * (essai + 1))
    raise derniere


def periode_fr(annee, mois):
    return f"{MOIS_FR[mois - 1]} {annee}"


def numero_mois(jeton):
    """Numero du mois designe par un jeton comme « Juill. », sinon None.

    Comparer les trois premieres lettres ne suffit pas : « Juin » et
    « Juill. » commencent tous deux par « jui », si bien que juillet etait lu
    comme juin, aussi bien dans les resumes anglais que dans le calcul d'age.
    """
    if not jeton:
        return None
    # Les accents sont retires des deux cotes : « Fev. », « Fév. » et
    # « fevrier » doivent tous designer le meme mois.
    propre = normaliser(jeton).strip().rstrip(".")
    for numero, nom in enumerate(MOIS_FR, start=1):
        if propre == normaliser(nom).rstrip("."):
            return numero
    for numero, nom in enumerate(MOIS_FR_LONG, start=1):
        if propre == normaliser(nom):
            return numero
    # Abreviations d'une autre main que la notre (« Jan. » pour « Janv. »).
    # On n'accepte le prefixe que s'il ne designe qu'un seul mois : « jui »
    # reste ambigu entre juin et juillet, et doit donc echouer bruyamment.
    if len(propre) >= 3:
        candidats = {n for n, nom in enumerate(MOIS_FR_LONG, start=1)
                     if normaliser(nom).startswith(propre)}
        if len(candidats) == 1:
            return candidats.pop()
    return None


def variation_annuelle(recent, an_avant):
    return round((recent / an_avant - 1) * 100, 1)


# ============================================================
# CANADA — Banque du Canada et Statistique Canada
# ============================================================

def fetch_valet(series, n):
    resp = obtenir(VALET_URL.format(series=series, n=n))
    resp.raise_for_status()
    return resp.json().get("observations", [])


def fetch_taux_directeur_canada():
    try:
        obs = fetch_valet(BDC_TAUX_DIRECTEUR, 1)
        if not obs:
            log("  ERREUR taux directeur CA : aucune observation")
            return None
        derniere = obs[0]
        valeur = float(derniere[BDC_TAUX_DIRECTEUR]["v"])
        jour = datetime.strptime(derniere["d"], "%Y-%m-%d")
        log(f"  Taux directeur CA : {valeur} % au {derniere['d']}")
        return {"value": valeur, "period": periode_fr(jour.year, jour.month)}
    except Exception as e:
        log(f"  ERREUR taux directeur CA : {e}")
        return None


def _ipc_canada_series(n=30):
    """Indice IPC mensuel du Canada, du plus ancien au plus recent."""
    obs = fetch_valet(BDC_IPC_INDICE, n)
    return {o["d"]: float(o[BDC_IPC_INDICE]["v"]) for o in obs}


def fetch_inflation_canada():
    try:
        valeurs = _ipc_canada_series(14)
        if not valeurs:
            log("  ERREUR inflation CA : aucune observation")
            return None
        dernier = max(valeurs)
        recent = datetime.strptime(dernier, "%Y-%m-%d")
        cle = recent.replace(year=recent.year - 1).strftime("%Y-%m-%d")
        if cle not in valeurs:
            log(f"  ERREUR inflation CA : {cle} absent de la serie")
            return None
        taux = variation_annuelle(valeurs[dernier], valeurs[cle])
        log(f"  Inflation CA : {taux} % ({dernier} sur douze mois)")
        return {"value": taux, "period": periode_fr(recent.year, recent.month)}
    except Exception as e:
        log(f"  ERREUR inflation CA : {e}")
        return None


def fetch_sparkline_inflation_canada():
    """Douze points d'inflation annuelle : il faut 24 mois d'indice."""
    try:
        valeurs = _ipc_canada_series(30)
        points = []
        for d in sorted(valeurs):
            ref = datetime.strptime(d, "%Y-%m-%d")
            cle = ref.replace(year=ref.year - 1).strftime("%Y-%m-%d")
            if cle in valeurs:
                points.append((ref, variation_annuelle(valeurs[d], valeurs[cle])))
        if len(points) >= 6:
            log(f"  Sparkline CA (inflation) : {len(points[-12:])} points")
            return points
        log("  Sparkline CA : historique insuffisant")
        return None
    except Exception as e:
        log(f"  ERREUR sparkline inflation CA : {e}")
        return None


def fetch_statcan_vecteur(vecteur, n=14):
    """Points d'un vecteur StatCan, du plus ancien au plus recent."""
    resp = obtenir(STATCAN_WDS, "post",
                   json=[{"vectorId": vecteur, "latestN": n}])
    resp.raise_for_status()
    charge = resp.json()
    if not charge or charge[0].get("status") != "SUCCESS":
        raise RuntimeError(f"reponse WDS inattendue pour {vecteur}")
    points = charge[0]["object"]["vectorDataPoint"]
    return sorted(
        ((p["refPer"], float(p["value"])) for p in points if p.get("value") is not None),
        key=lambda x: x[0],
    )


def fetch_chomage_canada():
    try:
        points = fetch_statcan_vecteur(STATCAN_CHOMAGE, 3)
        if not points:
            log("  ERREUR chomage CA : aucune observation")
            return None
        date_str, valeur = points[-1]
        ref = datetime.strptime(date_str, "%Y-%m-%d")
        log(f"  Chomage CA : {valeur} % ({date_str})")
        return {"value": valeur, "period": periode_fr(ref.year, ref.month)}
    except Exception as e:
        log(f"  ERREUR chomage CA : {e}")
        return None


def fetch_variation_emploi_canada():
    """Variation mensuelle de l'emploi, en milliers.

    Sert au resume : c'est le chiffre que reprend la presse le matin de la
    publication (« +75 100 emplois en juillet »).
    """
    try:
        points = fetch_statcan_vecteur(STATCAN_EMPLOI, 3)
        if len(points) < 2:
            return None
        (_, avant), (date_str, apres) = points[-2], points[-1]
        ref = datetime.strptime(date_str, "%Y-%m-%d")
        variation = round(apres - avant, 1)
        log(f"  Emploi CA : {variation:+.1f} milliers ({date_str})")
        return {"value": variation, "annee": ref.year, "mois": ref.month,
                "period": periode_fr(ref.year, ref.month)}
    except Exception as e:
        log(f"  ERREUR emploi CA : {e}")
        return None


# ============================================================
# ETATS-UNIS — Fed de New York et BLS
# ============================================================

def fetch_taux_directeur_us():
    try:
        resp = obtenir(NYFED_EFFR_URL)
        resp.raise_for_status()
        taux = resp.json()["refRates"][0]
        milieu = (taux["targetRateFrom"] + taux["targetRateTo"]) / 2
        jour = datetime.strptime(taux["effectiveDate"], "%Y-%m-%d")
        log(f"  Taux directeur US : {milieu} % au {taux['effectiveDate']}")
        return {"value": round(milieu, 3),
                "period": periode_fr(jour.year, jour.month)}
    except Exception as e:
        log(f"  ERREUR taux directeur US : {e}")
        return None


def _bls_mensuels(serie):
    """Observations mensuelles d'une serie BLS, indexees par (annee, mois).

    M13 designe une moyenne annuelle qu'il ne faut pas melanger aux mois, et
    le BLS renvoie des entrees vides pour les mois pas encore publies.
    """
    resp = obtenir(BLS_URL.format(serie=serie))
    resp.raise_for_status()
    charge = resp.json()
    if charge.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(charge.get("status", "statut BLS inconnu"))
    mensuels = {}
    for o in charge["Results"]["series"][0]["data"]:
        if not o["period"].startswith("M") or o["period"] == "M13":
            continue
        try:
            mensuels[(int(o["year"]), int(o["period"][1:]))] = float(o["value"])
        except ValueError:
            continue
    return mensuels


def fetch_inflation_us():
    try:
        mensuels = _bls_mensuels(BLS_IPC)
        if not mensuels:
            log("  ERREUR inflation US : aucune observation mensuelle")
            return None
        recent = max(mensuels)
        an_avant = (recent[0] - 1, recent[1])
        if an_avant not in mensuels:
            log(f"  ERREUR inflation US : {an_avant} absent de la serie")
            return None
        taux = variation_annuelle(mensuels[recent], mensuels[an_avant])
        log(f"  Inflation US : {taux} % ({recent[0]}-{recent[1]:02d})")
        return {"value": taux, "period": periode_fr(*recent)}
    except Exception as e:
        log(f"  ERREUR inflation US : {e}")
        return None


def fetch_chomage_us():
    try:
        mensuels = _bls_mensuels(BLS_CHOMAGE)
        if not mensuels:
            log("  ERREUR chomage US : aucune observation")
            return None
        recent = max(mensuels)
        log(f"  Chomage US : {mensuels[recent]} % ({recent[0]}-{recent[1]:02d})")
        return {"value": mensuels[recent], "period": periode_fr(*recent)}
    except Exception as e:
        log(f"  ERREUR chomage US : {e}")
        return None


def fetch_variation_emploi_us():
    """Variation mensuelle de l'emploi non agricole, en milliers."""
    try:
        mensuels = _bls_mensuels(BLS_EMPLOI)
        if len(mensuels) < 2:
            return None
        recent = max(mensuels)
        precedent = (recent[0], recent[1] - 1) if recent[1] > 1 else (recent[0] - 1, 12)
        if precedent not in mensuels:
            return None
        variation = round(mensuels[recent] - mensuels[precedent], 1)
        log(f"  Emploi US : {variation:+.1f} milliers ({recent[0]}-{recent[1]:02d})")
        return {"value": variation, "annee": recent[0], "mois": recent[1],
                "period": periode_fr(*recent)}
    except Exception as e:
        log(f"  ERREUR emploi US : {e}")
        return None


# ============================================================
# APPLICATION ET FRAICHEUR
# ============================================================

def appliquer(indicateur, mesure, source):
    """Ecrit une mesure fraiche dans un indicateur, tendance comprise."""
    if not mesure:
        return False
    ancienne = indicateur.get("value")
    indicateur["value"] = mesure["value"]
    if isinstance(ancienne, (int, float)):
        if mesure["value"] > ancienne:
            indicateur["trend"] = "up"
        elif mesure["value"] < ancienne:
            indicateur["trend"] = "down"
        else:
            indicateur["trend"] = "stable"
    indicateur["period"] = mesure["period"]
    indicateur["source"] = source
    indicateur["manual"] = False
    return True


def creer_ou_appliquer(indicateurs, cle, mesure, source, unit, nom_fr, nom_en):
    """Comme appliquer(), mais cree l'indicateur s'il n'existe pas encore."""
    if cle not in indicateurs:
        if not mesure:
            return False
        indicateurs[cle] = {"value": None, "unit": unit, "trend": "stable",
                            "period": "", "source": source,
                            "label": {"fr": nom_fr, "en": nom_en}}
    return appliquer(indicateurs[cle], mesure, source)


def age_en_jours(periode):
    """Age d'un libelle de periode, ou None s'il ne designe pas une date.

    « 2026F », « FY26F » et « 2026 cible » sont des previsions : elles n'ont
    pas d'age a mesurer et ne doivent pas declencher d'alerte.
    """
    if not isinstance(periode, str) or not periode.strip():
        return None
    texte = periode.strip()
    aujourdhui = datetime.now()

    try:
        return (aujourdhui - datetime.strptime(texte, "%Y-%m-%d")).days
    except ValueError:
        pass

    morceaux = texte.split()
    if len(morceaux) == 2:
        numero = numero_mois(morceaux[0])
        if numero:
            try:
                reference = datetime(int(morceaux[1]), numero, 1)
            except ValueError:
                return None
            return (aujourdhui - reference).days
    return None


def ajouter_periodes_anglaises(data):
    """Double chaque libelle de periode d'une version anglaise.

    Le site se dit bilingue, mais les cartes affichaient « Juill. 2026 » meme
    en anglais. Les periodes sont produites en francais par le pipeline : on
    les traduit une fois, a l'ecriture, plutot qu'a chaque rendu.
    """
    for contenu in data["regions"].values():
        for ind in contenu.get("indicators", {}).values():
            periode = ind.get("period")
            if isinstance(periode, str) and periode.strip():
                ind["periodEn"] = periode_en(periode)


def _substituer_marqueurs(gabarit, brent, cad, inr):
    """Remplace {{brent}}, {{cad}} et {{inr}} par les valeurs vivantes du jour.

    Six marqueurs et non trois : le francais separe ses milliers par une
    espace insecable et decime par une virgule, l'anglais fait l'inverse. Le
    huard et la roupie gardent leurs deux decimales, la ou nombre_fr()
    laisserait « 1,4 » pour un taux qui s'ecrit « 1,40 ».

    Leve une erreur si un marqueur reste non substitue : mieux vaut garder
    l'ancienne version d'un fichier editorial que publier un « {{brent}} »
    litteral.
    """
    rendu = (gabarit
             .replace("{{brent}}", nombre_fr(round(float(brent))))
             .replace("{{brentEn}}", f"{round(float(brent)):,}")
             .replace("{{cad}}", f"{float(cad):.2f}".replace(".", ","))
             .replace("{{cadEn}}", f"{float(cad):.2f}"))
    if inr is not None:
        rendu = (rendu
                 .replace("{{inr}}", f"{float(inr):.2f}".replace(".", ","))
                 .replace("{{inrEn}}", f"{float(inr):.2f}"))
    if "{{" in rendu:
        raise ValueError("marqueur non substitue dans le gabarit")
    return rendu


def poser_contenu_editorial(data):
    """Recopie la chronologie, la matrice provinciale et les interconnexions
    depuis leurs gabarits.

    Le texte annoncait « Brent a 90 $ » et « 1,38 CAD/USD » longtemps apres
    que le baril soit passe par 118 $ puis 70 $ et que le huard soit tombe a
    1,40 : un chiffre ecrit en dur dans une analyse ne vieillit pas
    visiblement, il devient simplement faux. Meme logique pour les
    interconnexions : l'onglet datait de mars et decrivait Ormuz comme ferme
    sans interruption, une roupie a 92,54/USD comme un record encore valide,
    et une inflation indienne projetee a 4,5 % que l'OCDE dementait deja.
    """
    log("Contenu editorial...")

    try:
        with open(CHRONO_FILE, encoding="utf-8") as f:
            evenements = json.load(f)["evenements"]
        # Le site attend des entrees sans le champ `source`, qui ne sert qu'a
        # rendre chaque ligne verifiable dans le depot.
        data["timeline"] = [
            {c: e[c] for c in ("date", "title", "regions", "theme")}
            for e in sorted(evenements, key=lambda e: e["date"])
        ]
        log(f"  Chronologie : {len(data['timeline'])} evenements, "
            f"du {data['timeline'][0]['date']} au {data['timeline'][-1]['date']}")
    except Exception as e:
        log(f"  ERREUR chronologie : {e}, ancienne version conservee")

    brent = (data["regions"]["WORLD"]["sparkline"]["data"] or [None])[-1]
    cad = data["regions"]["CA"]["indicators"]["exchange"].get("value")
    inr = data["regions"]["IN"]["indicators"]["exchange"].get("value")
    if brent is None or cad is None:
        log("  Brent ou huard indisponible, contenu vivant inchange")
        return

    try:
        with open(ANALYSE_FILE, encoding="utf-8") as f:
            gabarit = json.dumps(json.load(f)["provincialAnalysis"],
                                 ensure_ascii=False)
        rendu = _substituer_marqueurs(gabarit, brent, cad, inr)
        data["regions"]["CA"]["provincialAnalysis"] = json.loads(rendu)
        log(f"  Matrice provinciale : Brent {round(float(brent))} $, "
            f"huard {round(float(cad), 2)}")
    except Exception as e:
        log(f"  ERREUR matrice provinciale : {e}, ancienne version conservee")

    try:
        with open(INTERCO_FILE, encoding="utf-8") as f:
            liens = json.load(f)["interconnections"]
        gabarit = json.dumps(liens, ensure_ascii=False)
        rendu = _substituer_marqueurs(gabarit, brent, cad, inr)
        data["interconnections"] = [
            {c: e[c] for c in ("from", "to", "type", "title", "description", "impact")}
            for e in json.loads(rendu)
        ]
        log(f"  Interconnexions : {len(data['interconnections'])} liens")
    except Exception as e:
        log(f"  ERREUR interconnexions : {e}, ancienne version conservee")


def controler_fraicheur(data, seuil_jours=100):
    """Liste les indicateurs devenus trop vieux. Retourne les manquements."""
    log(f"Controle de fraicheur (seuil : {seuil_jours} jours)...")
    perimes = []
    for region, contenu in data["regions"].items():
        for nom, ind in contenu.get("indicators", {}).items():
            age = age_en_jours(ind.get("period"))
            if age is not None and age > seuil_jours:
                perimes.append(f"{region}.{nom} = {ind.get('period')} ({age} j)")
                log(f"  PERIME {region}.{nom} : {ind.get('period')} ({age} jours)")
    if not perimes:
        log("  Aucun indicateur au-dela du seuil.")
    else:
        log(f"  {len(perimes)} indicateur(s) a rafraichir a la main "
            f"(voir MISE_A_JOUR_MANUELLE.md).")
    return perimes


# ============================================================
# CONTROLE DE COHERENCE — chaque valeur face a une seconde source
# ============================================================
#
# Un pipeline qui ne lit qu'une source par indicateur ne peut pas distinguer
# une vraie donnee d'une erreur de lecture qui ressemble a une vraie donnee :
# une colonne SDMX mal alignee, un decalage d'index, une conversion d'unite
# oubliee rendent tous un nombre plausible en apparence. Ce controle relit
# les indicateurs qui ont une seconde source publique independante et
# signale l'ecart plutot que de le publier en silence. Ceux qui n'en ont pas
# passent par une borne de plausibilite a la place : ca n'attrape pas une
# petite erreur, mais ca attrape un chiffre qui a change de colonne ou
# d'unite.

SEUIL_ECART_INFLATION = 0.5   # points de pourcentage
SEUIL_ECART_TAUX = 0.25       # points de pourcentage
SEUIL_ECART_CHANGE = 0.03     # relatif (3 %)

BORNES_PLAUSIBLES = {
    "inflation": (-5, 30),
    "rate": (0, 20),
    "unemployment": (1, 40),
    "gdp": (-15, 20),
}


def comparer_sources(nom, valeur_a, source_a, valeur_b, source_b, seuil, relatif=False):
    """Compare deux lectures independantes du meme indicateur.

    None si l'une des deux valeurs manque : une source secondaire
    indisponible n'est pas un desaccord, juste un controle qui n'a pas pu
    avoir lieu.
    """
    if valeur_a is None or valeur_b is None:
        return None
    ecart = abs(float(valeur_a) - float(valeur_b))
    ecart_mesure = ecart / abs(float(valeur_b)) if relatif and valeur_b else ecart
    suspect = ecart_mesure > seuil
    if suspect:
        log(f"  ECART {nom} : {source_a}={valeur_a} vs {source_b}={valeur_b}")
    return {"indicateur": nom, "type": "source_double",
            "sourceA": source_a, "valeurA": valeur_a,
            "sourceB": source_b, "valeurB": valeur_b,
            "ecart": round(ecart_mesure, 4), "suspect": suspect}


def verifier_borne(nom, valeur, source, cle_borne):
    """Signale une valeur hors de toute plausibilite, faute de seconde source.

    N'attrape pas une petite erreur de lecture, seulement un chiffre qui a
    change de colonne ou d'unite (un indice pris pour un taux, par exemple).
    """
    if valeur is None:
        return None
    mini, maxi = BORNES_PLAUSIBLES[cle_borne]
    suspect = not (mini <= float(valeur) <= maxi)
    if suspect:
        log(f"  HORS BORNES {nom} : {valeur} ({source}), attendu [{mini}, {maxi}]")
    return {"indicateur": nom, "type": "borne_plausibilite",
            "sourceA": source, "valeurA": valeur,
            "sourceB": None, "valeurB": f"[{mini}, {maxi}]",
            "ecart": None, "suspect": suspect}


# ============================================================
# CHINE ET INDE — OCDE (prix) et BRI (taux directeurs)
# ============================================================
#
# Ces deux blocs remplacent la saisie manuelle. Avant leur mise en place,
# l'IPC de l'Inde affiche sur le site datait de janvier 2026 (2,7 %) alors
# que la serie de l'OCDE donnait 4,76 % pour juin : ce n'etait pas un retard
# d'affichage, c'etait un chiffre faux de deux points.
#
# Les deux API parlent SDMX et savent rendre du CSV a plat, ce qui evite
# d'avoir a demeler l'indexation par position du JSON SDMX.

def lire_csv_sdmx(texte):
    """Extrait les couples (periode, valeur) d'une reponse SDMX en CSV.

    Les deux entrepots exposent les memes colonnes TIME_PERIOD et OBS_VALUE
    au milieu de metadonnees differentes. On ne lit que ces deux-la, triees
    du plus ancien au plus recent.
    """
    lignes = csv.DictReader(io.StringIO(texte))
    points = []
    for ligne in lignes:
        periode = (ligne.get("TIME_PERIOD") or "").strip()
        brut = (ligne.get("OBS_VALUE") or "").strip()
        if not periode or not brut:
            continue
        try:
            points.append((periode, float(brut)))
        except ValueError:
            continue
    return sorted(points, key=lambda x: x[0])


def _periode_ocde(jeton):
    """« 2026-06 » vers un couple (annee, mois)."""
    annee, mois = jeton.split("-")[:2]
    return int(annee), int(mois)


def fetch_inflation_ocde(pays, libelle, n=18):
    """Inflation annuelle d'un pays chez l'OCDE, en points de pourcentage."""
    try:
        resp = obtenir(OCDE_PRIX.format(pays=pays, n=n))
        resp.raise_for_status()
        points = lire_csv_sdmx(resp.text)
        if not points:
            log(f"  ERREUR inflation {libelle} : aucune observation OCDE")
            return None, None
        periode, valeur = points[-1]
        annee, mois = _periode_ocde(periode)
        log(f"  Inflation {libelle} : {round(valeur, 1)} % ({periode}, OCDE)")
        mesure = {"value": round(valeur, 1),
                  "period": periode_fr(annee, mois)}
        serie = [(datetime(*_periode_ocde(p), 1), round(v, 1))
                 for p, v in points]
        return mesure, serie
    except Exception as e:
        log(f"  ERREUR inflation {libelle} : {e}")
        return None, None


def fetch_taux_directeur_bri(pays, libelle):
    """Taux directeur officiel chez la BRI.

    La serie quotidienne est essayee d'abord : elle devance la mensuelle de
    plusieurs semaines. La mensuelle sert de repli si la premiere ne rend
    rien, pour ne pas dependre d'un seul point de defaillance.
    """
    for freq, n in (("D", 40), ("M", 6)):
        try:
            resp = obtenir(BRI_TAUX.format(freq=freq, pays=pays, n=n))
            resp.raise_for_status()
            points = lire_csv_sdmx(resp.text)
            if not points:
                continue
            periode, valeur = points[-1]
            annee, mois = _periode_ocde(periode)
            log(f"  Taux directeur {libelle} : {valeur} % "
                f"({periode}, BRI {freq})")
            return {"value": round(valeur, 3),
                    "period": periode_fr(annee, mois)}
        except Exception as e:
            log(f"  ERREUR taux directeur {libelle} ({freq}) : {e}")
    return None


# ============================================================
# TAUX DE CHANGE ET BOURSES
# ============================================================

def fetch_exchange_rates():
    log("Recuperation des taux de change...")
    try:
        resp = obtenir(EXCHANGE_RATES_URL)
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates", {})
        log(f"  CAD={rates.get('CAD')} CNY={rates.get('CNY')} INR={rates.get('INR')}")
        return {"CAD": rates.get("CAD"), "CNY": rates.get("CNY"),
                "INR": rates.get("INR"), "date": data.get("date", "")}
    except Exception as e:
        log(f"  ERREUR taux de change : {e}")
        return None


def fetch_stock_quote(symbol):
    try:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
               f"?interval=1d&range=1d")
        resp = obtenir(url)
        resp.raise_for_status()
        meta = resp.json()["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev = meta.get("previousClose") or meta.get("chartPreviousClose", 0)
        change = round((price - prev) / prev * 100, 2) if prev else 0
        trend = "up" if change > 0.1 else ("down" if change < -0.1 else "stable")
        return {"value": round(price), "change": change, "trend": trend}
    except Exception as e:
        log(f"  ERREUR Yahoo Finance ({symbol}) : {e}")
        return None


def fetch_taux_change_yahoo(ticker):
    """Cotation d'une paire de change chez Yahoo, en seconde source du taux
    de change Frankfurter/BCE. fetch_stock_quote() arrondit a l'entier, ce
    qui efface un huard a 1,40 ; ce prix-ci garde ses decimales."""
    try:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
               f"?interval=1d&range=1d")
        resp = obtenir(url)
        resp.raise_for_status()
        prix = resp.json()["chart"]["result"][0]["meta"].get("regularMarketPrice")
        return round(prix, 4) if prix else None
    except Exception as e:
        log(f"  ERREUR Yahoo Finance ({ticker}) : {e}")
        return None


def fetch_all_stocks():
    log("Recuperation des indices boursiers...")
    results = {}
    for region, symbol in STOCK_SYMBOLS.items():
        quote = fetch_stock_quote(symbol)
        if quote:
            log(f"  {region} ({symbol}) : {quote['value']} ({quote['change']:+.2f} %)")
            results[region] = quote
        time.sleep(0.4)
    return results


def etiquettes_mois(dates):
    """Libelles bilingues courts pour l'axe d'une sparkline."""
    return [{"fr": MOIS_FR[d.month - 1].rstrip("."),
             "en": MOIS_EN[d.month - 1].rstrip(".")} for d in dates]


def fetch_sparkline_data(symbol, interval="1mo", range_str="1y"):
    """Serie mensuelle et ses dates reelles.

    Les dates comptent autant que les valeurs : l'axe du graphique etait
    etiquete « Avr » a « Mar » en dur, une fenetre figee au lancement du
    projet en mars 2026 qui ne correspondait plus aux points traces.
    """
    try:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
               f"?interval={interval}&range={range_str}")
        resp = obtenir(url)
        resp.raise_for_status()
        resultat = resp.json()["chart"]["result"][0]
        closes = resultat["indicators"]["quote"][0]["close"]
        horodatages = resultat.get("timestamp", [])
        points = []
        for valeur, ts in zip(closes, horodatages):
            if valeur is None:
                continue
            points.append((datetime.fromtimestamp(ts, tz=timezone.utc),
                           round(valeur, 2)))
        return points
    except Exception as e:
        log(f"  ERREUR sparkline ({symbol}) : {e}")
        return None


def poser_sparkline(region_data, points, libelle=None):
    """Ecrit valeurs et etiquettes d'une sparkline a partir de (date, valeur).

    Yahoo renvoie le mois en cours deux fois — une fois comme dernier seau
    mensuel clos, une fois comme cotation vivante — ce qui donnait un axe
    finissant par « Août Août ». On ne garde qu'un point par mois, le plus
    recent.
    """
    if not points or len(points) < 6:
        return False
    par_mois = {}
    for date, valeur in points:
        par_mois[(date.year, date.month)] = (date, valeur)
    points = [par_mois[cle] for cle in sorted(par_mois)]
    derniers = points[-12:]
    region_data["sparkline"]["data"] = [v for _, v in derniers]
    region_data["sparkline"]["labels"] = etiquettes_mois([d for d, _ in derniers])
    if libelle:
        region_data["sparkline"]["label"] = libelle
    return True


def fetch_exchange_sparkline(from_currency, to_currency):
    """Un point de change par mois, avec sa date."""
    try:
        end = datetime.now()
        start = end - timedelta(days=365)
        url = (f"https://api.frankfurter.app/{start.strftime('%Y-%m-%d')}"
               f"..{end.strftime('%Y-%m-%d')}?from={from_currency}&to={to_currency}")
        resp = obtenir(url)
        resp.raise_for_status()
        rates = resp.json().get("rates", {})
        points, dernier_mois = [], None
        for d in sorted(rates):
            if d[:7] != dernier_mois:
                points.append((datetime.strptime(d, "%Y-%m-%d"),
                               rates[d][to_currency]))
                dernier_mois = d[:7]
        return points
    except Exception as e:
        log(f"  ERREUR sparkline FX ({from_currency}/{to_currency}) : {e}")
        return None


# ============================================================
# ACTUALITES
# ============================================================

def charger_flux(url):
    """Telecharge puis parse un flux.

    feedparser.parse(url) fait la requete lui-meme et n'accepte aucun
    timeout : un serveur qui ne repond jamais bloquait le workflow entier.
    On passe par requests, qui en a un.
    """
    resp = obtenir(url)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def horodatage(published_parsed):
    if not published_parsed:
        return None
    try:
        return datetime(*published_parsed[:6], tzinfo=timezone.utc)
    except Exception:
        return None


def temps_relatif(moment):
    if not moment:
        return "?"
    heures = (datetime.now(timezone.utc) - moment).total_seconds() / 3600
    if heures < 1:
        return "<1h"
    if heures < 24:
        return f"{int(heures)}h"
    if heures < 168:
        return f"{int(heures / 24)}j"
    return f"{int(heures / 168)}s"


MOTS_VIDES = {
    "the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "as",
    "is", "are", "with", "at", "by", "from", "its", "it", "that", "this",
    "says", "say", "said", "will", "may", "be", "not", "but", "over",
    "le", "la", "les", "des", "du", "de", "un", "une", "et", "ou", "en",
    "dans", "sur", "pour", "par", "au", "aux", "que", "qui", "est", "sont",
}


def mots_significatifs(titre):
    """Vocabulaire porteur d'un titre, pour comparer deux depeches."""
    mots = re.findall(r"[a-z0-9]+", normaliser(titre))
    return {m for m in mots if len(m) > 2 and m not in MOTS_VIDES}


def similarite(a, b):
    """Indice de Jaccard entre deux ensembles de mots."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def estimer_impact(titre, score):
    """L'impact suit le score du filtre, releve par un vocabulaire de rupture."""
    fort = ["crisis", "crise", "war", "guerre", "crash", "collapse",
            "recession", "record", "surge", "flambee", "plunge", "chute",
            "emergency", "urgence", "sanction", "tariff", "tarif", "ban",
            "shutdown", "default", "defaut"]
    bas = titre.lower()
    if score >= 8 or any(w in bas for w in fort):
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def charger_sante_flux():
    """Etat de sante des flux au dernier passage, ou vide si absent."""
    try:
        with open(SANTE_FLUX_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def noter_flux(url, nom, ok):
    """Enregistre un succes ou un echec pour un flux.

    Le compteur d'echecs consecutifs repart a zero au premier succes : une
    panne passagere (un 503, un timeout) ne doit pas s'additionner
    indefiniment avec la precedente si le flux repond entre-temps.
    """
    entree = SANTE_FLUX.setdefault(url, {"nom": nom, "echecsConsecutifs": 0,
                                         "dernierSucces": None})
    if nom:
        entree["nom"] = nom
    if ok:
        entree["echecsConsecutifs"] = 0
        entree["dernierSucces"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        entree["echecsConsecutifs"] = entree.get("echecsConsecutifs", 0) + 1


def flux_en_panne():
    """Flux dont les echecs consecutifs depassent le seuil."""
    return [
        {"url": url, "nom": e.get("nom") or url,
         "echecsConsecutifs": e["echecsConsecutifs"],
         "dernierSucces": e.get("dernierSucces")}
        for url, e in SANTE_FLUX.items()
        if e.get("echecsConsecutifs", 0) >= SEUIL_FLUX_EN_PANNE
    ]


def recuperer_actualites(region, langue="en"):
    """Actualites filtrees d'une region, les plus recentes d'abord.

    `langue` choisit le jeu de flux : anglophone ou francophone. Le filtre est
    le meme dans les deux cas, ses listes de mots-cles etant deja bilingues et
    insensibles aux accents.
    """
    flux_region = (RSS_FEEDS if langue == "en" else RSS_FEEDS_FR).get(region, [])
    retenues, rejetees, vus_urls = [], [], set()

    for url_flux, nom_source in flux_region:
        try:
            flux = charger_flux(url_flux)
            noter_flux(url_flux, nom_source, True)
        except Exception as e:
            log(f"    flux indisponible ({nom_source or 'Google News'}) : "
                f"{type(e).__name__}")
            noter_flux(url_flux, nom_source, False)
            continue

        for entree in flux.entries[:40]:
            brut = entree.get("title", "")
            lien = entree.get("link", "")
            if not brut or not lien or lien in vus_urls:
                continue

            # Google News expose l'editeur reel et suffixe ses titres.
            source = nom_source or (entree.get("source") or {}).get("title")
            titre = nettoyer_titre(brut, source)

            # Les rubriques choisies a la main sont fiables par construction.
            # Ce qui remonte d'une requete doit prouver son editeur.
            if nom_source is None and not source_fiable(source):
                rejetees.append((titre, f"source hors liste : {source}"))
                continue
            source = joli_editeur(source) or "Google News"

            verdict = evaluer(titre)
            if not verdict["accepte"]:
                rejetees.append((titre, verdict["motif"]))
                continue

            # Une redaction nationale ou un flux economique generaliste
            # couvre aussi l'etranger : un article de la CBC sur des centres
            # de donnees au Texas s'est deja retrouve sous l'onglet Canada
            # faute de le verifier. Verifie apres le filtre thematique, pour
            # que le motif de rejet d'un hors-sujet reste « hors sujet » et
            # non « hors zone ». Exempte : l'institution propre a la region
            # (elle parle d'elle-meme) et RESTE DU MONDE (rien a prouver).
            if (nom_source is not None and region != "WORLD"
                    and url_flux not in FLUX_EXEMPTS_ZONE
                    and not zone_mentionnee(titre, region)):
                rejetees.append((titre, f"hors zone {region} : mentionne une autre zone"))
                continue

            vus_urls.add(lien)
            moment = horodatage(entree.get("published_parsed"))
            retenues.append({
                "titre": titre,
                "url": lien,
                "source": source,
                "moment": moment,
                "theme": verdict["theme"],
                "score": verdict["score"],
                "impact": estimer_impact(titre, verdict["score"]),
            })

    # Deduplication par recouvrement de vocabulaire. Comparer les 45 premiers
    # caracteres ne suffisait pas : « America hurting its own interest... »
    # (Economic Times) et « "America is actually hurting its own interest"... »
    # (ANI) sont la meme depeche sous deux angles de citation.
    retenues.sort(key=lambda x: x["moment"] or datetime.min.replace(tzinfo=timezone.utc),
                  reverse=True)

    # Le classement par pure fraicheur faisait perdre l'analyse contre la
    # depeche : le Financial Times et The Economist passaient le filtre chaque
    # jour, une dizaine de titres chacun, et n'apparaissaient jamais, battus
    # par des fils d'agence publies quelques heures plus tard. Une veille
    # geoeconomique qui n'affiche jamais ces deux titres rate sa cible.
    #
    # On reserve donc jusqu'a trois des huit places aux sources d'analyse,
    # servies elles aussi par ordre de fraicheur. Les cinq autres restent
    # attribuees au plus recent, toutes sources confondues.
    uniques, empreintes, par_source = [], [], {}

    def tenter(item):
        empreinte = mots_significatifs(item["titre"])
        if any(similarite(empreinte, e) > 0.45 for e in empreintes):
            return False
        if par_source.get(item["source"], 0) >= MAX_PAR_SOURCE:
            return False
        empreintes.append(empreinte)
        par_source[item["source"]] = par_source.get(item["source"], 0) + 1
        uniques.append(item)
        return True

    for item in retenues:
        if len(uniques) >= PLACES_ANALYSE:
            break
        if normaliser(item["source"]) in SOURCES_ANALYSE:
            tenter(item)

    for item in retenues:
        if len(uniques) >= MAX_HEADLINES:
            break
        if item not in uniques:
            tenter(item)

    log(f"  {region} ({langue}) : {len(uniques)} retenues, "
        f"{len(rejetees)} ecartees")
    for titre, motif in rejetees[:4]:
        log(f"      ecarte — {titre[:58]} [{motif[:38]}]")

    # Les rejets alimentent le rapport hebdomadaire. Un filtre qui ne rend
    # jamais compte de ce qu'il coupe finit par couper des choses justes sans
    # que personne ne s'en apercoive.
    for titre, motif in rejetees:
        JOURNAL_REJETS.append({"region": region, "langue": langue,
                               "titre": titre, "motif": motif})
    return uniques


def formater_actualites(items):
    sorties = []
    for e in items:
        sorties.append({
            "title": {"fr": e["titre"], "en": e["titre"]},
            "url": e["url"],
            "theme": e["theme"],
            "time": temps_relatif(e["moment"]),
            "publishedAt": e["moment"].isoformat() if e["moment"] else None,
            "impact": e["impact"],
            "source": e["source"],
        })
    return sorties


# ============================================================
# RESUMES ET SENTIMENT — composes, jamais rediges d'avance
# ============================================================

THEMES_FR = {"trade": "commerce", "monetary": "politique monétaire",
             "energy": "énergie", "tech": "technologie",
             "geopolitics": "géopolitique"}
THEMES_EN = {"trade": "trade", "monetary": "monetary policy",
             "energy": "energy", "tech": "technology",
             "geopolitics": "geopolitics"}

NOMS_REGIONS = {
    "CA": ("L'économie canadienne", "The Canadian economy"),
    "US": ("L'économie américaine", "The US economy"),
    "CN": ("L'économie chinoise", "The Chinese economy"),
    "IN": ("L'économie indienne", "The Indian economy"),
    "WORLD": ("L'économie mondiale", "The global economy"),
}


def periode_en(periode):
    """« Juill. 2026 » devient « July 2026 ».

    Les libelles de prevision (« 2026F », « FY26F », « 2026 cible ») ne
    designent pas un mois : seul « cible » est traduit.
    """
    if not isinstance(periode, str) or not periode.strip():
        return periode
    morceaux = periode.strip().split()
    if len(morceaux) == 2:
        numero = numero_mois(morceaux[0])
        if numero:
            return f"{MOIS_EN[numero - 1]} {morceaux[1]}"
    return periode.replace("cible", "target")


def est_mois(periode):
    """Vrai si le libelle designe un mois, donc s'il se met en minuscules."""
    morceaux = str(periode).strip().split()
    return len(morceaux) == 2 and numero_mois(morceaux[0]) is not None


def en_minuscules(periode):
    """« Juin 2026 » devient « juin 2026 » ; « 2026F » reste « 2026F »."""
    return str(periode).lower() if est_mois(periode) else str(periode)


def nombre_fr(x):
    """Espace insecable comme separateur de milliers, virgule decimale."""
    if isinstance(x, float) and not x.is_integer():
        entier, decimale = f"{abs(x):.1f}".split(".")
        signe = "-" if x < 0 else ""
        return f"{signe}{int(entier):,}".replace(",", " ") + f",{decimale}"
    return f"{int(x):,}".replace(",", " ")


def phrase_emploi(emploi, chomage, langue):
    """« +75 100 emplois en juillet, chômage à 6,4 % »."""
    if not emploi and not chomage:
        return None
    bouts = []
    if emploi:
        milliers = emploi["value"]
        postes = int(round(milliers * 1000))
        mois = MOIS_FR_LONG[emploi["mois"] - 1]
        if langue == "fr":
            verbe = "a créé" if milliers >= 0 else "a perdu"
            bouts.append(f"{verbe} {nombre_fr(abs(postes))} emplois en {mois}")
        else:
            verbe = "added" if milliers >= 0 else "shed"
            bouts.append(f"{verbe} {abs(postes):,} jobs in "
                         f"{datetime(2000, emploi['mois'], 1).strftime('%B')}")
    if chomage:
        if langue == "fr":
            taux = str(chomage["value"]).replace(".", ",")
            bouts.append(f"le taux de chômage s'établit à {taux} % "
                         f"({en_minuscules(chomage['period'])})")
        else:
            bouts.append(f"unemployment stands at {chomage['value']}% "
                         f"({periode_en(chomage['period'])})")
    return ", ".join(bouts)


def composer_resume(region, indicateurs, actualites, emploi, chomage):
    """Un resume de trois a quatre phrases, entierement derive des donnees."""
    nom_fr, nom_en = NOMS_REGIONS[region]
    fr, en = [], []

    def val(cle):
        ind = indicateurs.get(cle) or {}
        return ind.get("value"), ind.get("period", "")

    pib, pib_per = val("gdp")
    infl, infl_per = val("inflation")
    taux, taux_per = val("rate")
    bourse = indicateurs.get("stockIndex") or {}

    # 1. Activite
    emploi_fr = phrase_emploi(emploi, chomage, "fr")
    emploi_en = phrase_emploi(emploi, chomage, "en")
    if emploi_fr:
        fr.append(f"{nom_fr} {emploi_fr}.")
        en.append(f"{nom_en} {emploi_en}.")
    elif pib is not None:
        fr.append(f"{nom_fr} progresse à un rythme de "
                  f"{str(pib).replace('.', ',')} % ({pib_per}).")
        en.append(f"{nom_en} is growing at {pib}% ({periode_en(pib_per)}).")

    # 2. Prix et taux
    if infl is not None and taux is not None:
        fr.append(f"L'inflation ressort à {str(infl).replace('.', ',')} % "
                  f"({en_minuscules(infl_per)}) pour un taux directeur de "
                  f"{str(taux).replace('.', ',')} % ({en_minuscules(taux_per)}).")
        en.append(f"Inflation is {infl}% ({periode_en(infl_per)}) against a "
                  f"policy rate of {taux}% ({periode_en(taux_per)}).")
    elif infl is not None:
        fr.append(f"L'inflation ressort à {str(infl).replace('.', ',')} % "
                  f"({en_minuscules(infl_per)}).")
        en.append(f"Inflation is {infl}% ({periode_en(infl_per)}).")

    # 3. Marches
    if bourse.get("value") and bourse.get("change") is not None:
        nom_indice = bourse.get("name", "L'indice de référence")
        variation = bourse["change"]
        sens_fr = "gagne" if variation >= 0 else "cède"
        sens_en = "is up" if variation >= 0 else "is down"
        fr.append(f"{nom_indice} {sens_fr} "
                  f"{str(abs(variation)).replace('.', ',')} % sur la séance.")
        en.append(f"{nom_indice} {sens_en} {abs(variation)}% on the session.")

    # 4. Ce que dit l'actualite du jour
    if actualites:
        comptes = {}
        for a in actualites:
            comptes[a["theme"]] = comptes.get(a["theme"], 0) + 1
        dominant = max(comptes, key=comptes.get)
        n = comptes[dominant]
        fr.append(f"Sur les {len(actualites)} nouvelles retenues aujourd'hui, "
                  f"{n} relèvent du thème « {THEMES_FR[dominant]} ».")
        en.append(f"Of the {len(actualites)} stories retained today, {n} fall "
                  f"under {THEMES_EN[dominant]}.")

    return {"fr": " ".join(fr), "en": " ".join(en)}


def calculer_sentiment(region, indicateurs, emploi, chomage, chomage_precedent):
    """Sentiment derive de regles explicites, pas d'une appreciation figee."""
    points, raisons_fr, raisons_en = 0, [], []

    # Fourchette de maitrise de l'inflation plutot qu'une cible ponctuelle :
    # la Banque du Canada et la Fed visent 2 % dans une bande de 1 a 3 %, la
    # RBI vise 4 % dans une bande de 2 a 6 %. Juger l'Inde a 2,7 % « en risque
    # deflationniste » etait un artefact de la cible ponctuelle.
    bande = {"CA": (1.0, 3.0), "US": (1.0, 3.0), "CN": (0.5, 3.0),
             "IN": (2.0, 6.0), "WORLD": (2.0, 4.0)}[region]
    infl = (indicateurs.get("inflation") or {}).get("value")
    if isinstance(infl, (int, float)):
        bas, haut = bande
        if infl > haut:
            points -= 1
            raisons_fr.append(f"inflation à {str(infl).replace('.', ',')} %, "
                              f"au-dessus de la fourchette")
            raisons_en.append(f"inflation at {infl}%, above the target band")
        elif infl < bas:
            points -= 1
            raisons_fr.append(f"inflation à {str(infl).replace('.', ',')} %, "
                              f"risque déflationniste")
            raisons_en.append(f"inflation at {infl}%, deflation risk")
        else:
            points += 1
            raisons_fr.append("inflation dans la fourchette cible")
            raisons_en.append("inflation within the target band")

    if emploi:
        if emploi["value"] > 0:
            points += 1
            raisons_fr.append("emploi en hausse")
            raisons_en.append("employment rising")
        else:
            points -= 1
            raisons_fr.append("emploi en recul")
            raisons_en.append("employment falling")

    if chomage and isinstance(chomage_precedent, (int, float)):
        if chomage["value"] > chomage_precedent:
            points -= 1
            raisons_fr.append("chômage en hausse")
            raisons_en.append("unemployment rising")
        elif chomage["value"] < chomage_precedent:
            points += 1
            raisons_fr.append("chômage en baisse")
            raisons_en.append("unemployment falling")

    pib = (indicateurs.get("gdp") or {}).get("value")
    if isinstance(pib, (int, float)):
        seuil = 5.0 if region in ("CN", "IN") else 1.5
        if pib >= seuil:
            points += 1
            raisons_fr.append(f"croissance de {str(pib).replace('.', ',')} %")
            raisons_en.append(f"growth of {pib}%")
        else:
            points -= 1
            raisons_fr.append(f"croissance faible ({str(pib).replace('.', ',')} %)")
            raisons_en.append(f"weak growth ({pib}%)")

    if points >= 2:
        valeur, label_fr, label_en = "positive", "Positif", "Positive"
    elif points <= -2:
        valeur, label_fr, label_en = "negative", "Négatif", "Negative"
    else:
        valeur, label_fr, label_en = "neutral", "Neutre", "Neutral"

    return {
        "value": valeur,
        "label": {"fr": label_fr, "en": label_en},
        "reason": {"fr": ", ".join(raisons_fr) or "données insuffisantes",
                   "en": ", ".join(raisons_en) or "insufficient data"},
    }


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def update_indicators():
    log("=" * 60)
    log("GeoEcon Pulse — Mise a jour des donnees")
    log("=" * 60)

    if not DATA_FILE.exists():
        log(f"ERREUR : {DATA_FILE} introuvable")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    data["lastUpdated"] = today

    SANTE_FLUX.update(charger_sante_flux())
    verifications = []

    # --- Taux de change ---
    fx = fetch_exchange_rates()
    if fx:
        for region, devise, arrondi in (("CA", "CAD", 3), ("CN", "CNY", 3),
                                        ("IN", "INR", 2)):
            if fx.get(devise):
                appliquer(data["regions"][region]["indicators"]["exchange"],
                          {"value": round(fx[devise], arrondi), "period": fx["date"]},
                          "Frankfurter/BCE")

    # Seconde source des taux de change : Yahoo Finance, qui lit les paires
    # de change comme des cotations boursières. Un ecart ici trahit plus
    # souvent une devise mal alignee dans la reponse Frankfurter qu'un vrai
    # desaccord de marche.
    for region, devise, ticker in (("CA", "CAD", "CAD=X"), ("CN", "CNY", "CNY=X"),
                                   ("IN", "INR", "INR=X")):
        if fx and fx.get(devise):
            secours = fetch_taux_change_yahoo(ticker)
            verifications.append(comparer_sources(
                f"Taux de change {region}", fx[devise], "Frankfurter/BCE",
                secours, "Yahoo Finance", SEUIL_ECART_CHANGE, relatif=True))

    # --- Indicateurs macro ---
    log("Recuperation des indicateurs macro...")
    ca = data["regions"]["CA"]["indicators"]
    us = data["regions"]["US"]["indicators"]

    chomage_ca_avant = (ca.get("unemployment") or {}).get("value")
    chomage_us_avant = (us.get("unemployment") or {}).get("value")

    taux_ca = fetch_taux_directeur_canada()
    appliquer(ca["rate"], taux_ca, "Banque du Canada")
    inflation_ca = fetch_inflation_canada()
    appliquer(ca["inflation"], inflation_ca, "Banque du Canada (IPC)")
    chomage_ca = fetch_chomage_canada()
    creer_ou_appliquer(ca, "unemployment", chomage_ca, "Statistique Canada",
                       "%", "Taux de chômage", "Unemployment")
    emploi_ca = fetch_variation_emploi_canada()

    # Secondes sources CA : la BRI republie le taux directeur canadien, et
    # l'OCDE republie son IPC. Toutes deux independantes de la Banque du
    # Canada, qui reste la source appliquee au tableau.
    taux_ca_bri = fetch_taux_directeur_bri("CA", "CA (controle)")
    verifications.append(comparer_sources(
        "Taux directeur CA", taux_ca and taux_ca["value"], "Banque du Canada",
        taux_ca_bri and taux_ca_bri["value"], "BRI", SEUIL_ECART_TAUX))
    inflation_ca_ocde, _ = fetch_inflation_ocde("CAN", "CA (controle)")
    verifications.append(comparer_sources(
        "Inflation CA", inflation_ca and inflation_ca["value"], "Banque du Canada",
        inflation_ca_ocde and inflation_ca_ocde["value"], "OCDE", SEUIL_ECART_INFLATION))

    taux_us = fetch_taux_directeur_us()
    appliquer(us["rate"], taux_us, "Federal Reserve (NY Fed)")
    taux_us_bri = fetch_taux_directeur_bri("US", "US (controle)")
    verifications.append(comparer_sources(
        "Taux directeur US", taux_us and taux_us["value"], "Federal Reserve (NY Fed)",
        taux_us_bri and taux_us_bri["value"], "BRI", SEUIL_ECART_TAUX))

    # Le BLS a rendu des 503 pendant toute la mise en place de ce pipeline.
    # L'OCDE republie le meme IPC americain (3,53 % pour juin 2026, contre
    # 3,5 % chez le BLS) : c'est un repli qui evite qu'une panne chez un seul
    # diffuseur fige l'inflation des Etats-Unis sur le site. On la recupere
    # dans tous les cas, panne ou pas, pour l'utiliser aussi en seconde
    # source de controle.
    inflation_us = fetch_inflation_us()
    inflation_us_ocde, _ = fetch_inflation_ocde("USA", "US (controle)")
    if inflation_us:
        appliquer(us["inflation"], inflation_us, "BLS")
    else:
        appliquer(us["inflation"], inflation_us_ocde, "OCDE (IPC, source BLS)")
    verifications.append(comparer_sources(
        "Inflation US", inflation_us and inflation_us["value"], "BLS",
        inflation_us_ocde and inflation_us_ocde["value"], "OCDE", SEUIL_ECART_INFLATION))

    chomage_us = fetch_chomage_us()
    creer_ou_appliquer(us, "unemployment", chomage_us, "BLS",
                       "%", "Taux de chômage", "Unemployment")
    emploi_us = fetch_variation_emploi_us()

    # Chine et Inde : ces quatre champs etaient saisis a la main et derivaient
    # de plusieurs mois. L'OCDE et la BRI les servent sans cle d'API. Ni l'une
    # ni l'autre n'a de seconde source publique facilement accessible pour
    # ces deux pays : verifier_borne() controle au moins la plausibilite.
    cn = data["regions"]["CN"]["indicators"]
    ind = data["regions"]["IN"]["indicators"]

    inflation_cn, serie_cn = fetch_inflation_ocde("CHN", "CN")
    appliquer(cn["inflation"], inflation_cn, "OCDE (IPC, source NBS)")
    inflation_in, serie_in = fetch_inflation_ocde("IND", "IN")
    appliquer(ind["inflation"], inflation_in, "OCDE (IPC, source MoSPI)")

    taux_cn = fetch_taux_directeur_bri("CN", "CN")
    appliquer(cn["rate"], taux_cn, "BRI (PBoC, taux préférentiel 1 an)")
    taux_in = fetch_taux_directeur_bri("IN", "IN")
    appliquer(ind["rate"], taux_in, "BRI (RBI, taux de prise en pension)")

    verifications.append(verifier_borne("Inflation CN", inflation_cn and inflation_cn["value"],
                                        "OCDE", "inflation"))
    verifications.append(verifier_borne("Inflation IN", inflation_in and inflation_in["value"],
                                        "OCDE", "inflation"))
    verifications.append(verifier_borne("Taux directeur CN", taux_cn and taux_cn["value"],
                                        "BRI", "rate"))
    verifications.append(verifier_borne("Taux directeur IN", taux_in and taux_in["value"],
                                        "BRI", "rate"))
    verifications.append(verifier_borne("Chômage CA", chomage_ca and chomage_ca["value"],
                                        "Statistique Canada", "unemployment"))
    verifications.append(verifier_borne("Chômage US", chomage_us and chomage_us["value"],
                                        "BLS", "unemployment"))

    # Ce qui reste a la main porte la marque. Ce sont des previsions annuelles
    # revisees une ou deux fois l'an, pas des series mensuelles : leur age ne
    # se mesure pas en jours, et le controle de fraicheur les ignore deja.
    for region, cles in (("CA", ("gdp",)), ("US", ("gdp",)), ("CN", ("gdp",)),
                         ("IN", ("gdp",)), ("WORLD", ("gdp", "inflation"))):
        for cle in cles:
            cible = data["regions"][region]["indicators"].get(cle)
            if cible is not None and not cible.get("source", "").startswith("OCDE"):
                cible["manual"] = True
            # Aucune de ces previsions n'a de seconde source verifiable en
            # continu (BdC, Fed, FMI...) : une borne de plausibilite reste le
            # seul filet qui attrape un chiffre saisi hors de son ordre de
            # grandeur.
            if cible is not None:
                verifications.append(verifier_borne(
                    f"{cle.upper()} {region}", cible.get("value"),
                    cible.get("source", "?"), cle))

    # --- Bourses ---
    for region, quote in fetch_all_stocks().items():
        if region in data["regions"]:
            action = data["regions"][region]["indicators"]["stockIndex"]
            action.update({"value": quote["value"], "change": quote["change"],
                           "trend": quote["trend"], "period": today})

    # --- Sparklines ---
    log("Recuperation des sparklines...")
    if poser_sparkline(data["regions"]["US"], fetch_sparkline_data("^GSPC")):
        log("  Sparkline US : posee")

    poser_sparkline(data["regions"]["CA"], fetch_sparkline_inflation_canada())

    # La courbe de l'Inde etait alimentee par le Sensex tout en s'annoncant
    # « Croissance PIB (trimestres) » : l'etiquette decrivait autre chose que
    # la donnee tracee. Celle de la Chine repetait la carte du taux de change.
    # Les deux passent a l'inflation, desormais disponible chez l'OCDE, ce qui
    # aligne les cinq zones sur une lecture comparable.
    libelle_inflation = {"fr": "Inflation (12 mois)",
                         "en": "Inflation (12 months)"}
    if serie_cn:
        poser_sparkline(data["regions"]["CN"], serie_cn, libelle_inflation)
    else:
        poser_sparkline(data["regions"]["CN"], fetch_exchange_sparkline("USD", "CNY"))
    if serie_in:
        poser_sparkline(data["regions"]["IN"], serie_in, libelle_inflation)
    poser_sparkline(data["regions"]["WORLD"], fetch_sparkline_data("BZ=F"))

    # --- Actualites ---
    log("Recuperation des actualites...")
    actualites_par_region = {}
    for region in ["CA", "US", "CN", "IN", "WORLD"]:
        items = recuperer_actualites(region, "en")
        actualites_par_region[region] = items
        if items:
            data["regions"][region]["headlines"] = formater_actualites(items)
        else:
            log(f"  {region} : aucune actualite retenue, ancien lot conserve")

        # Les titres francais viennent de la presse francophone, pas d'une
        # traduction automatique : un titre de presse est attribue a son
        # editeur, le reecrire par machine en ferait une citation fausse.
        items_fr = recuperer_actualites(region, "fr")
        if items_fr:
            data["regions"][region]["headlinesFr"] = formater_actualites(items_fr)
        else:
            log(f"  {region} : aucune actualite francophone, lot anglais servi")
        time.sleep(0.3)

    # --- Resumes et sentiment ---
    log("Composition des resumes et du sentiment...")
    emplois = {"CA": emploi_ca, "US": emploi_us}
    chomages = {"CA": chomage_ca, "US": chomage_us}
    avant = {"CA": chomage_ca_avant, "US": chomage_us_avant}
    for region in ["CA", "US", "CN", "IN", "WORLD"]:
        contenu = data["regions"][region]
        contenu["summary"] = composer_resume(
            region, contenu["indicators"], actualites_par_region.get(region, []),
            emplois.get(region), chomages.get(region))
        contenu["sentiment"] = calculer_sentiment(
            region, contenu["indicators"], emplois.get(region),
            chomages.get(region), avant.get(region))
        log(f"  {region} : sentiment {contenu['sentiment']['value']}")

    # --- Contenu editorial ---
    poser_contenu_editorial(data)

    # --- Fraicheur ---
    ajouter_periodes_anglaises(data)
    perimes = controler_fraicheur(data)
    data["staleIndicators"] = perimes

    # --- Coherence ---
    verifications = [v for v in verifications if v is not None]
    incoherences = [v for v in verifications if v["suspect"]]
    log(f"Controle de coherence : {len(verifications)} controle(s), "
        f"{len(incoherences)} ecart(s) suspect(s).")
    with open(COHERENCE_FILE, "w", encoding="utf-8") as f:
        json.dump({"date": today, "controles": verifications}, f,
                  ensure_ascii=False, indent=2)

    # --- Sante des flux ---
    kaput = flux_en_panne()
    if kaput:
        log(f"  {len(kaput)} flux en panne depuis {SEUIL_FLUX_EN_PANNE} passages ou plus.")
        for flux_mort in kaput:
            log(f"    EN PANNE {flux_mort['nom']} : {flux_mort['echecsConsecutifs']} echecs, "
                f"dernier succes {flux_mort['dernierSucces'] or 'jamais'}")
    with open(SANTE_FLUX_FILE, "w", encoding="utf-8") as f:
        json.dump(SANTE_FLUX, f, ensure_ascii=False, indent=2)

    # --- Sauvegarde ---
    log("Sauvegarde de indicators.json...")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Journal des rejets : un instantane par passage, ecrase a chaque fois.
    # Le rapport hebdomadaire agrege ces instantanes depuis l'historique Git.
    log(f"Journal des rejets : {len(JOURNAL_REJETS)} titres ecartes.")
    with open(REJETS_FILE, "w", encoding="utf-8") as f:
        json.dump({"date": today, "rejets": JOURNAL_REJETS},
                  f, ensure_ascii=False, indent=2)

    log("=" * 60)
    log(f"Mise a jour terminee — {today}")
    log("=" * 60)

    if perimes or incoherences or kaput:
        # Sortie non nulle : le workflow marque l'execution en echec et
        # GitHub envoie un courriel. C'est le seul rappel fiable pour ce qui
        # n'a pas de source automatisable, ce qui contredit une seconde
        # source, ou ce qui a cesse de repondre.
        log("Anomalies detectees, voir ci-dessus.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(update_indicators())

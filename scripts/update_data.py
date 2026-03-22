#!/usr/bin/env python3
"""
GeoEcon Pulse — Script de mise à jour automatique des données
Récupère les taux de change, indices boursiers et headlines RSS
Met à jour data/indicators.json
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import feedparser

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "indicators.json"

TIMEOUT = 15  # seconds per request

# Taux de change — frankfurter.app (gratuit, sans clé, CORS-friendly)
EXCHANGE_RATES_URL = "https://api.frankfurter.app/latest?from=USD&to=CAD,CNY,INR"

# Indices boursiers — Yahoo Finance (pas d'API key requise)
STOCK_SYMBOLS = {
    "CA": "^GSPTSE",    # S&P/TSX
    "US": "^GSPC",      # S&P 500
    "CN": "000001.SS",  # SSE Composite
    "IN": "^BSESN",     # SENSEX
    "WORLD": "ACWI",    # MSCI ACWI ETF (proxy)
}
STOCK_NAMES = {
    "CA": "S&P/TSX",
    "US": "S&P 500",
    "CN": "SSE Composite",
    "IN": "SENSEX",
    "WORLD": "MSCI World",
}

# Flux RSS par région
RSS_FEEDS = {
    "CA": [
        ("https://www.bankofcanada.ca/feed/", "Banque du Canada"),
        ("https://ici.radio-canada.ca/rss/4159", "Radio-Canada Économie"),
        ("https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/business/", "Globe and Mail"),
    ],
    "US": [
        ("https://feeds.reuters.com/reuters/businessNews", "Reuters"),
        ("https://www.cnbc.com/id/10001147/device/rss/rss.html", "CNBC"),
        ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC Business"),
    ],
    "CN": [
        ("https://www.scmp.com/rss/4/feed", "SCMP"),
        ("https://feeds.reuters.com/reuters/worldNews", "Reuters World"),
    ],
    "IN": [
        ("https://economictimes.indiatimes.com/rssfeedstopstories.cms", "Economic Times"),
        ("https://feeds.reuters.com/reuters/INbusinessNews", "Reuters India"),
    ],
    "WORLD": [
        ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC World"),
        ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
        ("https://feeds.reuters.com/reuters/worldNews", "Reuters World"),
    ],
}

# Mots-clés pour filtrer les headlines NON économiques
EXCLUDE_KEYWORDS = [
    "hockey", "nhl", "lnh", "canadiens", "habs", "leafs", "oilers",
    "soccer", "football", "nba", "nfl", "mlb", "tennis", "olympics",
    "olympique", "coupe stanley", "stanley cup", "playoffs",
    "météo", "weather", "tempête", "storm", "neige", "snow",
    "sport", "match", "goal", "but ", "victoire", "défaite",
    "série", "saison", "classement", "ligue",
    "caufield", "slafkovsky", "mcdavid", "crosby", "ovechkin",
    "célébrité", "celebrity", "divertissement", "entertainment",
    "recette", "recipe", "cuisine", "restaurant",
    "horoscope", "zodiac",
]

# Mots-clés pour identifier les headlines économiques (au moins un doit matcher)
ECONOMIC_KEYWORDS = [
    "econom", "économ", "trade", "commerc", "tarif", "tariff",
    "inflation", "gdp", "pib", "growth", "croissance", "recession",
    "bank", "banque", "rate", "taux", "fed ", "monetary", "monétaire",
    "oil", "pétrole", "energy", "énergie", "gas", "gaz",
    "market", "marché", "stock", "bourse", "index", "indice",
    "dollar", "currency", "devise", "yuan", "rupee", "roupie",
    "export", "import", "employ", "job", "chômage", "unemploy",
    "budget", "fiscal", "deficit", "déficit", "debt", "dette",
    "sanction", "geopolit", "géopolit", "war", "guerre", "iran",
    "china", "chine", "india", "inde", "trump", "tarif",
    "manufacture", "industri", "tech", "semiconductor", "ai ",
    " ia ", "artificial", "artificielle",
    "investment", "investiss", "fund", "fonds",
    "supply chain", "chaîne", "shipping", "transport",
    "climate", "climat", "carbon", "carbone", "emission", "émission",
    "imf", "fmi", "world bank", "banque mondiale", "wto", "omc",
    "ormuz", "hormuz", "opec", "opep",
    "billion", "milliard", "trillion", "revenue", "revenu",
    "tax", "impôt", "subsid", "subvention",
    "housing", "immobili", "logement", "mortgage", "hypothèque",
    "crypto", "bitcoin", "blockchain",
    "pipeline", "lng", "gnl", "refinery", "raffinerie",
    "canola", "lumber", "bois", "steel", "acier", "aluminum", "aluminium",
    "central bank", "banque centrale", "policy rate", "taux directeur",
]

# Mots-clés pour classifier les thèmes
THEME_KEYWORDS = {
    "trade": [
        "tarif", "tariff", "trade", "commerce", "export", "import", "cusma",
        "usmca", "wto", "omc", "customs", "douane", "dumping", "quota",
        "supply chain", "chaîne", "manufacturing", "manufacturier", "gdp", "pib",
        "growth", "croissance", "recession", "emploi", "job", "unemployment",
        "chômage", "labor", "travail",
    ],
    "monetary": [
        "taux", "rate", "interest", "intérêt", "banque centrale", "central bank",
        "fed", "boc", "pboc", "rbi", "ecb", "bce", "inflation", "déflation",
        "deflation", "monetary", "monétaire", "yield", "rendement", "bond",
        "obligation", "quantitative", "dollar", "currency", "devise", "forex",
        "rupee", "yuan", "roupie",
    ],
    "energy": [
        "oil", "pétrole", "opec", "opep", "gas", "gaz", "energy", "énergie",
        "brent", "crude", "brut", "pipeline", "lng", "gnl", "solar", "solaire",
        "renewable", "renouvelable", "nuclear", "nucléaire", "coal", "charbon",
        "hormuz", "ormuz", "refinery", "raffinerie",
    ],
    "tech": [
        "tech", "ai", "ia", "artificial intelligence", "intelligence artificielle",
        "semiconductor", "semi-conducteur", "chip", "puce", "data", "donnée",
        "cloud", "cyber", "quantum", "quantique", "robot", "automat", "software",
        "logiciel", "startup", "crypto", "bitcoin", "blockchain",
    ],
    "geopolitics": [
        "war", "guerre", "military", "militaire", "sanction", "nato", "otan",
        "iran", "russia", "russie", "ukraine", "china", "chine", "taiwan",
        "missile", "nuclear weapon", "arme nucléaire", "diplomacy", "diplomatie",
        "conflict", "conflit", "invasion", "alliance", "trump", "xi",
        "election", "élection", "coup", "regime", "régime",
    ],
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ============================================================
# TAUX DE CHANGE (frankfurter.app)
# ============================================================

def fetch_exchange_rates():
    """Récupère CAD/USD, CNY/USD, INR/USD depuis frankfurter.app"""
    log("Récupération des taux de change...")
    try:
        resp = requests.get(EXCHANGE_RATES_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates", {})
        date_str = data.get("date", "")
        log(f"  Taux de change récupérés pour {date_str}: CAD={rates.get('CAD')}, CNY={rates.get('CNY')}, INR={rates.get('INR')}")
        return {
            "CAD": rates.get("CAD"),
            "CNY": rates.get("CNY"),
            "INR": rates.get("INR"),
            "date": date_str,
        }
    except Exception as e:
        log(f"  ERREUR taux de change: {e}")
        return None


# ============================================================
# INDICES BOURSIERS (Yahoo Finance)
# ============================================================

def fetch_stock_quote(symbol):
    """Récupère le cours d'un indice via Yahoo Finance"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; GeoEconPulse/1.0)"}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose", 0)

        change_pct = 0
        if prev_close and prev_close > 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        trend = "up" if change_pct > 0.1 else ("down" if change_pct < -0.1 else "stable")

        return {
            "value": round(price),
            "change": change_pct,
            "trend": trend,
        }
    except Exception as e:
        log(f"  ERREUR Yahoo Finance ({symbol}): {e}")
        return None


def fetch_all_stocks():
    """Récupère tous les indices boursiers"""
    log("Récupération des indices boursiers...")
    results = {}
    for region, symbol in STOCK_SYMBOLS.items():
        quote = fetch_stock_quote(symbol)
        if quote:
            log(f"  {region} ({symbol}): {quote['value']} ({quote['change']:+.2f}%)")
            results[region] = quote
        time.sleep(0.5)  # Rate limiting
    return results


# ============================================================
# SPARKLINES — données historiques 12 mois
# ============================================================

def fetch_sparkline_data(symbol, interval="1mo", range_str="1y"):
    """Récupère les données historiques pour les sparklines"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_str}"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; GeoEconPulse/1.0)"}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        # Filtrer les None et arrondir
        return [round(c, 2) if c else None for c in closes]
    except Exception as e:
        log(f"  ERREUR sparkline ({symbol}): {e}")
        return None


def fetch_exchange_sparkline(from_currency, to_currency):
    """Données historiques de taux de change via frankfurter.app"""
    try:
        end = datetime.now()
        start = end - timedelta(days=365)
        url = (
            f"https://api.frankfurter.app/{start.strftime('%Y-%m-%d')}"
            f"..{end.strftime('%Y-%m-%d')}?from={from_currency}&to={to_currency}"
        )
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates", {})
        # Prendre un point par mois (environ 30 jours d'intervalle)
        sorted_dates = sorted(rates.keys())
        monthly = []
        last_month = None
        for d in sorted_dates:
            month = d[:7]
            if month != last_month:
                monthly.append(rates[d][to_currency])
                last_month = month
        # Garder les 12 derniers
        return monthly[-12:] if len(monthly) >= 12 else monthly
    except Exception as e:
        log(f"  ERREUR sparkline FX ({from_currency}/{to_currency}): {e}")
        return None


# ============================================================
# HEADLINES RSS
# ============================================================

def classify_theme(text):
    """Classifie un texte dans un thème basé sur les mots-clés"""
    text_lower = text.lower()
    scores = {}
    for theme, keywords in THEME_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[theme] = score
    if scores:
        return max(scores, key=scores.get)
    return "trade"  # default


def estimate_impact(title):
    """Estime l'impact d'une headline (high/medium/low)"""
    title_lower = title.lower()
    high_words = [
        "crisis", "crise", "war", "guerre", "crash", "collapse",
        "recession", "record", "surge", "flambée", "plunge", "chute",
        "massive", "unprecedented", "historique", "emergency", "urgence",
        "billion", "milliard", "trillion",
    ]
    medium_words = [
        "rise", "hausse", "fall", "baisse", "concern", "préoccupation",
        "policy", "politique", "reform", "réforme", "forecast", "prévision",
        "expect", "growth", "croissance", "inflation", "rate", "taux",
    ]
    if any(w in title_lower for w in high_words):
        return "high"
    if any(w in title_lower for w in medium_words):
        return "medium"
    return "low"


def time_ago(published_parsed):
    """Convertit un timestamp en format relatif (2h, 1j, 3j, 1s)"""
    if not published_parsed:
        return "?"
    try:
        from email.utils import formatdate
        import calendar
        pub_time = datetime(*published_parsed[:6], tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - pub_time
        hours = delta.total_seconds() / 3600
        if hours < 1:
            return "<1h"
        elif hours < 24:
            return f"{int(hours)}h"
        elif hours < 168:  # 7 days
            return f"{int(hours / 24)}j"
        else:
            weeks = int(hours / 168)
            return f"{weeks}s"
    except Exception:
        return "?"


def fetch_rss_headlines(region):
    """Récupère les headlines RSS pour une région"""
    feeds = RSS_FEEDS.get(region, [])
    all_entries = []

    for feed_url, source_name in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:25]:
                title_en = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published_parsed")

                if not title_en or not link:
                    continue

                # Filtrer les headlines non économiques
                title_lower = title_en.lower()
                if any(kw in title_lower for kw in EXCLUDE_KEYWORDS):
                    continue
                if not any(kw in title_lower for kw in ECONOMIC_KEYWORDS):
                    continue

                all_entries.append({
                    "title_en": title_en,
                    "url": link,
                    "source": source_name,
                    "published_parsed": published,
                    "theme": classify_theme(title_en),
                    "impact": estimate_impact(title_en),
                    "time": time_ago(published),
                })
        except Exception as e:
            log(f"  ERREUR RSS ({source_name}): {e}")

    # Trier par date (plus récent en premier)
    all_entries.sort(
        key=lambda x: x["published_parsed"] or (1970, 1, 1, 0, 0, 0, 0, 0, 0),
        reverse=True,
    )

    # Garder les 8 plus récentes, dédupliquées par titre
    seen = set()
    unique = []
    for entry in all_entries:
        title_key = entry["title_en"][:50].lower()
        if title_key not in seen:
            seen.add(title_key)
            unique.append(entry)
        if len(unique) >= 8:
            break

    return unique


def format_headlines(entries):
    """Convertit les entrées RSS en format indicators.json"""
    headlines = []
    for e in entries:
        headlines.append({
            "title": {
                "fr": e["title_en"],  # RSS en anglais, FR = même texte (à traduire manuellement)
                "en": e["title_en"],
            },
            "url": e["url"],
            "theme": e["theme"],
            "time": e["time"],
            "impact": e["impact"],
            "source": e["source"],
        })
    return headlines


# ============================================================
# MISE À JOUR DU JSON
# ============================================================

def update_indicators():
    """Fonction principale de mise à jour"""
    log("=" * 60)
    log("GeoEcon Pulse — Mise à jour automatique des données")
    log("=" * 60)

    # Charger le JSON existant
    if not DATA_FILE.exists():
        log(f"ERREUR: {DATA_FILE} introuvable")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    data["lastUpdated"] = today

    # --- Taux de change ---
    fx = fetch_exchange_rates()
    if fx:
        date_str = fx["date"]
        if fx["CAD"]:
            ca = data["regions"]["CA"]["indicators"]["exchange"]
            old_val = ca["value"]
            ca["value"] = round(fx["CAD"], 3)
            ca["trend"] = "up" if fx["CAD"] > old_val else ("down" if fx["CAD"] < old_val else "stable")
            ca["period"] = date_str
            ca["source"] = "Frankfurter/ECB"

        if fx["CNY"]:
            cn = data["regions"]["CN"]["indicators"]["exchange"]
            old_val = cn["value"]
            cn["value"] = round(fx["CNY"], 3)
            cn["trend"] = "up" if fx["CNY"] > old_val else ("down" if fx["CNY"] < old_val else "stable")
            cn["period"] = date_str
            cn["source"] = "Frankfurter/ECB"

        if fx["INR"]:
            ind = data["regions"]["IN"]["indicators"]["exchange"]
            old_val = ind["value"]
            ind["value"] = round(fx["INR"], 2)
            ind["trend"] = "up" if fx["INR"] > old_val else ("down" if fx["INR"] < old_val else "stable")
            ind["period"] = date_str
            ind["source"] = "Frankfurter/ECB"

    # --- Indices boursiers ---
    stocks = fetch_all_stocks()
    for region, quote in stocks.items():
        if region in data["regions"]:
            stock = data["regions"][region]["indicators"]["stockIndex"]
            stock["value"] = quote["value"]
            stock["change"] = quote["change"]
            stock["trend"] = quote["trend"]
            stock["period"] = today

    # --- Sparklines (indices boursiers) ---
    log("Récupération des données sparkline...")
    sparkline_map = {
        "US": ("^GSPC", "S&P 500 (12 mois)", "S&P 500 (12 months)"),
        "IN": ("^BSESN", "SENSEX (12 mois)", "SENSEX (12 months)"),
    }
    for region, (symbol, label_fr, label_en) in sparkline_map.items():
        spark_data = fetch_sparkline_data(symbol)
        if spark_data:
            clean = [v for v in spark_data if v is not None]
            if len(clean) >= 6:
                data["regions"][region]["sparkline"]["data"] = clean[-12:]
                log(f"  Sparkline {region}: {len(clean)} points")
        time.sleep(0.5)

    # Sparkline Canada — inflation (pas d'API simple, on garde les données manuelles)
    # Sparkline Chine — Yuan/USD via frankfurter
    yuan_spark = fetch_exchange_sparkline("USD", "CNY")
    if yuan_spark and len(yuan_spark) >= 6:
        data["regions"]["CN"]["sparkline"]["data"] = yuan_spark[-12:]
        log(f"  Sparkline CN (Yuan/USD): {len(yuan_spark)} points")

    # Sparkline Monde — Brent via Yahoo
    brent_spark = fetch_sparkline_data("BZ=F")
    if brent_spark:
        clean = [v for v in brent_spark if v is not None]
        if len(clean) >= 6:
            data["regions"]["WORLD"]["sparkline"]["data"] = clean[-12:]
            log(f"  Sparkline WORLD (Brent): {len(clean)} points")

    # --- Headlines RSS ---
    log("Récupération des headlines RSS...")
    for region in ["CA", "US", "CN", "IN", "WORLD"]:
        entries = fetch_rss_headlines(region)
        if entries:
            headlines = format_headlines(entries)
            data["regions"][region]["headlines"] = headlines
            log(f"  {region}: {len(headlines)} headlines récupérées")
        else:
            log(f"  {region}: aucune headline (flux RSS indisponibles)")
        time.sleep(0.3)

    # --- Sauvegarder ---
    log("Sauvegarde de indicators.json...")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log("=" * 60)
    log(f"Mise à jour terminée — {today}")
    log("=" * 60)


if __name__ == "__main__":
    update_indicators()

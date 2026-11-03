"""Normalisation des noms, adresses, domaines, téléphones et rapprochement flou."""
import re
import unicodedata
from difflib import SequenceMatcher

FORMES_JURIDIQUES = {
    "sarl", "sas", "sasu", "eurl", "sa", "sci", "snc", "scop", "ei", "eirl", "micro", "entreprise",
    "association", "asso", "ste", "societe", "cie", "et", "the", "le", "la", "les", "l", "de", "du", "des", "d",
}

# Eurométropole de Strasbourg : codes postaux et communes (pour la zone du score).
CP_EUROMETROPOLE = {
    "67000", "67100", "67200", "67300", "67400", "67380", "67540", "67800", "67201", "67205", "67206",
    "67207", "67460", "67116", "67550", "67610", "67810", "67960", "67118", "67640", "67114", "67115",
    "67450", "67204", "67202", "67113", "67088", "67089", "67090", "67091", "67092", "67093", "67094",
    "67095", "67096", "67097", "67098", "67099", "67081", "67082", "67083", "67084", "67085", "67086",
}
COMMUNES_EUROMETROPOLE = {
    "strasbourg", "schiltigheim", "illkirch graffenstaden", "illkirch", "lingolsheim", "ostwald",
    "bischheim", "hoenheim", "eckbolsheim", "oberhausbergen", "mittelhausbergen", "niederhausbergen",
    "souffelweyersheim", "reichstett", "vendenheim", "wantzenau", "holtzheim", "entzheim",
    "geispolsheim", "fegersheim", "eschau", "plobsheim", "lampertheim", "mundolsheim", "achenheim",
    "breuschwickersheim", "hangenbieten", "kolbsheim", "osthoffen", "oberschaeffolsheim", "wolfisheim",
    "blaesheim", "lipsheim", "eckwersheim",
}


def sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texte) if not unicodedata.combining(c))


def nom(texte: str | None) -> str:
    if not texte:
        return ""
    t = sans_accents(texte).casefold()
    t = re.sub(r"[’'`]", " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    mots = [m for m in t.split() if m not in FORMES_JURIDIQUES]
    return " ".join(mots)


def slug(texte: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", sans_accents(texte or "").casefold()).strip("-")[:48] or "sans-nom"


def email(texte: str | None) -> str:
    if not texte:
        return ""
    t = re.sub(r"^mailto:", "", texte.strip().lower())
    t = t.split("?")[0]
    trouve = re.search(r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9.-]+\.[a-z]{2,24}", t)
    if trouve:
        return trouve.group(0).strip(".")
    return t.strip("<>\"' .,;:")


def domaine(texte: str | None) -> str:
    """Domaine d'une adresse e-mail ou d'une URL, sans www."""
    if not texte:
        return ""
    t = texte.strip().lower()
    if "@" in t and "://" not in t:
        t = t.split("@")[-1]
    else:
        t = re.sub(r"^[a-z]+://", "", t)
        t = t.split("/")[0]
    t = t.split(":")[0].strip(".")
    return re.sub(r"^www\.", "", t)


def url(texte: str | None) -> str:
    if not texte:
        return ""
    t = texte.strip()
    if not re.match(r"^[a-z]+://", t, re.I):
        t = "https://" + t
    return t.rstrip("/")


def telephone(texte: str | None) -> str:
    if not texte:
        return ""
    chiffres = re.sub(r"\D", "", texte)
    if chiffres.startswith("0033"):
        chiffres = "0" + chiffres[4:]
    elif chiffres.startswith("33") and len(chiffres) == 11:
        chiffres = "0" + chiffres[2:]
    return chiffres


def instagram(texte: str | None) -> str:
    if not texte:
        return ""
    t = texte.strip().lower()
    t = re.sub(r"^https?://(www\.)?instagram\.com/", "", t)
    return t.strip("@/ ").split("/")[0].split("?")[0]


def similarite(a: str, b: str) -> float:
    """Similarité de deux noms normalisés (0 à 1) : moyenne séquence + recouvrement de mots."""
    na, nb = nom(a), nom(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ma, mb = set(na.split()), set(nb.split())
    jaccard = len(ma & mb) / len(ma | mb)
    compact = SequenceMatcher(None, na.replace(" ", ""), nb.replace(" ", "")).ratio()
    sim = max(0.6 * seq + 0.4 * jaccard, 0.95 * compact)
    if re.findall(r"\d+", na) != re.findall(r"\d+", nb):
        sim = min(sim, 0.85)  # « Studio 1 » et « Studio 2 » sont deux structures
    return round(sim, 3)


def zone(ville: str | None, code_postal: str | None) -> str | None:
    cp = re.sub(r"\D", "", code_postal or "")[:5]
    v = nom(ville)
    if cp in CP_EUROMETROPOLE or v in COMMUNES_EUROMETROPOLE:
        return "strasbourg"
    if cp.startswith(("67", "68")):
        return "alsace"
    if cp or v:
        return "france"
    return None

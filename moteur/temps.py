"""Dates : heure de Paris, jours fériés (Alsace-Moselle comprise), jours ouvrés."""
from datetime import date, datetime, timedelta, timezone

from .config import FUSEAU

JOURS = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]


def maintenant() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=FUSEAU)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def lire_iso(texte: str) -> datetime:
    dt = datetime.fromisoformat(texte.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=FUSEAU)
    return dt


def local(dt: datetime) -> datetime:
    return dt.astimezone(FUSEAU)


def paques(annee: int) -> date:
    """Dimanche de Pâques (algorithme de Meeus/Jones/Butcher)."""
    a = annee % 19
    b, c = divmod(annee, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = (h + l - 7 * m + 114) % 31 + 1
    return date(annee, mois, jour)


def jours_feries(annee: int, alsace: bool = True) -> set[date]:
    p = paques(annee)
    feries = {
        date(annee, 1, 1), p + timedelta(days=1), date(annee, 5, 1), date(annee, 5, 8),
        p + timedelta(days=39), p + timedelta(days=50), date(annee, 7, 14), date(annee, 8, 15),
        date(annee, 11, 1), date(annee, 11, 11), date(annee, 12, 25),
    }
    if alsace:
        feries |= {p - timedelta(days=2), date(annee, 12, 26)}
    return feries


def est_ouvre(jour: date, jours_envoi=(0, 1, 2, 3, 4), alsace: bool = True) -> bool:
    return jour.weekday() in jours_envoi and jour not in jours_feries(jour.year, alsace)


def ajouter_jours_ouvres(depart: date, n: int, jours_envoi=(0, 1, 2, 3, 4), alsace: bool = True) -> date:
    jour = depart
    restant = n
    while restant > 0:
        jour += timedelta(days=1)
        if est_ouvre(jour, jours_envoi, alsace):
            restant -= 1
    return jour


def jours_ouvres_entre(debut: date, fin: date, jours_envoi=(0, 1, 2, 3, 4), alsace: bool = True) -> int:
    """Nombre de jours ouvrés dans [debut, fin]."""
    if fin < debut:
        return 0
    n, jour = 0, debut
    while jour <= fin:
        if est_ouvre(jour, jours_envoi, alsace):
            n += 1
        jour += timedelta(days=1)
    return n


def hm(texte: str) -> tuple[int, int]:
    h, m = texte.split(":")
    return int(h), int(m)


def dans_fenetre(dt_local: datetime, debut: str, fin: str) -> bool:
    minutes = dt_local.hour * 60 + dt_local.minute
    hd, md = hm(debut)
    hf, mf = hm(fin)
    return hd * 60 + md <= minutes < hf * 60 + mf


def lundi_de(jour: date) -> date:
    return jour - timedelta(days=jour.weekday())

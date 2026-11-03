"""Statistiques bayésiennes pour petits échantillons (loi Bêta-Bernoulli).

À 10 mails par jour, les échantillons sont petits : on raisonne en probabilités
(« 92 % de chances que A fasse mieux que B ») plutôt qu'en moyennes brutes, et on dit
« pas concluant » quand c'est le cas. Tirages de Monte-Carlo à graine fixe : mêmes données,
même verdict."""
import math
import random

TIRAGES = 20000


def _rng(graine: int = 7) -> random.Random:
    return random.Random(graine)


def tirages_beta(a: float, b: float, n: int = TIRAGES, graine: int = 7) -> list[float]:
    r = _rng(graine)
    return [r.betavariate(max(a, 1e-6), max(b, 1e-6)) for _ in range(n)]


def posterieur(succes: float, essais: float, prior=(1.0, 1.0)) -> tuple[float, float]:
    echecs = max(essais - succes, 0.0)
    return prior[0] + succes, prior[1] + echecs


def moyenne(succes: float, essais: float, prior=(1.0, 1.0)) -> float:
    a, b = posterieur(succes, essais, prior)
    return a / (a + b)


def intervalle(succes: float, essais: float, prior=(1.0, 1.0), niveau: float = 0.9) -> tuple[float, float]:
    a, b = posterieur(succes, essais, prior)
    t = sorted(tirages_beta(a, b, 8000))
    bas = t[int((1 - niveau) / 2 * len(t))]
    haut = t[min(len(t) - 1, int((1 + niveau) / 2 * len(t)))]
    return bas, haut


def proba_au_dessus(succes: float, essais: float, seuil: float, prior=(1.0, 1.0)) -> float:
    a, b = posterieur(succes, essais, prior)
    t = tirages_beta(a, b, 8000)
    return sum(1 for x in t if x > seuil) / len(t)


def proba_superieur(s1: float, n1: float, s2: float, n2: float, prior=(1.0, 1.0)) -> float:
    """P(taux 1 > taux 2)."""
    a1, b1 = posterieur(s1, n1, prior)
    a2, b2 = posterieur(s2, n2, prior)
    t1 = tirages_beta(a1, b1, 8000, graine=11)
    t2 = tirages_beta(a2, b2, 8000, graine=13)
    return sum(1 for x, y in zip(t1, t2) if x > y) / len(t1)


def proba_meilleur(bras: list[tuple[float, float]], prior=(1.0, 1.0), n: int = 8000) -> list[float]:
    """Pour chaque bras (succès, essais) : probabilité d'être le meilleur."""
    if not bras:
        return []
    series = [tirages_beta(*posterieur(s, e, prior), n=n, graine=17 + i) for i, (s, e) in enumerate(bras)]
    gagnes = [0] * len(bras)
    for j in range(n):
        meilleur = max(range(len(bras)), key=lambda i: series[i][j])
        gagnes[meilleur] += 1
    return [g / n for g in gagnes]


def wilson(succes: float, essais: float, z: float = 1.645) -> tuple[float, float]:
    if essais <= 0:
        return 0.0, 1.0
    p = succes / essais
    d = 1 + z * z / essais
    centre = (p + z * z / (2 * essais)) / d
    marge = z * math.sqrt(p * (1 - p) / essais + z * z / (4 * essais * essais)) / d
    return max(0.0, centre - marge), min(1.0, centre + marge)


def niveau_preuve(proba: float, n_min_ok: bool, tests: int = 1) -> str:
    """Traduit une probabilité en niveau de preuve, corrigé du nombre de tests faits (Bonferroni)."""
    if not n_min_ok:
        return "données insuffisantes"
    seuil_prouve = max(0.95, 1 - 0.05 / max(tests, 1))
    if proba >= seuil_prouve:
        return "prouvé"
    if proba >= 0.90:
        return "probable"
    if proba >= 0.75:
        return "piste"
    if proba <= 0.25:
        return "écarté"
    return "non concluant"


def pct(x: float | None, decimales: int = 1) -> str:
    return "—" if x is None else f"{100 * x:.{decimales}f} %"

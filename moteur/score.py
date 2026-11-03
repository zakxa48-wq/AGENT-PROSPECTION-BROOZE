"""Score de probabilité de réponse (sur 100) et recalibrage par régression logistique.

Le score de départ est une hypothèse (docs/02-offre-cible.md). Le recalibrage apprend des
vraies réponses : chaque poids est rapproché de ce que les données montrent, avec une
prudence proportionnelle au nombre de réponses observées (rétrécissement)."""
import math

from . import normalise
from .config import charger

SIGNAUX = ("zone", "boite", "declencheur", "actif_14j", "publie_sans_effet", "pub_meta",
           "matiere_exploitable", "pas_video_pro")


def boite_de(p: dict, zone: str | None) -> str | None:
    s = p.get("signaux") or {}
    if s.get("boite"):
        return s["boite"]
    t = (p.get("verif") or {}).get("type")
    if t in ("perso", "nominative"):
        return "decideur"
    if t == "generique":
        return "contact_local" if zone in ("strasbourg", "alsace") else "generique_distant"
    if t == "guichet":
        return "guichet"
    return None


def caracteristiques(p: dict) -> tuple[dict[str, bool], float]:
    s = p.get("signaux") or {}
    zone = s.get("zone") or normalise.zone(p.get("ville"), p.get("code_postal"))
    boite = boite_de(p, zone)
    f = {
        "zone_strasbourg": zone == "strasbourg",
        "zone_alsace": zone == "alsace",
        "boite_decideur": boite == "decideur",
        "boite_contact_local": boite == "contact_local",
        "declencheur": bool(s.get("declencheur")),
        "actif_14j": bool(s.get("actif_14j")),
        "publie_sans_effet": bool(s.get("publie_sans_effet")),
        "pub_meta": bool(s.get("pub_meta")),
        "matiere_exploitable": bool(s.get("matiere_exploitable")),
        "pas_video_pro": bool(s.get("pas_video_pro")),
    }
    connus = sum(1 for k in SIGNAUX if (zone if k == "zone" else boite if k == "boite" else s.get(k)) is not None)
    return f, connus / len(SIGNAUX)


def exclusions_de(p: dict, crm=None) -> list[str]:
    ex = list(p.get("exclusions") or [])
    if (p.get("verif") or {}).get("type") == "guichet" and "guichet" not in ex:
        ex.append("guichet")
    if crm is not None and p.get("email"):
        if normalise.domaine(p["email"]) in crm.domaines_exclus() and "desinscrit" not in ex:
            ex.append("desinscrit")
    return ex


def calculer(p: dict, crm=None, conf: dict | None = None) -> dict:
    conf = conf or charger("score")
    poids = conf["poids"]
    f, completude = caracteristiques(p)
    detail = [(k, poids.get(k, 0)) for k, v in f.items() if v and poids.get(k, 0)]
    score = max(0, min(100, sum(pts for _, pts in detail)))
    ex = [x for x in exclusions_de(p, crm) if x in conf["exclusions"]]
    if ex:
        score = 0
    return {
        "score": score,
        "detail": detail,
        "exclusions": ex,
        "completude": round(completude, 2),
        "decision": ("exclu" if ex else "priorite" if score >= conf["seuil_priorite"]
                     else "envoi" if score >= conf["seuil_envoi"] else "ecarte"),
    }


# --- Recalibrage ----------------------------------------------------------------------------

def _logistique(X: list[list[float]], y: list[int], l2: float = 1.0, iterations: int = 3000,
                pas: float = 0.3) -> list[float]:
    """Régression logistique avec pénalité L2 (descente de gradient). Retourne [biais, b1..bk]."""
    n, k = len(X), len(X[0])
    b = [0.0] * (k + 1)
    for _ in range(iterations):
        g = [0.0] * (k + 1)
        for xi, yi in zip(X, y):
            z = b[0] + sum(bj * xj for bj, xj in zip(b[1:], xi))
            p = 1 / (1 + math.exp(-max(-30, min(30, z))))
            err = p - yi
            g[0] += err
            for j in range(k):
                g[j + 1] += err * xi[j]
        for j in range(k + 1):
            reg = l2 * b[j] if j else 0.0
            b[j] -= pas * (g[j] + reg) / n
    return b


def calibrer(crm, metrique: str = "reponse") -> dict:
    """Propose de nouveaux poids à partir des premiers contacts délivrés et de leur issue."""
    from .diagnostic import issues_premiers_contacts
    conf = charger("score")
    lignes = issues_premiers_contacts(crm)
    lignes = [l for l in lignes if not l["rebond"]]
    noms = list(conf["poids"].keys())
    X, y = [], []
    for l in lignes:
        f, _ = caracteristiques(crm.prospects[l["prospect"]])
        X.append([1.0 if f.get(nm) else 0.0 for nm in noms])
        y.append(1 if l[metrique] else 0)
    n, positifs = len(y), sum(y)
    if n < 20 or positifs < 3:
        return {"n": n, "positifs": positifs, "fiable": False, "message": "Pas assez de données pour recalibrer.",
                "poids_actuels": conf["poids"], "poids_proposes": conf["poids"]}
    b = _logistique(X, y)
    variance = {nm: sum(row[j] for row in X) for j, nm in enumerate(noms)}
    coefs = {nm: b[j + 1] for j, nm in enumerate(noms)}
    # 1 point de score ≈ 0,05 en log-cote (20 points ≈ x2,7 de chances de réponse).
    suggestion = {nm: (round(c / 0.05) if variance[nm] >= 5 else None) for nm, c in coefs.items()}
    confiance = min(1.0, positifs / 50)
    proposes = {}
    for nm, ancien in conf["poids"].items():
        s = suggestion[nm]
        proposes[nm] = ancien if s is None else int(round((1 - confiance) * ancien + confiance * max(-20, min(30, s))))
    return {
        "n": n, "positifs": positifs, "fiable": n >= 150 and positifs >= 15, "confiance": round(confiance, 2),
        "coefficients": {k: round(v, 3) for k, v in coefs.items()},
        "observations_par_signal": variance,
        "poids_actuels": conf["poids"], "poids_proposes": proposes,
        "message": ("Signaux jamais observés (variance < 5) : poids inchangés. "
                    "Les poids proposés sont un mélange ancien/nouveau pondéré par le nombre de réponses."),
    }

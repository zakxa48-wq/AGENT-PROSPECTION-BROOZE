"""Tests d'approches en continu : échantillonnage de Thompson avec exposition retardée.

- Chaque premier contact reçoit une approche (bras) : A témoin, B, C…
- Chaque jour, l'allocation tire au sort selon la probabilité actuelle de chaque bras d'être
  le meilleur : les approches qui convertissent reçoivent progressivement plus d'envois.
- Correction du retard : un mail envoyé hier n'a pas encore eu le temps d'obtenir sa réponse.
  Il ne compte que pour une fraction d'essai (courbe de maturation), sinon les nouveaux bras
  seraient injustement pénalisés.
- Garde-fous statistiques : le témoin garde une part minimale ; un champion n'est déclaré
  qu'au-delà d'un nombre minimal d'essais et d'une probabilité élevée d'être le meilleur."""
import random
from datetime import date, datetime

from . import stats, temps
from .config import charger


def maturation(age_jours: float, conf: dict) -> float:
    xs, ys = conf["maturation"]["jours"], conf["maturation"]["part"]
    if age_jours <= xs[0]:
        return ys[0]
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if age_jours <= x1:
            return y0 + (y1 - y0) * (age_jours - x0) / (x1 - x0)
    return ys[-1]


def reestimer_maturation(crm, conf: dict) -> dict:
    """Recalcule la courbe à partir des délais réels de réponse (si au moins 20 réponses)."""
    delais = []
    for e in crm.evenements(type_="reponse"):
        premier = crm.premier_envoi(e["prospect"])
        if premier:
            delais.append((temps.lire_iso(e["ts"]) - temps.lire_iso(premier["ts"])).total_seconds() / 86400)
    if len(delais) < 20:
        return conf["maturation"]
    jours = conf["maturation"]["jours"]
    part = [round(sum(1 for d in delais if d <= j) / len(delais), 3) for j in jours]
    part[-1] = 1.0
    return {"jours": jours, "part": part, "n": len(delais)}


def resultats_par_bras(crm, conf: dict | None = None, maintenant: datetime | None = None) -> dict:
    conf = conf or charger("approches")
    t = maintenant or temps.maintenant()
    courbe = {"maturation": reestimer_maturation(crm, conf)}
    from .diagnostic import issues_premiers_contacts
    bras = {b["id"]: {"bras": b, "envois": 0, "essais": 0.0, "reponse": 0, "positive": 0, "rdv": 0,
                      "gagne": 0, "rebond": 0} for b in conf["bras"]}
    for l in issues_premiers_contacts(crm, live=True):
        a = l["dims"].get("approche")
        if a not in bras:
            continue
        r = bras[a]
        r["envois"] += 1
        if l["rebond"]:
            r["rebond"] += 1
            continue
        age = (t - temps.lire_iso(l["ts"])).total_seconds() / 86400
        succes = l[conf["recompense"]]
        r["essais"] += 1.0 if succes else maturation(age, courbe)
        for m in ("reponse", "positive", "rdv", "gagne"):
            r[m] += int(bool(l[m]))
    prior = tuple(conf["prior"])
    actifs = [k for k, r in bras.items() if r["bras"].get("statut") in ("actif", "champion")]
    pm = stats.proba_meilleur([(bras[k][conf["recompense"]], bras[k]["essais"]) for k in actifs], prior)
    for k, p in zip(actifs, pm):
        r = bras[k]
        r["p_meilleur"] = round(p, 3)
        r["taux_estime"] = round(stats.moyenne(r[conf["recompense"]], r["essais"], prior), 4)
        r["intervalle_90"] = tuple(round(x, 4) for x in stats.intervalle(r[conf["recompense"]], r["essais"], prior))
    return bras


def allouer(n: int, crm, jour: date | None = None, conf: dict | None = None,
            maintenant: datetime | None = None) -> list[str]:
    """Approche à utiliser pour chacun des n premiers contacts du jour."""
    conf = conf or charger("approches")
    if n <= 0:
        return []
    res = resultats_par_bras(crm, conf, maintenant)
    actifs = [b for b in conf["bras"] if b.get("statut") in ("actif", "champion")]
    if not actifs:
        raise ValueError("aucune approche active dans config/approches.json")
    temoin = next((b["id"] for b in actifs if b.get("temoin")), actifs[0]["id"])
    graine = int((jour or temps.local(maintenant or temps.maintenant()).date()).strftime("%Y%m%d"))
    rng = random.Random(graine)
    prior = conf["prior"]
    choix = []
    for _ in range(n):
        tirages = {}
        for b in actifs:
            r = res[b["id"]]
            a_, b_ = stats.posterieur(r[conf["recompense"]], r["essais"], prior)
            tirages[b["id"]] = rng.betavariate(a_, b_)
        choix.append(max(tirages, key=tirages.get))
    # Parts minimales : le témoin (tant qu'aucun champion n'est prouvé) puis chaque bras actif.
    minimums = {b["id"]: int(round(conf["part_min_bras"] * n)) for b in actifs}
    minimums[temoin] = max(minimums[temoin], int(round(conf["part_min_temoin"] * n)))
    while sum(minimums.values()) > n:
        k = max((k for k in minimums if k != temoin), key=lambda k: minimums[k], default=temoin)
        minimums[k] -= 1
    for bras_id, mini in minimums.items():
        manque = mini - choix.count(bras_id)
        for _ in range(max(0, manque)):
            surplus = max(set(choix), key=lambda k: choix.count(k) - minimums.get(k, 0))
            choix[choix.index(surplus)] = bras_id
    rng.shuffle(choix)
    return choix


def decisions(crm, conf: dict | None = None, maintenant: datetime | None = None) -> list[dict]:
    """Recommandations : champion à promouvoir, bras à retirer, ou continuer."""
    conf = conf or charger("approches")
    res = resultats_par_bras(crm, conf, maintenant)
    sortie = []
    for k, r in res.items():
        if "p_meilleur" not in r:
            continue
        assez = r["essais"] >= conf["essais_min"]
        if assez and r["p_meilleur"] >= conf["seuil_champion"]:
            avis = "champion : à promouvoir comme nouveau témoin"
        elif assez and r["p_meilleur"] <= conf["seuil_retrait"]:
            avis = "à retirer : presque aucune chance d'être le meilleur"
        elif not assez:
            avis = f"continuer : {r['essais']:.0f}/{conf['essais_min']} essais effectifs"
        else:
            avis = "continuer : pas encore concluant"
        sortie.append({"bras": k, "nom": r["bras"]["nom"], "envois": r["envois"], "essais": round(r["essais"], 1),
                       "positives": r["positive"], "reponses": r["reponse"], "rdv": r["rdv"],
                       "taux_estime": r["taux_estime"], "intervalle_90": r["intervalle_90"],
                       "p_meilleur": r["p_meilleur"], "avis": avis})
    return sorted(sortie, key=lambda d: -d["p_meilleur"])

"""Objectifs : l'agent se fixe des cibles, mesure, puis s'ajuste.

Règle : une cible tenue deux semaines de suite (probabilité ≥ 80 % d'être au-dessus) est relevée
d'un pas, sans dépasser un plafond réaliste. Une cible manquée n'est pas baissée : elle déclenche
le diagnostic (on cherche la cause au lieu de baisser la barre)."""
import json
from datetime import datetime, timedelta

from . import stats, temps
from .config import charger


def _chemin(crm):
    return crm.dossier / "objectifs_courants.json"


def cibles_courantes(crm) -> dict:
    base = dict(charger("objectifs")["cibles"])
    chemin = _chemin(crm)
    if chemin.exists():
        base.update(json.loads(chemin.read_text(encoding="utf-8")).get("cibles", {}))
    return base


def bilan_semaine(crm, lundi, cibles: dict | None = None) -> dict:
    from .diagnostic import entonnoir, issues_premiers_contacts
    cibles = cibles or cibles_courantes(crm)
    debut = datetime.combine(lundi, datetime.min.time(), tzinfo=temps.FUSEAU)
    fin = debut + timedelta(days=7)
    lignes = issues_premiers_contacts(crm, live=True, depuis=debut, jusqua=fin)
    etapes = entonnoir(lignes, cibles)
    resultats = {"semaine": lundi.isoformat(), "envois": len(lignes),
                 "envois_atteint": len(lignes) >= cibles.get("envois_semaine", 50)}
    for e in etapes:
        if e["essais"] >= 5 and e.get("cible") is not None:
            p = 1 - e["p_sous_cible"]
            resultats[e["etape"]] = {"taux": round(e["taux"], 4), "essais": e["essais"], "cible": e["cible"],
                                     "p_atteint": round(p, 3), "atteint": p >= 0.8}
    return resultats


def ajuster(crm, aujourdhui=None, appliquer: bool = False) -> dict:
    conf = charger("objectifs")
    cibles = cibles_courantes(crm)
    jour = aujourdhui or temps.local(temps.maintenant()).date()
    lundi = temps.lundi_de(jour)
    s1 = bilan_semaine(crm, lundi - timedelta(days=7), cibles)
    s2 = bilan_semaine(crm, lundi - timedelta(days=14), cibles)
    nouvelles, changements = dict(cibles), []
    for cle, plafond in conf["plafonds"].items():
        r1, r2 = s1.get(cle), s2.get(cle)
        if r1 and r2 and r1["atteint"] and r2["atteint"]:
            proposee = min(plafond, round(cibles[cle] * (1 + conf["pas_relevement"]), 4))
            if proposee > cibles[cle]:
                nouvelles[cle] = proposee
                changements.append(f"{cle} : {stats.pct(cibles[cle])} → {stats.pct(proposee)} "
                                   f"(tenue 2 semaines : {stats.pct(r2['taux'])}, {stats.pct(r1['taux'])})")
    manquees = [f"{cle} : {stats.pct(r['taux'])} pour {stats.pct(r['cible'])} (p atteint {stats.pct(r['p_atteint'], 0)})"
                for cle, r in s1.items() if isinstance(r, dict) and not r["atteint"] and r["p_atteint"] < 0.3]
    if appliquer and changements:
        _chemin(crm).write_text(json.dumps({"cibles": nouvelles, "maj": jour.isoformat(),
                                            "changements": changements}, ensure_ascii=False, indent=2),
                                encoding="utf-8")
        with open(crm.dossier / "objectifs_historique.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"date": jour.isoformat(), "cibles": nouvelles, "changements": changements,
                                "semaine_precedente": s1}, ensure_ascii=False) + "\n")
    return {"cibles": nouvelles, "changements": changements, "manquees_a_diagnostiquer": manquees,
            "semaine_precedente": s1, "semaine_d_avant": s2, "applique": appliquer and bool(changements)}

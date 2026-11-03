"""Le diagnostic : où est l'erreur, avec quelle preuve, et que faire.

1. L'entonnoir, étape par étape (délivrabilité, réponse, qualité des réponses, rendez-vous,
   proposition, closing, récurrence), comparé aux cibles avec une probabilité, pas une impression.
2. Le goulot : l'étape dont la correction rapporterait le plus de clients (théorie des contraintes).
3. Les facteurs : TOUTES les caractéristiques enregistrées (segment, zone, type de boîte, approche,
   jour, créneau, longueur, objet, pièce jointe, prix, origine, score…) sont scannées
   automatiquement ; celles qui expliquent un écart sont classées avec un niveau de preuve corrigé
   du nombre de tests (on ne crie pas victoire sur un hasard).
4. Les causes du catalogue (config/causes.json) : chacune a un test chiffré et un verdict.
5. Le registre des erreurs : ce qui se répète devient une règle ; on mesure que les erreurs baissent.
Les mêmes outils expliquent les réussites : ce qui marche est prouvé de la même façon."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from . import normalise, stats, temps
from .config import charger
from .crm import POSITIVES

ETAPES = [
    # clé, numérateur, dénominateur, libellé
    ("delivrabilite", "delivres", "envoyes", "mails délivrés / envoyés"),
    ("reponse", "reponses", "delivres", "réponses humaines / délivrés"),
    ("positivite", "positives", "reponses", "réponses positives / réponses"),
    ("rdv", "rdv", "positives", "rendez-vous / réponses positives"),
    ("proposition", "propositions", "rdv", "propositions / rendez-vous"),
    ("closing", "gagnes", "propositions", "signés / propositions"),
    ("recurrence", "recurrents", "gagnes", "clients récurrents / signés"),
]
ORDRE_NIVEAUX = {"prouvé": 0, "probable": 1, "piste": 2, "non concluant": 3, "données insuffisantes": 4, "écarté": 5,
                 "mesuré": 0, "conforme": 6}


def _tranche_score(s) -> str:
    if s is None:
        return "inconnu"
    return "≥75" if s >= 75 else "60-74" if s >= 60 else "<60"


def issues_premiers_contacts(crm, live: bool | None = None, depuis: datetime | None = None,
                             jusqua: datetime | None = None) -> list[dict]:
    """Une ligne par prospect ayant reçu un premier contact, avec ses caractéristiques et son issue."""
    lignes = []
    for pid, evs in crm.par_prospect.items():
        premier = next((e for e in evs if e["type"] == "envoye" and (e.get("donnees") or {}).get("etape", 1) == 1
                        and (e.get("donnees") or {}).get("type_envoi", "premier_contact") == "premier_contact"), None)
        if not premier:
            continue
        if live is True and premier.get("historique"):
            continue
        if live is False and not premier.get("historique"):
            continue
        t0 = temps.lire_iso(premier["ts"])
        if (depuis and t0 < depuis) or (jusqua and t0 >= jusqua):
            continue
        p = crm.prospects.get(pid, {})
        sig = p.get("signaux") or {}
        dims = {
            "segment": p.get("segment") or "inconnu",
            "zone": sig.get("zone") or normalise.zone(p.get("ville"), p.get("code_postal")) or "inconnue",
            "type_adresse": (p.get("verif") or {}).get("type") or "inconnu",
            "origine": (p.get("origine") or "inconnue").split("_20")[0],
            "liste_zak": "oui" if p.get("liste_zak") else "non",
            "score_tranche": _tranche_score(p.get("score")),
            "declencheur": "oui" if sig.get("declencheur") else ("non" if sig else "inconnu"),
        }
        for k, v in ((premier.get("donnees") or {}).get("dims") or {}).items():
            if isinstance(v, bool):
                v = "oui" if v else "non"
            dims[k] = str(v)
        reponses = [e for e in evs if e["type"] == "reponse"]
        relances = [e for e in evs if e["type"] == "envoye" and (e.get("donnees") or {}).get("etape", 1) >= 2]
        classe = (reponses[0].get("donnees") or {}).get("classe") if reponses else None
        types = {e["type"] for e in evs}
        lignes.append({
            "prospect": pid, "ts": premier["ts"], "historique": bool(premier.get("historique")), "dims": dims,
            "rebond": "rebond" in types, "auto": "auto_reponse" in types,
            "reponse": bool(reponses), "positive": any((e.get("donnees") or {}).get("classe") in POSITIVES
                                                     for e in reponses),
            "rdv": "rdv" in types, "proposition": "proposition" in types, "gagne": "gagne" in types,
            "recurrent": "recurrent" in types, "classe": classe,
            "apres_relance": bool(reponses and relances and relances[0]["ts"] < reponses[0]["ts"]),
            "delai_reponse_j": ((temps.lire_iso(reponses[0]["ts"]) - t0).total_seconds() / 86400) if reponses else None,
        })
    return sorted(lignes, key=lambda l: l["ts"])


def compter(lignes: list[dict]) -> dict:
    c = {"envoyes": len(lignes), "rebonds": sum(l["rebond"] for l in lignes)}
    c["delivres"] = c["envoyes"] - c["rebonds"]
    for k_src, k in (("reponse", "reponses"), ("positive", "positives"), ("rdv", "rdv"),
                     ("proposition", "propositions"), ("gagne", "gagnes"), ("recurrent", "recurrents")):
        c[k] = sum(1 for l in lignes if l[k_src] and not l["rebond"])
    return c


def entonnoir(lignes: list[dict], cibles: dict) -> list[dict]:
    c = compter(lignes)
    sortie = []
    for cle, num, den, libelle in ETAPES:
        s, n = c[num], c[den]
        cible = cibles.get(cle)
        etape = {"etape": cle, "libelle": libelle, "succes": s, "essais": n, "cible": cible,
                 "taux": (s / n) if n else None}
        if n >= 5:
            etape["estime"] = stats.moyenne(s, n)
            etape["intervalle_90"] = stats.intervalle(s, n)
            if cible is not None:
                etape["p_sous_cible"] = round(1 - stats.proba_au_dessus(s, n, cible), 3)
                etape["statut"] = ("sous la cible" if etape["p_sous_cible"] >= 0.75 else
                                   "conforme" if etape["p_sous_cible"] <= 0.4 else "incertain")
        else:
            etape["statut"] = "données insuffisantes"
        sortie.append(etape)
    return sortie


def goulot(etapes: list[dict]) -> dict | None:
    """Étape dont la remise à la cible multiplierait le plus le nombre de clients, pondérée par la preuve."""
    candidats = []
    for i, e in enumerate(etapes):
        if e.get("statut") != "sous la cible" or not e.get("cible"):
            continue
        facteur = e["cible"] / max(e["estime"], 0.005)
        candidats.append(((facteur - 1) * e["p_sous_cible"], -i, e, facteur))
    if not candidats:
        return None
    impact, _, e, facteur = max(candidats, key=lambda c: (c[0], c[1]))
    return {"etape": e["etape"], "libelle": e["libelle"], "taux": e["estime"], "cible": e["cible"],
            "multiplicateur_si_corrige": round(facteur, 1), "p_sous_cible": e["p_sous_cible"],
            "niveau": stats.niveau_preuve(e["p_sous_cible"], e["essais"] >= 10)}


def facteurs(lignes: list[dict], metrique: str = "reponse", n_min: int = 10, max_niveaux: int = 12) -> list[dict]:
    base = lignes if metrique == "rebond" else [l for l in lignes if not l["rebond"]]
    valeurs = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for l in base:
        for dim, val in l["dims"].items():
            v = valeurs[dim][val]
            v[1] += 1
            v[0] += int(bool(l[metrique]))
    dims_testees = [d for d, vals in valeurs.items()
                    if 2 <= len(vals) <= max_niveaux and sum(1 for s, n in vals.values() if n >= n_min) >= 2]
    resultats = []
    for dim in dims_testees:
        niveaux = [(val, s, n) for val, (s, n) in valeurs[dim].items() if n >= n_min]
        niveaux.sort(key=lambda x: -stats.moyenne(x[1], x[2]))
        (vb, sb, nb), (vw, sw, nw) = niveaux[0], niveaux[-1]
        p = stats.proba_superieur(sb, nb, sw, nw)
        resultats.append({
            "dimension": dim, "metrique": metrique, "p_ecart": round(p, 3),
            "niveau": stats.niveau_preuve(p, True, tests=len(dims_testees)),
            "meilleur": {"valeur": vb, "succes": sb, "essais": nb, "taux": sb / nb},
            "pire": {"valeur": vw, "succes": sw, "essais": nw, "taux": sw / nw},
            "niveaux": [{"valeur": v, "succes": s, "essais": n, "taux": round(s / n, 4)} for v, s, n in niveaux],
        })
    return sorted(resultats, key=lambda r: (ORDRE_NIVEAUX[r["niveau"]], -r["p_ecart"]))


def objections(lignes: list[dict]) -> dict:
    classes = Counter(l["classe"] for l in lignes if l["reponse"] and l["classe"])
    total = sum(classes.values())
    return {"total": total, "classes": dict(classes.most_common()),
            "parts": {k: round(v / total, 3) for k, v in classes.items()} if total else {}}


def _delais_reponse(crm, live: bool = True) -> list[float]:
    """Heures entre une réponse positive du prospect et notre réponse."""
    delais = []
    for pid, evs in crm.par_prospect.items():
        for i, e in enumerate(evs):
            if e["type"] != "reponse" or (live and e.get("historique")):
                continue
            if (e.get("donnees") or {}).get("classe") not in POSITIVES | {"redirection", "pas_compris"}:
                continue
            suite = next((x for x in evs[i + 1:] if x["type"] in ("repondu", "rdv", "proposition")), None)
            if suite:
                delais.append((temps.lire_iso(suite["ts"]) - temps.lire_iso(e["ts"])).total_seconds() / 3600)
            else:
                age = (temps.maintenant() - temps.lire_iso(e["ts"])).total_seconds() / 3600
                delais.append(age)
    return delais


def registre_erreurs(crm, jours: int = 14, maintenant: datetime | None = None) -> dict:
    t = maintenant or temps.maintenant()
    recent = crm.evenements(type_="erreur", depuis=t - timedelta(days=jours))
    avant = [e for e in crm.evenements(type_="erreur", depuis=t - timedelta(days=2 * jours))
             if temps.lire_iso(e["ts"]) < t - timedelta(days=jours)]
    envois_recents = len([e for e in crm.evenements(type_="envoye", live=True, depuis=t - timedelta(days=jours))])
    envois_avant = len([e for e in crm.evenements(type_="envoye", live=True, depuis=t - timedelta(days=2 * jours))
                        if temps.lire_iso(e["ts"]) < t - timedelta(days=jours)])
    regles = {(e.get("donnees") or {}).get("categorie") for e in crm.evenements(type_="regle")}
    cat_r = Counter((e.get("donnees") or {}).get("categorie", "autre") for e in recent)
    cat_a = Counter((e.get("donnees") or {}).get("categorie", "autre") for e in avant)
    lignes = []
    for cat in sorted(set(cat_r) | set(cat_a)):
        lignes.append({
            "categorie": cat, "recent": cat_r[cat], "avant": cat_a[cat],
            "pour_100_envois_recent": round(100 * cat_r[cat] / envois_recents, 1) if envois_recents else None,
            "pour_100_envois_avant": round(100 * cat_a[cat] / envois_avant, 1) if envois_avant else None,
            "regle_existante": cat in regles,
            "a_transformer_en_regle": cat_r[cat] >= 2 and cat not in regles,
        })
    total_r = sum(cat_r.values())
    total_a = sum(cat_a.values())
    return {"jours": jours, "lignes": lignes, "total_recent": total_r, "total_avant": total_a,
            "taux_recent": round(100 * total_r / envois_recents, 1) if envois_recents else None,
            "taux_avant": round(100 * total_a / envois_avant, 1) if envois_avant else None}


def evaluer_causes(crm, lignes: list[dict], etapes: list[dict], cibles: dict, tests_facteurs: dict,
                   maintenant: datetime | None = None) -> list[dict]:
    t = maintenant or temps.maintenant()
    catalogue = charger("causes")["causes"]
    par_etape = {e["etape"]: e for e in etapes}
    obj = objections(lignes)
    conf_garde = charger("garde_fous")
    sortie = []
    for cause in catalogue:
        test = cause["test"]
        typ = test["type"]
        niveau, proba, preuve = "données insuffisantes", None, ""
        if typ == "volume_sous_objectif":
            live = [l for l in lignes if not l["historique"] and temps.lire_iso(l["ts"]) >= t - timedelta(days=7)]
            debut = min((temps.lire_iso(l["ts"]) for l in lignes if not l["historique"]), default=None)
            if debut:
                jours = temps.jours_ouvres_entre(max(debut, t - timedelta(days=7)).date(), t.date())
                attendu = cibles.get("envois_semaine", 50) / 5 * jours
                proba = 1.0 if len(live) < 0.9 * attendu else 0.0
                niveau = "mesuré" if proba else "écarté"
                preuve = f"{len(live)} premiers contacts sur 7 jours glissants pour {attendu:.0f} attendus ({jours} j ouvrés)"
        elif typ == "stock_qualifies":
            seuil = charger("score")["seuil_envoi"]
            stock = sum(1 for pid, p in crm.prospects.items()
                        if crm.etape_courante(pid) == 0 and (p.get("score") or 0) >= seuil and not p.get("exclusions")
                        and crm.etat(pid) in ("qualifie", "pret"))
            besoin = test.get("jours", 3) * conf_garde["paliers_premier_contact"][0]
            proba = 1.0 if stock < besoin else 0.0
            niveau = "mesuré" if proba else "écarté"
            preuve = f"{stock} prospects qualifiés en stock pour {besoin} nécessaires ({test.get('jours', 3)} jours)"
        elif typ == "etape_sous_cible":
            e = par_etape.get(test["etape"], {})
            if e.get("essais", 0) >= 10 and "p_sous_cible" in e:
                proba = e["p_sous_cible"]
                niveau = stats.niveau_preuve(proba, True)
                preuve = (f"{e['libelle']} : {e['succes']}/{e['essais']} = {stats.pct(e['taux'])} "
                          f"(cible {stats.pct(e['cible'], 0)}) ; probabilité d'être sous la cible {stats.pct(proba, 0)}")
            elif e:
                preuve = f"{e.get('libelle')} : {e.get('succes', 0)}/{e.get('essais', 0)} (moins de 10 cas)"
        elif typ == "facteur":
            f = next((x for x in tests_facteurs.get(test["metrique"], []) if x["dimension"] == test["dimension"]), None)
            if f:
                proba, niveau = f["p_ecart"], f["niveau"]
                preuve = " ; ".join(f"{n['valeur']} {stats.pct(n['taux'])} ({n['succes']}/{n['essais']})"
                                    for n in f["niveaux"])
            else:
                preuve = "pas assez de cas dans au moins deux valeurs (10 minimum chacune)"
        elif typ == "part_objection":
            s = sum(obj["classes"].get(k, 0) for k in test["classes"])
            n = obj["total"]
            if n >= 5:
                proba = round(stats.proba_au_dessus(s, n, test["seuil"]), 3)
                niveau = stats.niveau_preuve(proba, True)
                preuve = f"{s}/{n} réponses ({stats.pct(s / n, 0)}) ; seuil d'alerte {stats.pct(test['seuil'], 0)}"
            else:
                preuve = f"{n} réponses classées (5 minimum)"
        elif typ == "note_sceptique":
            notes = [float((e.get("donnees") or {}).get("note", 0)) for e in
                     crm.evenements(type_="controle", depuis=t - timedelta(days=14))]
            if len(notes) >= 5:
                moy = sum(notes) / len(notes)
                proba = 1.0 if moy < test["seuil"] else 0.0
                niveau = "mesuré" if proba else "écarté"
                preuve = f"note moyenne {moy:.2f}/10 sur {len(notes)} relectures (seuil {test['seuil']})"
        elif typ == "delai_reponse":
            d = _delais_reponse(crm)
            if len(d) >= 3:
                lents = sum(1 for x in d if x > test["heures"])
                proba = round(stats.proba_au_dessus(lents, len(d), test["seuil"]), 3)
                niveau = stats.niveau_preuve(proba, True)
                preuve = f"{lents}/{len(d)} réponses à des prospects intéressés données après {test['heures']} h"
        elif typ == "taux_nature":
            natures = set(test["natures"])
            n = len(lignes)
            s = 0
            for l in lignes:
                if l["rebond"]:
                    reb = next((e for e in crm.evenements(l["prospect"], "rebond")), None)
                    if reb and (reb.get("donnees") or {}).get("nature") in natures:
                        s += 1
            if n >= 20:
                proba = round(stats.proba_au_dessus(s, n, test["seuil"]), 3)
                niveau = stats.niveau_preuve(proba, True)
                preuve = (f"{s}/{n} premiers contacts sur des adresses invalides ({stats.pct(s / n)}) ; "
                          f"seuil {stats.pct(test['seuil'], 0)}")
        elif typ == "part_reponses_relances":
            rep = [l for l in lignes if l["reponse"]]
            if len(rep) >= 10:
                s = sum(l["apres_relance"] for l in rep)
                proba = round(1 - stats.proba_au_dessus(s, len(rep), test["seuil"]), 3)
                niveau = stats.niveau_preuve(proba, True)
                preuve = f"{s}/{len(rep)} réponses obtenues après une relance (seuil {stats.pct(test['seuil'], 0)})"
        elif typ == "score_predictif":
            deliv = [l for l in lignes if not l["rebond"]]
            haut = [l for l in deliv if l["dims"]["score_tranche"] == "≥75"]
            bas = [l for l in deliv if l["dims"]["score_tranche"] in ("60-74", "<60")]
            if len(haut) >= 15 and len(bas) >= 15:
                p_sup = stats.proba_superieur(sum(l["reponse"] for l in haut), len(haut),
                                              sum(l["reponse"] for l in bas), len(bas))
                proba = round(1 - p_sup, 3)
                niveau = stats.niveau_preuve(proba, True)
                preuve = (f"score ≥75 : {sum(l['reponse'] for l in haut)}/{len(haut)} réponses ; "
                          f"score <75 : {sum(l['reponse'] for l in bas)}/{len(bas)}")
        elif typ == "erreurs_recurrentes":
            reg = registre_erreurs(crm, test.get("jours", 14), t)
            a_faire = [l["categorie"] for l in reg["lignes"] if l["a_transformer_en_regle"]]
            proba = 1.0 if a_faire else 0.0
            niveau = "mesuré" if a_faire else ("écarté" if reg["total_recent"] or reg["total_avant"] else "données insuffisantes")
            preuve = ("erreurs répétées sans règle : " + ", ".join(a_faire)) if a_faire else "aucune erreur répétée sans règle"
        sortie.append({"id": cause["id"], "famille": cause["famille"], "titre": cause["titre"], "niveau": niveau,
                       "proba": proba, "preuve": preuve, "action": cause["action"]})
    return sorted(sortie, key=lambda c: (ORDRE_NIVEAUX.get(c["niveau"], 9), -(c["proba"] or 0)))


def diagnostiquer(crm, perimetre: str = "auto", cibles: dict | None = None, depuis: datetime | None = None,
                  maintenant: datetime | None = None) -> dict:
    from .objectifs import cibles_courantes
    cibles = cibles or cibles_courantes(crm)
    toutes = issues_premiers_contacts(crm, depuis=depuis)
    live = [l for l in toutes if not l["historique"]]
    if perimetre == "auto":
        perimetre = "live" if len(live) >= 20 else "tout"
    choisies = {"live": live, "historique": [l for l in toutes if l["historique"]], "tout": toutes}[perimetre]
    etapes = entonnoir(choisies, cibles)
    tests = {m: facteurs(toutes, m) for m in ("rebond", "reponse", "positive")}
    causes = evaluer_causes(crm, choisies, etapes, cibles, tests, maintenant)
    succes = [f for f in tests["positive"] + tests["reponse"] if f["niveau"] in ("prouvé", "probable")]
    directives = [c for c in causes if c["niveau"] in ("prouvé", "probable", "mesuré")][:3]
    if len(directives) < 3:
        directives += [c for c in causes if c["niveau"] == "piste"][:3 - len(directives)]
    return {
        "perimetre": perimetre, "n_premiers_contacts": len(choisies), "n_live": len(live),
        "n_historique": len(toutes) - len(live), "cibles": cibles, "entonnoir": etapes, "goulot": goulot(etapes),
        "facteurs": tests, "ce_qui_marche": succes, "objections": objections(choisies), "causes": causes,
        "erreurs": registre_erreurs(crm, maintenant=maintenant), "directives_proposees": directives,
    }

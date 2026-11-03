"""La file du jour : ce que l'agent doit faire, dans l'ordre de priorité.

1. Répondre aux prospects qui ont écrit (vitesse = conversion).
2. Les relances dues (J+3, J+7, J+12 ouvrés), dans le même fil.
3. Les nouveaux premiers contacts, dans la limite du plafond restant : liste de Zak d'abord,
   puis score décroissant ; une seule entité par structure ; approche attribuée par Thompson.
4. Les fiches à compléter (adresse, source, signaux) pour l'Éclaireur."""
from datetime import datetime

from . import experiences, normalise, temps
from .config import charger
from .garde_fou import Garde


def file_du_jour(crm, maintenant: datetime | None = None) -> dict:
    t = maintenant or temps.maintenant()
    garde = Garde(crm, t)
    conf = garde.conf
    jour = temps.local(t).date()
    seuil = charger("score")["seuil_envoi"]

    reponses = [{"prospect": e["prospect"], "nom": crm.prospects[e["prospect"]].get("nom"),
                 "classe": (e.get("donnees") or {}).get("classe"), "recue": e["ts"]}
                for e in crm.reponses_sans_suite()]

    relances = []
    for pid in crm.prospects:
        etape = crm.etape_courante(pid)
        if etape == 0 or etape >= len(conf["sequence_jours_ouvres"]) or crm.a_repondu(pid):
            continue
        if crm.etat(pid) in ("exclu_definitif", "exclu", "adresse_invalide"):
            continue
        premier = crm.premier_envoi(pid)
        if not premier or premier.get("historique"):
            continue
        depart = temps.local(temps.lire_iso(premier["ts"])).date()
        due = temps.ajouter_jours_ouvres(depart, conf["sequence_jours_ouvres"][etape], garde.jours, garde.alsace)
        if due <= jour:
            approche = ((premier.get("donnees") or {}).get("dims") or {}).get("approche")
            relances.append({"prospect": pid, "nom": crm.prospects[pid].get("nom"), "etape": etape + 1,
                             "due": due.isoformat(), "approche": approche,
                             "thread_id": (premier.get("donnees") or {}).get("thread_id")})

    plafond = garde.plafond_premiers_contacts()
    restant_pc = max(0, plafond - garde.premiers_contacts_du_jour())
    restant_total = max(0, conf["plafond_total_jour"] - len(garde.envois_du_jour()) - len(relances))
    places = min(restant_pc, restant_total) if temps.est_ouvre(jour, garde.jours, garde.alsace) else 0

    candidats, a_completer, domaines = [], [], set()
    from .verif import GRATUITS
    for pid, p in crm.prospects.items():
        if crm.etape_courante(pid) > 0 or crm.etat(pid) not in ("qualifie", "pret", "nouveau", "a_qualifier"):
            continue
        manque = [m for m, ok in (("email", p.get("email")), ("source de l'adresse", p.get("email_source")),
                                  ("signaux (recherche de l'Éclaireur)", (p.get("completude") or 0) >= 0.75))
                  if not ok]
        if manque:
            a_completer.append({"prospect": pid, "nom": p.get("nom"), "manque": manque,
                                "liste_zak": bool(p.get("liste_zak"))})
            continue
        if (p.get("score") or 0) < seuil or p.get("exclusions") or (p.get("verif") or {}).get("bloquant"):
            continue
        candidats.append(p)
    candidats.sort(key=lambda p: (not p.get("liste_zak"), -(p.get("score") or 0), p.get("cree_le", "")))
    choisis = []
    for p in candidats:
        dom = normalise.domaine(p["email"])
        cle = dom if dom not in GRATUITS else p["email"]
        if cle in domaines or crm.deja_contacte(p["email"], jours=conf["delai_recontact_jours"], maintenant=t, sauf=p["id"]):
            continue
        domaines.add(cle)
        choisis.append(p)
        if len(choisis) >= places:
            break
    approches = experiences.allouer(len(choisis), crm, jour, maintenant=t)
    nouveaux = [{"prospect": p["id"], "nom": p.get("nom"), "score": p.get("score"), "segment": p.get("segment"),
                 "liste_zak": bool(p.get("liste_zak")), "approche": a} for p, a in zip(choisis, approches)]
    a_completer.sort(key=lambda x: not x["liste_zak"])
    tiedes = []
    for pid, p in crm.prospects.items():
        etat = crm.etat(pid)
        if etat not in ("en_discussion", "rdv", "proposition", "en_veille"):
            continue
        dernier = crm.par_prospect[pid][-1]
        age = (t - temps.lire_iso(dernier["ts"])).days
        tiedes.append({"prospect": pid, "nom": p.get("nom"), "etat": etat, "dernier_echange": dernier["ts"][:10],
                       "jours_sans_nouvelles": age,
                       "a_faire": "relance avec une idée neuve (jamais « je reviens vers vous »)" if age >= 10
                       else "attendre"})
    tiedes.sort(key=lambda x: -x["jours_sans_nouvelles"])
    return {
        "date": jour.isoformat(), "garde": garde.resume(), "places_premier_contact": places,
        "1_reponses_a_traiter": reponses, "2_relances_dues": relances, "3_nouveaux_contacts": nouveaux,
        "4_fiches_a_completer": a_completer[:30],
        "5_leads_tiedes": tiedes, "stock_qualifie_restant": max(0, len(candidats) - len(choisis)),
    }

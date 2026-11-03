"""Comptes rendus pour Zak : quotidien (5 lignes) et hebdomadaire (bilan complet).

Format texte brut (lisible dans Gmail sur téléphone, pas de Markdown)."""
from datetime import timedelta

from . import experiences, objectifs, stats, temps
from .diagnostic import diagnostiquer, issues_premiers_contacts
from .garde_fou import Garde


def quotidien(crm, maintenant=None) -> str:
    t = maintenant or temps.maintenant()
    g = Garde(crm, t)
    r = g.resume()
    jour = temps.local(t).date()
    du_jour = [e for e in crm.evenements(live=True) if temps.local(temps.lire_iso(e["ts"])).date() == jour]
    rep = [e for e in du_jour if e["type"] == "reponse"]
    pos = [e for e in rep if (e.get("donnees") or {}).get("classe") in ("positive", "question_prix")]
    rdv = [e for e in du_jour if e["type"] == "rdv"]
    attente = crm.reponses_sans_suite()
    alertes = []
    if r["pause"]:
        alertes.append("PAUSE active")
    if crm.evenements(type_="limite_envoi", depuis=t - timedelta(days=1)):
        alertes.append("LIMITE D'ENVOI GMAIL signalée : arrêt 24 h")
    if attente:
        alertes.append(f"{len(attente)} réponse(s) de prospect en attente")
    lignes = [
        f"Brooze prospection, {temps.local(t).strftime('%d/%m')} : {r['premiers_contacts']} premiers contacts, "
        f"{r['envois_du_jour']} envois au total (palier {r['palier']}).",
        f"Réponses aujourd'hui : {len(rep)} dont {len(pos)} positive(s) ; rendez-vous pris : {len(rdv)}.",
        f"Santé : bounces {r['bounces_50_derniers']} ; note moyenne du Sceptique "
        f"{r['note_sceptique_moyenne_14j'] if r['note_sceptique_moyenne_14j'] is not None else '—'}/10.",
    ]
    lignes.append("Alerte : " + " ; ".join(alertes) if alertes else "Aucune alerte.")
    return "\n".join(lignes)


def _ligne_etape(e) -> str:
    if e.get("statut") == "données insuffisantes":
        return f"- {e['libelle']} : {e['succes']}/{e['essais']} (pas assez de cas)"
    return (f"- {e['libelle']} : {e['succes']}/{e['essais']} = {stats.pct(e['taux'])} "
            f"(cible {stats.pct(e['cible'], 0)}) : {e['statut']}")


def hebdomadaire(crm, maintenant=None) -> str:
    t = maintenant or temps.maintenant()
    d = diagnostiquer(crm, maintenant=t)
    obj = objectifs.ajuster(crm, temps.local(t).date(), appliquer=False)
    exps = experiences.decisions(crm, maintenant=t)
    semaine = [l for l in issues_premiers_contacts(crm, live=True, depuis=t - timedelta(days=7))]
    L = [f"BILAN HEBDOMADAIRE BROOZE PROSPECTION, semaine du {temps.lundi_de(temps.local(t).date()).strftime('%d/%m')}",
         "",
         f"Périmètre analysé : {d['perimetre']} ({d['n_premiers_contacts']} premiers contacts ; "
         f"{d['n_live']} de l'agent, {d['n_historique']} historiques). Cette semaine : {len(semaine)} premiers contacts.",
         ]
    if d["n_historique"]:
        L.append("Données historiques : zone et segment estimés d'après les noms et les campagnes, relances en partie "
                 "captées. Elles orientent ; seules les mesures de l'agent tranchent.")
    L += ["", "1. L'ENTONNOIR"]
    L += [_ligne_etape(e) for e in d["entonnoir"]]
    g = d["goulot"]
    L += ["", "2. LE GOULOT"]
    L.append(f"{g['libelle']} : {stats.pct(g['taux'])} pour une cible de {stats.pct(g['cible'], 0)}. "
             f"Le corriger multiplierait les clients par {g['multiplicateur_si_corrige']} (preuve : {g['niveau']})."
             if g else "Aucune étape n'est prouvée sous sa cible (ou pas encore assez de données).")
    L += ["", "3. LES CAUSES (avec preuve)"]
    utiles = [c for c in d["causes"] if c["niveau"] in ("prouvé", "probable", "mesuré", "piste")]
    for c in utiles[:6]:
        L.append(f"- [{c['niveau']}] {c['titre']} : {c['preuve']}. → {c['action']}")
    if not utiles:
        L.append("- Rien de prouvé pour l'instant : les volumes sont encore trop faibles pour conclure.")
    L += ["", "4. CE QUI MARCHE (prouvé ou probable)"]
    for f in d["ce_qui_marche"][:4]:
        L.append(f"- {f['dimension']} = {f['meilleur']['valeur']} : {stats.pct(f['meilleur']['taux'])} de "
                 f"{'réponses positives' if f['metrique'] == 'positive' else 'réponses'} "
                 f"({f['meilleur']['succes']}/{f['meilleur']['essais']}) contre {stats.pct(f['pire']['taux'])} pour "
                 f"{f['pire']['valeur']} ({f['niveau']}).")
    if not d["ce_qui_marche"]:
        L.append("- Pas encore de facteur de succès prouvé.")
    L += ["", "5. LES APPROCHES EN TEST"]
    for x in exps:
        L.append(f"- {x['bras']} « {x['nom']} » : {x['envois']} envois, {x['positives']} positive(s), "
                 f"taux estimé {stats.pct(x['taux_estime'])}, {stats.pct(x['p_meilleur'], 0)} de chances d'être la "
                 f"meilleure → {x['avis']}.")
    L += ["", "6. LES ERREURS"]
    er = d["erreurs"]
    L.append(f"{er['total_recent']} erreur(s) sur 14 jours (avant : {er['total_avant']}). "
             + ("Taux pour 100 envois : " + f"{er['taux_recent']} contre {er['taux_avant']}." if er["taux_recent"] is not None and er["taux_avant"] is not None else ""))
    for l in er["lignes"]:
        if l["a_transformer_en_regle"]:
            L.append(f"- {l['categorie']} : {l['recent']} fois → règle à écrire.")
    L += ["", "7. LES OBJECTIFS"]
    L += [f"- relevé : {c}" for c in obj["changements"]] or ["- aucune cible relevée cette semaine."]
    L += [f"- manqué (diagnostic en cours) : {m}" for m in obj["manquees_a_diagnostiquer"]]
    L += ["", "8. DIRECTIVES PROPOSÉES POUR LA SEMAINE"]
    for i, c in enumerate(d["directives_proposees"], 1):
        L.append(f"{i}. {c['action']} (pourquoi : {c['titre'].lower()}, {c['niveau']})")
    if not d["directives_proposees"]:
        L.append("1. Tenir le volume et la qualité : il faut des données avant de changer quoi que ce soit.")
    return "\n".join(L)

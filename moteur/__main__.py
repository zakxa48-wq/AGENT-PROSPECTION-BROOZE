"""Ligne de commande du moteur : python3 -m moteur <commande> [options]

Commandes principales (détail : docs/07-moteur.md) :
  etat                          vue d'ensemble (garde-fou, palier, stock, états)
  importer FICHIER              importer une liste (CSV, XLSX, JSON) ; --zak pour la liste de Zak
  historique FICHIER.json       importer l'historique extrait de Gmail
  verifier-email ADRESSE        vérifier une adresse (syntaxe, type de boîte, MX)
  prospect voir|ajouter|maj     lire ou modifier une fiche
  score ID|--tous               (re)calculer le score
  evenement TYPE ID --json '{}' enregistrer un fait (rédigé, contrôle, réponse, rdv, erreur…)
  peut-envoyer TYPE ID          LE GARDE-FOU : code 0 = autorisé, 2 = refusé
  envoye ID --etape N ...       enregistrer un envoi réel (juste après l'envoi Gmail)
  file                          la file du jour (réponses, relances, nouveaux, fiches à compléter)
  experiences [allouer N]       état des tests d'approches / allocation
  diagnostic [--json]           entonnoir, goulot, facteurs, causes, erreurs
  objectifs [--appliquer]       bilan et relèvement des cibles
  rapport quotidien|hebdo       comptes rendus pour Zak
  regle CATEGORIE "TEXTE"       enregistrer une règle apprise (et la lister avec `regles`)
  calibrer [--appliquer]        recalibrer les poids du score sur les vraies réponses
  coffre ouvrir|fermer          chiffrer / déchiffrer les données
"""
import argparse
import json
import sys

from . import coffre, crm as crm_mod, experiences, importer, objectifs, planificateur, rapport, score, temps, verif
from .config import DOSSIER_CONFIG, charger
from .diagnostic import diagnostiquer
from .garde_fou import Garde


def _json(o) -> str:
    return json.dumps(o, ensure_ascii=False, indent=2, default=str)


def _lire_json(texte: str | None) -> dict:
    if not texte:
        return {}
    if texte.startswith("@"):
        with open(texte[1:], encoding="utf-8") as f:
            return json.load(f)
    return json.loads(texte)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m moteur", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("etat")
    a = sp.add_parser("importer")
    a.add_argument("fichier")
    a.add_argument("--zak", action="store_true", help="liste fournie par Zak (prioritaire)")
    a.add_argument("--origine", default=None)
    a.add_argument("--simulation", action="store_true")
    a.add_argument("--sans-mx", action="store_true")
    a = sp.add_parser("historique")
    a.add_argument("fichier")
    a = sp.add_parser("verifier-email")
    a.add_argument("adresse")
    a.add_argument("--source", default=None)
    a = sp.add_parser("prospect")
    a.add_argument("action", choices=["voir", "ajouter", "maj", "liste"])
    a.add_argument("id", nargs="?")
    a.add_argument("--json", default=None)
    a.add_argument("--etat", default=None)
    a = sp.add_parser("score")
    a.add_argument("id", nargs="?")
    a.add_argument("--tous", action="store_true")
    a = sp.add_parser("evenement")
    a.add_argument("type")
    a.add_argument("id", nargs="?")
    a.add_argument("--json", default=None)
    a = sp.add_parser("peut-envoyer")
    a.add_argument("type", choices=["premier_contact", "relance", "reponse"])
    a.add_argument("id", nargs="?")
    a.add_argument("--etape", type=int, default=None)
    a = sp.add_parser("envoye")
    a.add_argument("id")
    a.add_argument("--type", default="premier_contact", choices=["premier_contact", "relance", "reponse"])
    a.add_argument("--etape", type=int, default=1)
    a.add_argument("--approche", default=None)
    a.add_argument("--message", default=None)
    a.add_argument("--thread", default=None)
    a.add_argument("--objet", default=None)
    a.add_argument("--mots", type=int, default=None)
    a.add_argument("--dims", default=None, help="JSON : objet_type, mention_em, signal…")
    sp.add_parser("file")
    a = sp.add_parser("experiences")
    a.add_argument("action", nargs="?", default="etat", choices=["etat", "allouer"])
    a.add_argument("n", nargs="?", type=int, default=10)
    a = sp.add_parser("diagnostic")
    a.add_argument("--json", action="store_true")
    a.add_argument("--perimetre", default="auto", choices=["auto", "live", "historique", "tout"])
    a = sp.add_parser("objectifs")
    a.add_argument("--appliquer", action="store_true")
    a = sp.add_parser("rapport")
    a.add_argument("type", choices=["quotidien", "hebdo"])
    a = sp.add_parser("regle")
    a.add_argument("categorie")
    a.add_argument("texte")
    sp.add_parser("regles")
    a = sp.add_parser("calibrer")
    a.add_argument("--appliquer", action="store_true")
    a = sp.add_parser("coffre")
    a.add_argument("action", choices=["ouvrir", "fermer"])
    args = ap.parse_args(argv)

    if args.cmd == "coffre":
        print(_json(coffre.ouvrir() if args.action == "ouvrir" else coffre.fermer()))
        return 0
    if args.cmd == "verifier-email":
        print(_json(verif.verifier(args.adresse, args.source)))
        return 0

    c = crm_mod.CRM()

    if args.cmd == "etat":
        from collections import Counter
        etats = Counter(c.etat(pid) for pid in c.prospects)
        print(_json({"garde": Garde(c).resume(), "prospects": len(c.prospects), "evenements": len(c.journal),
                     "etats": dict(etats.most_common()), "reponses_en_attente": len(c.reponses_sans_suite())}))
    elif args.cmd == "importer":
        origine = args.origine or (f"fichier_zak_{temps.local(temps.maintenant()).date()}" if args.zak else "import")
        r = importer.importer(c, args.fichier, origine, liste_zak=args.zak, simulation=args.simulation,
                              mx=not args.sans_mx)
        print(_json({k: (v if not isinstance(v, list) or len(v) <= 15 else v[:15] + [f"… {len(v) - 15} de plus"])
                     for k, v in r.items()}))
        print(f"\nRésumé : {len(r['importes'])} importés, {len(r['doublons_fichier'])} doublons dans le fichier, "
              f"{len(r['doublons_crm'])} déjà connus, {len(r['deja_contactes'])} déjà contactés, "
              f"{len(r['adresses_bloquees'])} adresses bloquées, {len(r['sans_email'])} sans e-mail, "
              f"{len(r['sans_source'])} sans source.")
    elif args.cmd == "historique":
        print(_json(importer.importer_historique(c, args.fichier)))
    elif args.cmd == "prospect":
        if args.action == "liste":
            for pid, p in sorted(c.prospects.items()):
                e = c.etat(pid)
                if not args.etat or e == args.etat:
                    print(f"{pid}\t{e}\t{p.get('score', '—')}\t{p.get('nom')}")
        elif args.action == "voir":
            print(_json({"fiche": c.prospects.get(args.id), "etat": c.etat(args.id), "evenements": c.evenements(args.id)}))
        elif args.action == "ajouter":
            d = _lire_json(args.json)
            if d.get("email"):
                v = verif.verifier(d["email"], d.get("email_source"))
                d["verif"] = {k: v[k] for k in ("type", "gratuit", "mx", "bloquant", "raisons", "avertissements")}
            s = score.calculer(d, c)
            d["score"], d["score_detail"], d["completude"] = s["score"], s["detail"], s["completude"]
            pid, cree = c.ajouter_prospect(d)
            if cree:
                c.evenement("importe", pid, origine=d.get("origine", "eclaireur"))
            c.sauver()
            print(_json({"id": pid, "cree": cree, "score": s}))
        elif args.action == "maj":
            d = _lire_json(args.json)
            p = c.maj_prospect(args.id, **d)
            if "email" in d or "email_source" in d:
                v = verif.verifier(p["email"], p.get("email_source"))
                p["verif"] = {k: v[k] for k in ("type", "gratuit", "mx", "bloquant", "raisons", "avertissements")}
            s = score.calculer(p, c)
            p["score"], p["score_detail"], p["completude"] = s["score"], s["detail"], s["completude"]
            c.evenement("qualifie", args.id, score=s["score"], decision=s["decision"], completude=s["completude"])
            c.sauver()
            print(_json({"fiche": p, "score": s}))
    elif args.cmd == "score":
        ids = list(c.prospects) if args.tous else [args.id]
        for pid in ids:
            s = score.calculer(c.prospects[pid], c)
            c.prospects[pid].update(score=s["score"], score_detail=s["detail"], completude=s["completude"])
            if not args.tous:
                print(_json(s))
        c.sauver()
        if args.tous:
            print(f"{len(ids)} scores recalculés")
    elif args.cmd == "evenement":
        e = c.evenement(args.type, args.id, **_lire_json(args.json))
        if args.type in ("desinscrit", "plainte") and args.id:
            c.prospects[args.id].setdefault("exclusions", []).append("desinscrit")
        c.sauver()
        print(_json(e))
    elif args.cmd == "peut-envoyer":
        v = Garde(c).verifier(args.type, args.id, args.etape)
        print(v.texte())
        return 0 if v.ok else 2
    elif args.cmd == "envoye":
        g = Garde(c)
        v = g.verifier(args.type, args.id, args.etape if args.type == "relance" else None)
        if not v.ok:
            print("ATTENTION : cet envoi n'était pas autorisé par le garde-fou. Il est enregistré comme erreur.\n" + v.texte())
            c.evenement("erreur", args.id, categorie="envoi_non_autorise", description="; ".join(v.raisons))
        e = g.enregistrer_envoi(args.id, args.type, args.etape, args.approche, args.message, args.thread, args.objet,
                                args.mots, _lire_json(args.dims))
        print(_json(e))
    elif args.cmd == "file":
        print(_json(planificateur.file_du_jour(c)))
    elif args.cmd == "experiences":
        if args.action == "allouer":
            print(_json(experiences.allouer(args.n, c)))
        else:
            print(_json(experiences.decisions(c)))
    elif args.cmd == "diagnostic":
        d = diagnostiquer(c, perimetre=args.perimetre)
        if args.json:
            print(_json(d))
        else:
            print(rapport.hebdomadaire(c) if args.perimetre == "auto" else _json(
                {k: d[k] for k in ("perimetre", "entonnoir", "goulot", "causes", "ce_qui_marche", "objections")}))
    elif args.cmd == "objectifs":
        print(_json(objectifs.ajuster(c, appliquer=args.appliquer)))
    elif args.cmd == "rapport":
        print(rapport.quotidien(c) if args.type == "quotidien" else rapport.hebdomadaire(c))
    elif args.cmd == "regle":
        e = c.evenement("regle", None, categorie=args.categorie, texte=args.texte)
        c.sauver()
        print(_json(e))
    elif args.cmd == "regles":
        for e in c.evenements(type_="regle"):
            d = e.get("donnees") or {}
            print(f"[{e['ts'][:10]}] {d.get('categorie')} : {d.get('texte')}")
    elif args.cmd == "calibrer":
        r = score.calibrer(c)
        print(_json(r))
        if args.appliquer:
            if not r.get("poids_proposes") or r["poids_proposes"] == r["poids_actuels"]:
                print("Rien à appliquer.")
            else:
                conf = charger("score")
                conf["poids"] = r["poids_proposes"]
                (DOSSIER_CONFIG / "score.json").write_text(json.dumps(conf, ensure_ascii=False, indent=2) + "\n",
                                                          encoding="utf-8")
                c.evenement("note", None, sujet="recalibrage du score", avant=r["poids_actuels"],
                            apres=r["poids_proposes"], n=r["n"], positifs=r["positifs"])
                c.sauver()
                print("Poids appliqués dans config/score.json (à committer avec la justification).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

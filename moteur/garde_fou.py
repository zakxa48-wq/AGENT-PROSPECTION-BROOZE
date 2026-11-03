"""Le garde-fou : AUCUN envoi sans son accord. Il applique en code les règles de
docs/03-garde-fous.md : arrêt d'urgence, coupe-circuit, jours et fenêtres, plafonds par palier,
espacement, santé des bounces, doublons, source de l'adresse, note du Sceptique, séquence.

Usage par l'agent, avant CHAQUE envoi :  python3 -m moteur peut-envoyer <type> <prospect>
Code de sortie 0 = autorisé, 2 = refusé (avec les raisons)."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import temps
from .config import RACINE, charger, pilotage

TYPES_ENVOI = ("premier_contact", "relance", "reponse")


@dataclass
class Verdict:
    ok: bool
    raisons: list[str] = field(default_factory=list)
    infos: dict = field(default_factory=dict)

    def texte(self) -> str:
        tete = "AUTORISÉ" if self.ok else "REFUSÉ"
        lignes = [tete] + [f"- {r}" for r in self.raisons]
        lignes += [f"  {k} : {v}" for k, v in self.infos.items()]
        return "\n".join(lignes)


class Garde:
    def __init__(self, crm, maintenant: datetime | None = None, conf: dict | None = None):
        self.crm = crm
        self.t = maintenant or temps.maintenant()
        self.loc = temps.local(self.t)
        self.conf = dict(conf or charger("garde_fous"))
        self.pilot = pilotage(crm.dossier)
        self.jours = tuple(self.conf["jours_envoi"])
        self.alsace = self.conf.get("jours_feries_alsace", True)

    # --- mesures ------------------------------------------------------------------------
    def envois_live(self) -> list[dict]:
        return self.crm.evenements(type_="envoye", live=True)

    def envois_du_jour(self) -> list[dict]:
        jour = self.loc.date()
        return [e for e in self.envois_live() if temps.local(temps.lire_iso(e["ts"])).date() == jour]

    def premiers_contacts_du_jour(self) -> int:
        return sum(1 for e in self.envois_du_jour() if (e.get("donnees") or {}).get("etape", 1) == 1
                   and (e.get("donnees") or {}).get("type_envoi", "premier_contact") == "premier_contact")

    def rebonds(self, depuis: datetime | None = None) -> list[dict]:
        return self.crm.evenements(type_="rebond", live=True, depuis=depuis)

    def taux_rebond_50(self) -> tuple[float, int]:
        derniers = [e for e in self.envois_live() if (e.get("donnees") or {}).get("type_envoi") != "reponse"][-50:]
        if not derniers:
            return 0.0, 0
        ids = {e["prospect"] for e in derniers}
        reb = {e["prospect"] for e in self.rebonds() if e["prospect"] in ids}
        return 100 * len(reb) / len(derniers), len(derniers)

    def notes_sceptique(self, jours: int = 14) -> list[float]:
        depuis = self.t - timedelta(days=jours)
        return [float((e.get("donnees") or {}).get("note", 0)) for e in
                self.crm.evenements(type_="controle", live=True, depuis=depuis)]

    def palier(self) -> tuple[int, str]:
        paliers = self.conf["paliers_premier_contact"]
        premiers = [e for e in self.envois_live() if (e.get("donnees") or {}).get("etape", 1) == 1]
        force = self.pilot.get("palier_max")
        if not premiers:
            niveau, raison = 1, "démarrage"
        else:
            debut = temps.local(temps.lire_iso(premiers[0]["ts"])).date()
            jours_ouvres = temps.jours_ouvres_entre(debut, self.loc.date(), self.jours, self.alsace)
            taux, _ = self.taux_rebond_50()
            notes = self.notes_sceptique()
            note_moy = sum(notes) / len(notes) if notes else 0
            plaintes = self.crm.evenements(type_={"plainte", "limite_envoi"}, live=True,
                                           depuis=self.t - timedelta(days=30))
            niveau, raison = 1, f"palier 1 ({jours_ouvres} j ouvrés d'envoi)"
            for n, cle in ((2, "palier_2"), (3, "palier_3")):
                c = self.conf[cle]
                if (jours_ouvres >= c["jours_ouvres_min"] and taux <= c["bounce_max_pct"]
                        and note_moy >= c["note_moyenne_min"] and not plaintes):
                    niveau = n
                    raison = (f"palier {n} : {jours_ouvres} j ouvrés, bounces {taux:.1f} %, "
                              f"note moyenne {note_moy:.1f}, aucune plainte")
        if force and force < niveau:
            niveau, raison = force, f"palier limité à {force} par le maître agent"
        return min(niveau, len(paliers)), raison

    def plafond_premiers_contacts(self) -> int:
        niveau, _ = self.palier()
        return self.conf["paliers_premier_contact"][niveau - 1]

    # --- verdict -----------------------------------------------------------------------
    def verifier(self, type_envoi: str, prospect: str | None = None, etape: int | None = None) -> Verdict:
        if type_envoi not in TYPES_ENVOI:
            return Verdict(False, [f"type d'envoi inconnu : {type_envoi} ({', '.join(TYPES_ENVOI)})"])
        r: list[str] = []
        c = self.conf
        # 1. Arrêt d'urgence et coupe-circuit
        if (RACINE / "PAUSE").exists() or (self.crm.dossier / "PAUSE").exists():
            return Verdict(False, ["fichier PAUSE présent : aucun envoi"])
        limite = self.crm.evenements(type_="limite_envoi", depuis=self.t - timedelta(hours=c["arret_apres_limite_heures"]))
        if limite:
            return Verdict(False, [f"limite d'envoi Gmail signalée le {limite[-1]['ts']} : arrêt total "
                                   f"{c['arret_apres_limite_heures']} h"])
        if type_envoi != "reponse":
            plainte = self.crm.evenements(type_="plainte", depuis=self.t - timedelta(days=c["arret_apres_plainte_jours"]))
            if plainte:
                r.append(f"plainte reçue le {plainte[-1]['ts']} : prospection suspendue "
                         f"{c['arret_apres_plainte_jours']} jours")
        # 2. Jours et fenêtres
        if type_envoi == "reponse":
            if not temps.dans_fenetre(self.loc, *c["fenetre_reponses"]):
                r.append(f"hors fenêtre de réponse ({' – '.join(c['fenetre_reponses'])})")
        else:
            if not temps.est_ouvre(self.loc.date(), self.jours, self.alsace):
                r.append("jour non ouvré (week-end ou férié en Alsace) : pas de prospection")
            elif not any(temps.dans_fenetre(self.loc, d, f) for d, f in c["fenetres_premier_contact"]):
                fen = ", ".join(f"{d}–{f}" for d, f in c["fenetres_premier_contact"])
                r.append(f"hors fenêtre d'envoi ({fen}, heure de Paris)")
        # 3. Plafonds
        du_jour = self.envois_du_jour()
        if type_envoi == "premier_contact":
            plafond = self.plafond_premiers_contacts()
            fait = self.premiers_contacts_du_jour()
            if fait >= plafond:
                r.append(f"plafond de premiers contacts atteint ({fait}/{plafond})")
        if type_envoi != "reponse" and len(du_jour) >= c["plafond_total_jour"]:
            r.append(f"plafond total du jour atteint ({len(du_jour)}/{c['plafond_total_jour']})")
        # 4. Espacement (les réponses à un prospect qui nous écrit restent possibles)
        if type_envoi != "reponse" and du_jour:
            dernier = temps.lire_iso(du_jour[-1]["ts"])
            ecart = (self.t - dernier).total_seconds() / 60
            if ecart < c["espacement_min_minutes"]:
                r.append(f"dernier envoi il y a {ecart:.1f} min (minimum {c['espacement_min_minutes']} min)")
            recents = [e for e in du_jour if (self.t - temps.lire_iso(e["ts"])) <= timedelta(minutes=15)]
            if len(recents) >= c["max_envois_15_minutes"]:
                r.append(f"{len(recents)} envois dans les 15 dernières minutes (maximum {c['max_envois_15_minutes']})")
        # 5. Santé
        if type_envoi != "reponse":
            taux, base = self.taux_rebond_50()
            if base >= 10 and taux > c["bounces_max_pct_50_derniers"] and type_envoi == "premier_contact":
                r.append(f"bounces {taux:.1f} % sur les {base} derniers envois (> {c['bounces_max_pct_50_derniers']} %) : "
                         "nettoyer la file avant tout nouveau contact")
            reb_jour = [e for e in self.rebonds() if temps.local(temps.lire_iso(e["ts"])).date() == self.loc.date()]
            if len(reb_jour) >= c["bounces_max_jour"]:
                r.append(f"{len(reb_jour)} bounces aujourd'hui : envois suspendus jusqu'à demain")
        # 6. Le prospect
        if prospect:
            r += self._verifier_prospect(type_envoi, prospect, etape)
        infos = {"palier": self.palier()[1],
                 "premiers_contacts_aujourdhui": f"{self.premiers_contacts_du_jour()}/{self.plafond_premiers_contacts()}",
                 "envois_aujourdhui": f"{len(du_jour)}/{c['plafond_total_jour']}"}
        return Verdict(not r, r, infos)

    def _verifier_prospect(self, type_envoi: str, pid: str, etape: int | None) -> list[str]:
        r = []
        crm, c = self.crm, self.conf
        p = crm.prospects.get(pid)
        if not p:
            return [f"prospect inconnu : {pid}"]
        etat = crm.etat(pid)
        if etat in ("exclu_definitif", "exclu", "adresse_invalide", "refus", "perdu"):
            if not (type_envoi == "reponse" and etat in ("refus",)):
                r.append(f"prospect dans l'état « {etat} »")
        if not p.get("email"):
            return r + ["aucune adresse e-mail"]
        v = p.get("verif") or {}
        if v.get("bloquant"):
            r.append("adresse bloquée à la vérification : " + "; ".join(v.get("raisons", [])))
        if type_envoi == "reponse":
            return r
        if not p.get("email_source"):
            r.append("source officielle de l'adresse non renseignée")
        from .normalise import domaine
        if domaine(p["email"]) in crm.domaines_exclus():
            r.append("domaine désinscrit (quelqu'un de cette structure a demandé à ne plus être contacté)")
        if p.get("exclusions"):
            r.append("exclusions : " + ", ".join(p["exclusions"]))
        if crm.a_repondu(pid):
            r.append("le prospect a déjà répondu : on lui répond (type « reponse »), on ne le prospecte plus")
        etape_faite = crm.etape_courante(pid)
        if type_envoi == "premier_contact":
            if etape_faite > 0:
                r.append("premier contact déjà envoyé à ce prospect")
            autre = crm.deja_contacte(p["email"], jours=c["delai_recontact_jours"], maintenant=self.t, sauf=pid)
            if autre:
                r.append(f"même adresse ou même structure déjà contactée récemment ({autre})")
            seuil = charger("score")["seuil_envoi"]
            if (p.get("score") or 0) < seuil:
                r.append(f"score {p.get('score', 0)} sous le seuil d'envoi ({seuil})")
            etape_voulue = 1
        else:
            if etape_faite == 0:
                return r + ["aucun premier contact envoyé : pas de relance possible"]
            etape_voulue = etape or etape_faite + 1
            if etape_voulue != etape_faite + 1:
                r.append(f"étape {etape_voulue} demandée, étape attendue {etape_faite + 1}")
            seq = c["sequence_jours_ouvres"]
            if etape_voulue > len(seq):
                return r + ["séquence terminée"]
            premier = crm.premier_envoi(pid)
            depart = temps.local(temps.lire_iso(premier["ts"])).date()
            due = temps.ajouter_jours_ouvres(depart, seq[etape_voulue - 1], self.jours, self.alsace)
            if self.loc.date() < due:
                r.append(f"relance {etape_voulue} prévue le {due.isoformat()}, pas avant")
        # Contrôle du Sceptique sur le texte de cette étape
        redige = [e for e in crm.evenements(pid, "redige") if (e.get("donnees") or {}).get("etape", 1) == etape_voulue]
        if not redige:
            r.append(f"aucun texte rédigé enregistré pour l'étape {etape_voulue}")
        else:
            controles = [e for e in crm.evenements(pid, "controle")
                         if e["ts"] >= redige[-1]["ts"] and (e.get("donnees") or {}).get("etape", 1) == etape_voulue]
            if not controles:
                r.append("texte non relu par le Sceptique")
            elif float((controles[-1].get("donnees") or {}).get("note", 0)) < c["note_sceptique_min"]:
                r.append(f"note du Sceptique {controles[-1]['donnees'].get('note')} < {c['note_sceptique_min']}")
        return r

    # --- après un envoi réel ------------------------------------------------------------
    def enregistrer_envoi(self, prospect: str, type_envoi: str, etape: int, approche: str | None = None,
                          message_id: str | None = None, thread_id: str | None = None, objet: str | None = None,
                          mots: int | None = None, dims: dict | None = None) -> dict:
        d = dict(dims or {})
        d.setdefault("jour", temps.JOURS[self.loc.weekday()])
        d.setdefault("creneau", "matin" if self.loc.hour < 12 else "apres_midi")
        if approche:
            d["approche"] = approche
        if mots:
            d.setdefault("longueur", "<70" if mots < 70 else "70-90" if mots <= 90 else "91-110" if mots <= 110 else ">110")
        type_evt = "repondu" if type_envoi == "reponse" else "envoye"
        e = self.crm.evenement(type_evt, prospect, ts=temps.iso(self.t), type_envoi=type_envoi, etape=etape,
                               message_id=message_id, thread_id=thread_id, objet=objet, mots=mots, dims=d)
        if type_envoi == "reponse":
            # une réponse compte aussi dans les envois du jour (plafond total), sans étape de séquence
            self.crm.evenement("envoye", prospect, ts=temps.iso(self.t), type_envoi="reponse", etape=0, dims=d)
        self.crm.sauver()
        return e

    def resume(self) -> dict:
        taux, base = self.taux_rebond_50()
        niveau, raison = self.palier()
        notes = self.notes_sceptique()
        return {
            "maintenant_paris": self.loc.strftime("%a %d/%m %H:%M"),
            "jour_ouvre": temps.est_ouvre(self.loc.date(), self.jours, self.alsace),
            "palier": niveau, "palier_raison": raison,
            "premiers_contacts": f"{self.premiers_contacts_du_jour()}/{self.plafond_premiers_contacts()}",
            "envois_du_jour": f"{len(self.envois_du_jour())}/{self.conf['plafond_total_jour']}",
            "bounces_50_derniers": f"{taux:.1f} % (sur {base})",
            "note_sceptique_moyenne_14j": round(sum(notes) / len(notes), 2) if notes else None,
            "pause": (RACINE / "PAUSE").exists(),
        }

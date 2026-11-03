"""CRM événementiel : chaque action est un événement daté ; l'état d'un prospect se déduit
de son histoire. C'est ce qui permet au diagnostic de tout ré-analyser après coup.

Tables (dans donnees/) : prospects.jsonl (fiches), evenements.jsonl (journal immuable)."""
import itertools
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from . import normalise, stockage, temps
from .config import dossier_donnees

TYPES = {
    "importe", "qualifie", "exclu", "dossier", "redige", "controle", "envoye", "rebond", "auto_reponse",
    "reponse", "repondu", "relance_planifiee", "rdv", "proposition", "gagne", "perdu", "recurrent",
    "desinscrit", "plainte", "limite_envoi", "erreur", "regle", "note",
}
CLASSES_REPONSE = {
    "positive", "question_prix", "redirection", "deja_videaste", "interne", "pas_moment", "pas_budget",
    "pas_compris", "pas_interesse", "stop", "autre",
}
POSITIVES = {"positive", "question_prix"}
REFUS_DEFINITIFS = {"stop"}
CHAMPS = (
    "nom", "type", "segment", "secteur", "ville", "code_postal", "adresse", "site", "email", "email_source",
    "decideur", "role", "telephone", "instagram", "signaux", "exclusions", "score", "score_detail",
    "origine", "liste_zak", "notes", "extra", "verif", "completude",
)


class CRM:
    def __init__(self, dossier: Path | None = None):
        self.dossier = Path(dossier) if dossier else dossier_donnees()
        self.chemin_prospects = self.dossier / "prospects.jsonl"
        self.chemin_evenements = self.dossier / "evenements.jsonl"
        self.prospects: dict[str, dict] = {p["id"]: p for p in stockage.lire_jsonl(self.chemin_prospects)}
        self.journal: list[dict] = stockage.lire_jsonl(self.chemin_evenements)
        self.journal.sort(key=lambda e: e["ts"])
        self._index()

    # --- index et doublons --------------------------------------------------------------
    def _index(self) -> None:
        self.par_email, self.par_domaine, self.par_tel, self.par_insta = {}, {}, {}, {}
        self.par_prospect: dict[str, list[dict]] = {}
        for p in self.prospects.values():
            self._indexer(p)
        for e in self.journal:
            if e.get("prospect"):
                self.par_prospect.setdefault(e["prospect"], []).append(e)

    def _indexer(self, p: dict) -> None:
        if p.get("email"):
            self.par_email[p["email"]] = p["id"]
            dom = normalise.domaine(p["email"])
            if dom and not (p.get("verif") or {}).get("gratuit"):
                from .verif import GRATUITS
                if dom not in GRATUITS:
                    self.par_domaine.setdefault(dom, p["id"])
        if p.get("site"):
            self.par_domaine.setdefault(normalise.domaine(p["site"]), p["id"])
        if p.get("telephone"):
            self.par_tel[p["telephone"]] = p["id"]
        if p.get("instagram"):
            self.par_insta[p["instagram"]] = p["id"]

    def trouver_doublon(self, p: dict) -> tuple[str, str] | None:
        """(id existant, raison) si l'entité est déjà connue."""
        from .verif import GRATUITS
        e = normalise.email(p.get("email"))
        if e and e in self.par_email:
            return self.par_email[e], "même adresse"
        for source in (e, p.get("site")):
            dom = normalise.domaine(source) if source else ""
            if dom and dom not in GRATUITS and dom in self.par_domaine:
                return self.par_domaine[dom], f"même domaine ({dom})"
        tel = normalise.telephone(p.get("telephone"))
        if tel and tel in self.par_tel:
            return self.par_tel[tel], "même téléphone"
        ig = normalise.instagram(p.get("instagram"))
        if ig and ig in self.par_insta:
            return self.par_insta[ig], "même Instagram"
        if p.get("nom"):
            ville = normalise.nom(p.get("ville"))
            for autre in self.prospects.values():
                sim = normalise.similarite(p["nom"], autre.get("nom", ""))
                meme_ville = ville and ville == normalise.nom(autre.get("ville"))
                if sim >= 0.97 or (meme_ville and sim >= 0.92):
                    return autre["id"], f"nom très proche ({autre.get('nom')}, similarité {sim})"
        return None

    # --- écriture -------------------------------------------------------------------------
    def _nouvel_id(self, p: dict) -> str:
        from .verif import GRATUITS
        dom = normalise.domaine(p.get("site") or p.get("email") or "")
        base = normalise.slug(dom if dom and dom not in GRATUITS else f"{p.get('nom', '')}-{p.get('ville', '')}")
        ident = f"p-{base}"
        for n in itertools.count(2):
            if ident not in self.prospects:
                return ident
            ident = f"p-{base}-{n}"
        return ident

    def ajouter_prospect(self, donnees: dict, autoriser_doublon: bool = False) -> tuple[str, bool]:
        """Retourne (id, cree). Si doublon : (id existant, False)."""
        doublon = None if autoriser_doublon else self.trouver_doublon(donnees)
        if doublon:
            return doublon[0], False
        p = {k: donnees[k] for k in CHAMPS if k in donnees and donnees[k] not in (None, "", [], {})}
        if p.get("email"):
            p["email"] = normalise.email(p["email"])
        p["id"] = donnees.get("id") or self._nouvel_id(p)
        p["cree_le"] = donnees.get("cree_le") or temps.iso(temps.maintenant())
        self.prospects[p["id"]] = p
        self._indexer(p)
        return p["id"], True

    def maj_prospect(self, ident: str, **champs) -> dict:
        p = self.prospects[ident]
        for k, v in champs.items():
            if k in CHAMPS:
                if v in (None, ""):
                    p.pop(k, None)
                else:
                    p[k] = v
        self._indexer(p)
        return p

    def evenement(self, type_: str, prospect: str | None = None, ts: str | None = None,
                  historique: bool = False, **donnees) -> dict:
        if type_ not in TYPES:
            raise ValueError(f"type d'événement inconnu : {type_} (connus : {', '.join(sorted(TYPES))})")
        if prospect and prospect not in self.prospects:
            raise KeyError(f"prospect inconnu : {prospect}")
        if type_ == "reponse" and donnees.get("classe") not in CLASSES_REPONSE:
            raise ValueError(f"classe de réponse inconnue (attendu : {', '.join(sorted(CLASSES_REPONSE))})")
        e = {"id": uuid.uuid4().hex[:12], "ts": ts or temps.iso(temps.maintenant()), "type": type_}
        if prospect:
            e["prospect"] = prospect
        if historique:
            e["historique"] = True
        if donnees:
            e["donnees"] = donnees
        self.journal.append(e)
        self.journal.sort(key=lambda x: x["ts"])
        if prospect:
            self.par_prospect.setdefault(prospect, []).append(e)
            self.par_prospect[prospect].sort(key=lambda x: x["ts"])
        self._nouveaux = getattr(self, "_nouveaux", []) + [e]
        return e

    def sauver(self) -> None:
        stockage.ecrire_jsonl(self.chemin_prospects, sorted(self.prospects.values(), key=lambda p: p["id"]))
        stockage.ecrire_jsonl(self.chemin_evenements, self.journal)
        self._nouveaux = []

    # --- lecture --------------------------------------------------------------------------
    def evenements(self, prospect: str | None = None, type_: str | set | None = None,
                   depuis: datetime | None = None, live: bool | None = None) -> list[dict]:
        source = self.par_prospect.get(prospect, []) if prospect else self.journal
        types = {type_} if isinstance(type_, str) else type_
        sortie = []
        for e in source:
            if types and e["type"] not in types:
                continue
            if live is True and e.get("historique"):
                continue
            if live is False and not e.get("historique"):
                continue
            if depuis and temps.lire_iso(e["ts"]) < depuis:
                continue
            sortie.append(e)
        return sortie

    def premier_envoi(self, prospect: str) -> dict | None:
        for e in self.par_prospect.get(prospect, []):
            if e["type"] == "envoye" and (e.get("donnees") or {}).get("etape", 1) == 1:
                return e
        return None

    def etape_courante(self, prospect: str) -> int:
        etapes = [(e.get("donnees") or {}).get("etape", 1) for e in self.par_prospect.get(prospect, [])
                  if e["type"] == "envoye"]
        return max(etapes, default=0)

    def a_repondu(self, prospect: str) -> bool:
        return any(e["type"] == "reponse" for e in self.par_prospect.get(prospect, []))

    def reponses_sans_suite(self) -> list[dict]:
        """Réponses humaines arrivées après notre dernier message : à traiter en priorité 1."""
        attente = []
        for pid, evs in self.par_prospect.items():
            derniere_rep, notre_dernier = None, None
            for e in evs:
                if e["type"] == "reponse":
                    derniere_rep = e
                elif e["type"] in ("repondu", "envoye", "proposition", "rdv"):
                    notre_dernier = e
            if derniere_rep and derniere_rep.get("historique"):
                continue  # les réponses passées sont suivies comme leads tièdes (planificateur), pas comme urgences
            if derniere_rep and (not notre_dernier or notre_dernier["ts"] < derniere_rep["ts"]):
                if (derniere_rep.get("donnees") or {}).get("classe") not in REFUS_DEFINITIFS:
                    attente.append(derniere_rep)
        return sorted(attente, key=lambda e: e["ts"])

    def etat(self, prospect: str, maintenant: datetime | None = None) -> str:
        evs = self.par_prospect.get(prospect, [])
        types = {e["type"] for e in evs}
        if types & {"desinscrit", "plainte"}:
            return "exclu_definitif"
        if "recurrent" in types:
            return "client_recurrent"
        if "gagne" in types:
            return "client"
        if "perdu" in types:
            return "perdu"
        if "proposition" in types:
            return "proposition"
        if "rdv" in types:
            return "rdv"
        reponses = [e for e in evs if e["type"] == "reponse"]
        if reponses:
            classe = (reponses[-1].get("donnees") or {}).get("classe")
            if classe in POSITIVES or classe == "redirection":
                return "en_discussion"
            if classe == "pas_moment":
                return "en_veille"
            if classe in ("stop",):
                return "exclu_definitif"
            return "refus"
        if "exclu" in types:
            return "exclu"
        if any(e["type"] == "rebond" for e in evs):
            return "adresse_invalide"
        if "envoye" in types:
            etape = self.etape_courante(prospect)
            return "sequence_terminee" if etape >= 4 else f"en_sequence_{etape}"
        p = self.prospects.get(prospect, {})
        if "controle" in types and "redige" in types:
            return "pret"
        if p.get("score") is not None:
            from .config import charger
            if p["score"] >= charger("score")["seuil_envoi"]:
                return "qualifie"
            # Score bas parce que les signaux ne sont pas encore recherchés : à qualifier, pas écarté.
            return "a_qualifier" if (p.get("completude") or 0) < 0.75 else "ecarte"
        return "nouveau"

    def deja_contacte(self, email: str = "", domaine: str = "", jours: int = 180,
                      maintenant: datetime | None = None, sauf: str | None = None) -> str | None:
        """Id du prospect déjà contacté (même adresse ou même domaine pro) depuis `jours`."""
        from .verif import GRATUITS
        limite = (maintenant or temps.maintenant()) - timedelta(days=jours)
        email = normalise.email(email)
        domaine = normalise.domaine(domaine or email)
        for pid, p in self.prospects.items():
            if pid == sauf:
                continue
            meme = (email and p.get("email") == email) or (
                domaine and domaine not in GRATUITS and domaine in
                {normalise.domaine(p.get("email", "")), normalise.domaine(p.get("site", ""))})
            if not meme:
                continue
            for e in self.par_prospect.get(pid, []):
                if e["type"] == "envoye" and temps.lire_iso(e["ts"]) >= limite:
                    return pid
                if e["type"] in ("desinscrit", "plainte"):
                    return pid
        return None

    def domaines_exclus(self) -> set[str]:
        """Domaines pro dont quelqu'un a demandé à ne plus être contacté."""
        from .verif import GRATUITS
        sortie = set()
        for e in self.journal:
            if e["type"] in ("desinscrit", "plainte") or (
                    e["type"] == "reponse" and (e.get("donnees") or {}).get("classe") == "stop"):
                p = self.prospects.get(e.get("prospect"), {})
                dom = normalise.domaine(p.get("email", ""))
                if dom and dom not in GRATUITS:
                    sortie.add(dom)
        return sortie

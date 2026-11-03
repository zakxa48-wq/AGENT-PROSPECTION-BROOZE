"""Import d'une liste de prospects (CSV, TSV, XLSX, JSON) : reconnaissance des colonnes,
normalisation, vérification des adresses, dédoublonnage (dans le fichier et contre le CRM),
rapport détaillé. Rien n'est envoyé : l'import prépare seulement la file."""
import csv
import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from . import normalise, score, verif

SYNONYMES = {
    "nom": ["nom", "entreprise", "societe", "structure", "organisation", "raison sociale", "name", "company",
            "enseigne", "marque", "etablissement", "nom entreprise", "nom de la structure", "client"],
    "email": ["email", "e mail", "mail", "courriel", "adresse mail", "adresse email", "adresse e mail",
              "email contact", "contact email"],
    "site": ["site", "site web", "site internet", "website", "url", "web", "lien"],
    "ville": ["ville", "city", "commune", "localite", "localisation"],
    "code_postal": ["cp", "code postal", "zip", "postal"],
    "adresse": ["adresse", "address", "rue", "adresse postale"],
    "telephone": ["telephone", "tel", "phone", "portable", "mobile", "numero"],
    "decideur": ["decideur", "contact", "nom du contact", "prenom", "responsable", "gerant", "dirigeant",
                 "interlocuteur", "fondateur", "fondatrice", "personne"],
    "role": ["poste", "fonction", "role", "titre"],
    "secteur": ["secteur", "activite", "categorie", "type", "industrie", "domaine", "metier"],
    "instagram": ["instagram", "insta", "ig", "compte instagram"],
    "notes": ["notes", "note", "commentaire", "commentaires", "remarques", "pourquoi", "angle", "info",
              "infos", "observation", "idee"],
    "email_source": ["source", "source email", "source adresse", "origine", "trouve sur"],
    "segment": ["segment"],
}

SEGMENTS_MOTS = {
    "A": ["restaurant", "resto", "bar", "cafe", "brasserie", "bistrot", "salle", "sport", "fitness", "yoga", "pilates",
          "escalade", "loisir", "escape", "hotel", "spa", "bien etre", "coiffure", "barbier", "institut", "danse",
          "boxe", "crossfit", "bowling", "cinema", "traiteur", "food"],
    "B": ["artisan", "boulangerie", "patisserie", "chocolat", "bijou", "ceramique", "fleur", "fleuriste", "epicerie",
          "createur", "createurs", "atelier", "boutique", "caviste", "vin", "torrefacteur", "fromager", "mode",
          "concept store", "papeterie", "librairie"],
    "C": ["association", "asso", "festival", "theatre", "culture", "culturel", "club", "musee", "marche",
          "evenement", "ong", "fondation", "compagnie"],
    "D": ["formation", "ecole", "cfa", "cabinet", "immobilier", "agence immobiliere", "industrie", "pme", "conseil",
          "avocat", "expert", "clinique", "auto ecole", "b2b", "logistique", "btp"],
    "E": ["startup", "start up", "marque", "e commerce", "ecommerce", "dtc", "d2c", "application", "saas"],
}


def _cle(texte: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", normalise.sans_accents(str(texte)).lower())).strip()


def mapper_colonnes(entetes: list[str]) -> dict[str, str]:
    """{entête du fichier: champ} ; exact d'abord, puis inclusion."""
    mapping, pris = {}, set()
    cles = {h: _cle(h) for h in entetes}
    for passe in ("exact", "inclus"):
        for h, k in cles.items():
            if h in mapping:
                continue
            for champ, syns in SYNONYMES.items():
                if champ in pris:
                    continue
                if (passe == "exact" and k in syns) or (passe == "inclus" and any(
                        re.search(rf"\b{re.escape(s)}\b", k) for s in syns if len(s) > 2)):
                    mapping[h] = champ
                    pris.add(champ)
                    break
    return mapping


def _lire_xlsx_minimal(chemin: Path) -> list[list[str]]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(chemin) as z:
        partages = []
        if "xl/sharedStrings.xml" in z.namelist():
            racine = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
            for si in racine.findall("m:si", ns):
                partages.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
        feuilles = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))
        racine = ElementTree.fromstring(z.read(feuilles[0]))
    lignes = []
    for row in racine.iter(f"{{{ns['m']}}}row"):
        valeurs = {}
        for c in row.findall("m:c", ns):
            ref = c.get("r", "")
            col = 0
            for ch in re.match(r"[A-Z]+", ref).group(0):
                col = col * 26 + ord(ch) - 64
            v = c.find("m:v", ns)
            texte = ""
            if c.get("t") == "s" and v is not None:
                texte = partages[int(v.text)]
            elif c.get("t") == "inlineStr":
                texte = "".join(t.text or "" for t in c.iter(f"{{{ns['m']}}}t"))
            elif v is not None:
                texte = v.text or ""
            valeurs[col - 1] = texte
        if valeurs:
            lignes.append([valeurs.get(i, "") for i in range(max(valeurs) + 1)])
    return lignes


def lire_tableau(chemin: str | Path) -> list[dict]:
    chemin = Path(chemin)
    suffixe = chemin.suffix.lower()
    if suffixe == ".json":
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        return donnees if isinstance(donnees, list) else donnees.get("prospects", [])
    if suffixe in (".xlsx", ".xlsm"):
        try:
            import openpyxl
            feuille = openpyxl.load_workbook(chemin, read_only=True, data_only=True).worksheets[0]
            lignes = [["" if v is None else str(v) for v in row] for row in feuille.iter_rows(values_only=True)]
        except ImportError:
            lignes = _lire_xlsx_minimal(chemin)
    else:
        brut = chemin.read_bytes()
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                texte = brut.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        try:
            dialecte = csv.Sniffer().sniff(texte[:5000], delimiters=",;\t|")
        except csv.Error:
            dialecte = csv.excel
        lignes = list(csv.reader(io.StringIO(texte), dialecte))
    lignes = [l for l in lignes if any(str(c).strip() for c in l)]
    if not lignes:
        return []
    entetes = [str(h).strip() for h in lignes[0]]
    return [{entetes[i]: str(v).strip() for i, v in enumerate(l) if i < len(entetes)} for l in lignes[1:]]


def deviner_segment(secteur: str, nom: str = "") -> str | None:
    texte = " " + _cle(f"{secteur} {nom}") + " "
    for seg in ("C", "D", "E", "B", "A"):
        if any(f" {m} " in texte for m in SEGMENTS_MOTS[seg]):
            return seg
    return None


def preparer(ligne: dict, mapping: dict[str, str]) -> dict:
    p, extra = {}, {}
    for h, v in ligne.items():
        if not v:
            continue
        champ = mapping.get(h)
        if champ:
            p[champ] = v
        else:
            extra[h] = v
    if extra:
        p["extra"] = extra
    if p.get("email"):
        trouvees = re.findall(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+", p["email"])
        p["email"] = normalise.email(trouvees[0] if trouvees else p["email"])
    if p.get("site"):
        p["site"] = normalise.url(p["site"])
    if p.get("telephone"):
        p["telephone"] = normalise.telephone(p["telephone"])
    if p.get("instagram"):
        p["instagram"] = normalise.instagram(p["instagram"])
    if not p.get("nom"):
        p["nom"] = normalise.domaine(p.get("site") or p.get("email") or "") or "sans nom"
    if not p.get("segment"):
        seg = deviner_segment(p.get("secteur", ""), p.get("nom", ""))
        if seg:
            p["segment"] = seg
    if not p.get("email_source") and p.get("site") and p.get("email"):
        if normalise.domaine(p["email"]) == normalise.domaine(p["site"]):
            p["email_source"] = p["site"] + " (domaine du site, à confirmer sur la page contact)"
    zone = normalise.zone(p.get("ville"), p.get("code_postal"))
    p["signaux"] = {"zone": zone} if zone else {}
    return p


def importer(crm, chemin: str | Path, origine: str, liste_zak: bool = False, simulation: bool = False,
             mx: bool = True) -> dict:
    lignes = lire_tableau(chemin)
    entetes = list(lignes[0].keys()) if lignes else []
    mapping = mapper_colonnes(entetes)
    rapport = {"fichier": str(chemin), "lignes": len(lignes), "colonnes": mapping,
               "colonnes_ignorees": [h for h in entetes if h not in mapping],
               "importes": [], "doublons_fichier": [], "doublons_crm": [], "deja_contactes": [],
               "adresses_bloquees": [], "sans_email": [], "sans_source": [], "simulation": simulation}
    vus = {}
    for numero, ligne in enumerate(lignes, 2):
        p = preparer(ligne, mapping)
        cle = p.get("email") or normalise.domaine(p.get("site", "")) or normalise.nom(p.get("nom"))
        if cle in vus:
            rapport["doublons_fichier"].append({"ligne": numero, "nom": p["nom"], "comme_ligne": vus[cle]})
            continue
        vus[cle] = numero
        doublon = crm.trouver_doublon(p)
        if doublon:
            entree = {"ligne": numero, "nom": p["nom"], "existant": doublon[0], "raison": doublon[1]}
            if crm.etape_courante(doublon[0]) > 0:
                rapport["deja_contactes"].append(entree)
            else:
                rapport["doublons_crm"].append(entree)
            continue
        if p.get("email"):
            v = verif.verifier(p["email"], p.get("email_source"), mx=mx)
            p["verif"] = {k: v[k] for k in ("type", "gratuit", "mx", "bloquant", "raisons", "avertissements")}
            if v["correction"]:
                p["verif"]["correction"] = v["correction"]
            if v["bloquant"]:
                rapport["adresses_bloquees"].append({"ligne": numero, "nom": p["nom"], "email": p["email"],
                                                     "raisons": v["raisons"]})
        else:
            rapport["sans_email"].append({"ligne": numero, "nom": p["nom"]})
        if p.get("email") and not p.get("email_source"):
            rapport["sans_source"].append({"ligne": numero, "nom": p["nom"]})
        p["origine"] = origine
        if liste_zak:
            p["liste_zak"] = True
        s = score.calculer(p, crm)
        p["score"], p["score_detail"], p["completude"] = s["score"], s["detail"], s["completude"]
        if s["exclusions"]:
            p["exclusions"] = s["exclusions"]
        if not simulation:
            pid, _ = crm.ajouter_prospect(p)
            crm.evenement("importe", pid, origine=origine, fichier=Path(chemin).name, ligne=numero)
        else:
            pid = "(simulation)"
        rapport["importes"].append({"ligne": numero, "id": pid, "nom": p["nom"], "score": s["score"],
                                    "completude": s["completude"], "segment": p.get("segment")})
    if not simulation:
        crm.sauver()
    return rapport


def importer_historique(crm, chemin: str | Path) -> dict:
    """Historique extrait de Gmail (voir docs/07-moteur.md) : une entrée par entité contactée.
    Format : {"email","nom","date_premier","envois":[dates],"issue","classe","date_reponse","rdv","segment","zone","ville"}"""
    entrees = json.loads(Path(chemin).read_text(encoding="utf-8"))
    bilan = {"entrees": len(entrees), "crees": 0, "fusionnes": 0}
    for h in entrees:
        p = {"nom": h.get("nom") or normalise.domaine(h["email"]), "email": h["email"],
             "origine": "historique", "segment": h.get("segment"), "ville": h.get("ville"),
             "email_source": h.get("email_source") or "historique Gmail"}
        v = verif.verifier(h["email"], p["email_source"], mx=False)
        p["verif"] = {k: v[k] for k in ("type", "gratuit", "mx", "bloquant", "raisons", "avertissements")}
        p["signaux"] = {"zone": h.get("zone")} if h.get("zone") else {}
        pid, cree = crm.ajouter_prospect(p)
        bilan["crees" if cree else "fusionnes"] += 1
        if any(e.get("historique") for e in crm.evenements(pid)):
            continue
        dims = dict(h.get("dims") or {})
        for i, d in enumerate(sorted(h.get("envois") or [h["date_premier"]]), 1):
            crm.evenement("envoye", pid, ts=d, historique=True, etape=min(i, 4), type_envoi="premier_contact"
                          if i == 1 else "relance", dims=dims if i == 1 else {})
        issue = h.get("issue", "aucune")
        dr = h.get("date_reponse") or h["date_premier"]
        if issue == "rebond":
            crm.evenement("rebond", pid, ts=dr, historique=True, nature=h.get("nature_echec", "inconnue"),
                          preuve=h.get("preuve"))
        elif issue == "auto":
            crm.evenement("auto_reponse", pid, ts=dr, historique=True)
        elif issue == "reponse":
            crm.evenement("reponse", pid, ts=dr, historique=True, classe=h.get("classe", "autre"))
        for cle in ("rdv", "proposition"):
            if h.get(cle):
                crm.evenement(cle, pid, ts=h[cle], historique=True)
        if h.get("perdu"):
            crm.evenement("perdu", pid, ts=h["perdu"]["date"], historique=True, raison=h["perdu"]["raison"])
    crm.sauver()
    return bilan

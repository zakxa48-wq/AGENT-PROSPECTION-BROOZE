"""Vérification d'une adresse avant tout envoi : syntaxe, type de boîte, fautes de frappe,
domaines jetables, et enregistrement MX (requête DNS directe, sans dépendance).

Principe : une adresse douteuse coûte plus cher qu'un prospect perdu (un bounce abîme la
réputation de tout le domaine broozeproduction.fr)."""
import random
import re
import socket
import struct

from . import normalise

GUICHETS = {
    "sav", "support", "serviceclient", "service-client", "client", "clients", "noreply", "no-reply",
    "nepasrepondre", "ne-pas-repondre", "donotreply", "rh", "recrutement", "jobs", "job", "carriere",
    "carrieres", "candidature", "compta", "comptabilite", "facturation", "factures", "facture", "billing",
    "invoice", "invoices", "legal", "juridique", "dpo", "rgpd", "privacy", "abuse", "postmaster",
    "webmaster", "hostmaster", "admin", "root", "newsletter", "notifications", "notification", "mailer",
    "unsubscribe", "bounce", "ticket", "tickets", "helpdesk", "hotline", "achats", "achat", "fournisseurs",
}
GENERIQUES = {
    "contact", "contacts", "info", "infos", "information", "informations", "hello", "hey", "bonjour",
    "salut", "accueil", "reception", "reservation", "reservations", "resa", "booking", "commande",
    "commandes", "shop", "boutique", "store", "team", "equipe", "office", "bureau", "secretariat",
    "direction", "communication", "com", "presse", "press", "media", "medias", "partenariat",
    "partenariats", "partners", "asso", "association", "mail", "email", "general", "atelier", "studio",
    "marketing", "pro", "events", "evenements", "event", "ecole", "formation", "administration",
}
GRATUITS = {
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.fr", "outlook.com", "outlook.fr", "live.fr",
    "live.com", "msn.com", "yahoo.fr", "yahoo.com", "orange.fr", "wanadoo.fr", "free.fr", "sfr.fr",
    "neuf.fr", "laposte.net", "icloud.com", "me.com", "gmx.fr", "gmx.com", "gmx.de", "aol.com",
    "bbox.fr", "proton.me", "protonmail.com", "numericable.fr", "club-internet.fr", "aliceadsl.fr",
}
JETABLES = {
    "yopmail.com", "yopmail.fr", "mailinator.com", "guerrillamail.com", "10minutemail.com",
    "tempmail.com", "temp-mail.org", "trashmail.com", "jetable.org", "throwawaymail.com",
}
FAUTES = {
    "gmial.com": "gmail.com", "gmai.com": "gmail.com", "gnail.com": "gmail.com", "gmail.co": "gmail.com",
    "gmail.fr": "gmail.com", "gamil.com": "gmail.com", "gmaill.com": "gmail.com", "gmail.con": "gmail.com",
    "hotmial.com": "hotmail.com", "hotmail.con": "hotmail.com", "hotmal.fr": "hotmail.fr",
    "outlok.fr": "outlook.fr", "outook.com": "outlook.com", "yahou.fr": "yahoo.fr", "yaho.fr": "yahoo.fr",
    "orage.fr": "orange.fr", "oragne.fr": "orange.fr", "wanado.fr": "wanadoo.fr", "lapost.net": "laposte.net",
}
MOTIF = re.compile(r"^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
                   r"([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")


def type_boite(adresse: str) -> str:
    """nominative | generique | guichet | perso (fournisseur gratuit, souvent lu par le patron)."""
    locale, _, dom = adresse.partition("@")
    jetons = [j for j in re.split(r"[._+\-]", locale) if j]
    if locale in GUICHETS or any(j in GUICHETS for j in jetons):
        return "guichet"
    if locale in GENERIQUES or (jetons and jetons[0] in GENERIQUES):
        return "perso" if dom in GRATUITS else "generique"
    if dom in GRATUITS:
        return "perso"
    return "nominative"


def verifier(adresse: str, source: str | None = None, mx: bool = True) -> dict:
    a = normalise.email(adresse)
    res = {"email": a, "domaine": normalise.domaine(a), "valide": False, "bloquant": True,
           "raisons": [], "avertissements": [], "type": None, "gratuit": False, "mx": None,
           "correction": None, "source": source or None}
    if not a:
        res["raisons"].append("adresse vide")
        return res
    if not MOTIF.match(a) or ".." in a:
        res["raisons"].append("syntaxe invalide")
        return res
    res["valide"] = True
    dom = res["domaine"]
    if dom in FAUTES:
        res["correction"] = a.split("@")[0] + "@" + FAUTES[dom]
        res["raisons"].append(f"faute de frappe probable dans le domaine ({dom} → {FAUTES[dom]})")
    if dom in JETABLES:
        res["raisons"].append("domaine jetable")
    res["gratuit"] = dom in GRATUITS
    res["type"] = type_boite(a)
    if res["type"] == "guichet":
        res["raisons"].append("guichet (support, facturation, RH…) : jamais un décideur")
    if not source:
        res["avertissements"].append("source officielle non renseignée : envoi interdit tant qu'elle manque")
    if mx and not res["gratuit"] and not res["raisons"]:
        etat = verifier_mx(dom)
        res["mx"] = etat
        if etat is False:
            res["raisons"].append("le domaine ne reçoit pas d'e-mail (aucun MX ou domaine inexistant)")
        elif etat is None:
            res["avertissements"].append("MX non vérifiable depuis cet environnement")
    elif res["gratuit"]:
        res["mx"] = True
    res["bloquant"] = bool(res["raisons"])
    return res


# --- Requête DNS MX minimale (RFC 1035) -------------------------------------------------

def construire_requete(dom: str, ident: int | None = None, qtype: int = 15) -> bytes:
    ident = random.randint(0, 0xFFFF) if ident is None else ident
    entete = struct.pack(">HHHHHH", ident, 0x0100, 1, 0, 0, 0)
    question = b"".join(bytes([len(p)]) + p.encode("idna") for p in dom.strip(".").split(".")) + b"\x00"
    return entete + question + struct.pack(">HH", qtype, 1)


def _lire_nom(paquet: bytes, pos: int) -> tuple[str, int]:
    etiquettes, saute, fin = [], False, pos
    for _ in range(128):
        n = paquet[pos]
        if n == 0:
            pos += 1
            break
        if n & 0xC0 == 0xC0:
            cible = struct.unpack(">H", paquet[pos:pos + 2])[0] & 0x3FFF
            if not saute:
                fin = pos + 2
            saute, pos = True, cible
            continue
        etiquettes.append(paquet[pos + 1:pos + 1 + n].decode("ascii", "replace"))
        pos += 1 + n
    return ".".join(etiquettes), (fin if saute else pos)


def analyser_reponse(paquet: bytes) -> tuple[int, list[tuple[int, str]]]:
    """Retourne (rcode, [(préférence, serveur)])."""
    _, drapeaux, qd, an, _, _ = struct.unpack(">HHHHHH", paquet[:12])
    rcode = drapeaux & 0x000F
    pos = 12
    for _ in range(qd):
        _, pos = _lire_nom(paquet, pos)
        pos += 4
    mx = []
    for _ in range(an):
        _, pos = _lire_nom(paquet, pos)
        rtype, _, _, longueur = struct.unpack(">HHIH", paquet[pos:pos + 10])
        pos += 10
        if rtype == 15:
            pref = struct.unpack(">H", paquet[pos:pos + 2])[0]
            serveur, _ = _lire_nom(paquet, pos + 2)
            mx.append((pref, serveur))
        pos += longueur
    return rcode, sorted(mx)


def _serveurs_dns() -> list[str]:
    try:
        with open("/etc/resolv.conf", encoding="utf-8") as f:
            return [l.split()[1] for l in f if l.startswith("nameserver") and len(l.split()) > 1]
    except OSError:
        return []


_FIABLE: bool | None = None


def resolveur_fiable() -> bool:
    """Contrôle témoin : un résolveur qui ne trouve pas le MX de gmail.com est filtré (cas des
    environnements cloud à réseau limité, qui répondent « domaine inexistant » à tout). Dans ce
    cas aucune réponse DNS n'est crue : on renvoie « non vérifiable » plutôt qu'un faux verdict."""
    global _FIABLE
    if _FIABLE is None:
        _FIABLE = _interroger_mx("gmail.com") is True
    return _FIABLE


def verifier_mx(dom: str, delai: float = 2.0) -> bool | None:
    """True : le domaine a un MX. False : NXDOMAIN ou aucun MX. None : impossible de vérifier."""
    if not resolveur_fiable():
        return None
    return _interroger_mx(dom, delai)


def _interroger_mx(dom: str, delai: float = 2.0) -> bool | None:
    for serveur in _serveurs_dns()[:2]:
        try:
            with socket.socket(socket.AF_INET6 if ":" in serveur else socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(delai)
                requete = construire_requete(dom)
                s.sendto(requete, (serveur, 53))
                paquet, _ = s.recvfrom(4096)
            if paquet[:2] != requete[:2]:
                continue
            rcode, mx = analyser_reponse(paquet)
            if rcode == 3:
                return False
            if rcode == 0:
                return bool(mx)
        except (OSError, struct.error, IndexError):
            continue
    return None

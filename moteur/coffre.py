"""Le coffre : les données prospects voyagent CHIFFRÉES dans le dépôt (AES-256, clé dérivée
PBKDF2, 200 000 itérations, via openssl). Sans la clé, le fichier est illisible ; la clé n'est
jamais dans le dépôt (variable d'environnement BROOZE_CLE, conservée dans le Drive privé de Zak).

  python3 -m moteur coffre fermer   # donnees/ → coffre/donnees.tar.gz.enc (à committer)
  python3 -m moteur coffre ouvrir   # coffre/donnees.tar.gz.enc → donnees/"""
import gzip
import hashlib
import io
import os
import subprocess
import tarfile
from pathlib import Path

from .config import RACINE, dossier_donnees

FICHIER = RACINE / "coffre" / "donnees.tar.gz.enc"
EMPREINTE = RACINE / "coffre" / "empreinte.txt"


def _cle() -> str:
    cle = os.environ.get("BROOZE_CLE", "").strip()
    if len(cle) < 24:
        raise SystemExit("BROOZE_CLE absente : récupère la clé dans le Drive de Zak (fichier « BROOZE prospection, "
                         "clé du coffre ») puis `export BROOZE_CLE=…`.")
    return cle


def _openssl(args: list[str], entree: bytes) -> bytes:
    env = dict(os.environ, BROOZE_CLE=_cle())
    r = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-md", "sha256",
                        "-pass", "env:BROOZE_CLE", *args], input=entree, capture_output=True, env=env)
    if r.returncode != 0:
        raise SystemExit("openssl a échoué (mauvaise clé ?) : " + r.stderr.decode(errors="replace")[:300])
    return r.stdout


def fermer(dossier: Path | None = None) -> dict:
    dossier = Path(dossier or dossier_donnees())
    tampon = io.BytesIO()
    with tarfile.open(fileobj=tampon, mode="w") as tar:
        for f in sorted(dossier.rglob("*")):
            if f.is_file() and f.name != "PAUSE":
                info = tar.gettarinfo(str(f), arcname=str(f.relative_to(dossier)))
                info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
                with open(f, "rb") as h:
                    tar.addfile(info, h)
    brut = gzip.compress(tampon.getvalue(), mtime=0)
    empreinte = hashlib.sha256(brut).hexdigest()
    if EMPREINTE.exists() and EMPREINTE.read_text().strip() == empreinte and FICHIER.exists():
        return {"modifie": False, "empreinte": empreinte}
    FICHIER.parent.mkdir(exist_ok=True)
    FICHIER.write_bytes(_openssl(["-salt"], brut))
    EMPREINTE.write_text(empreinte + "\n")
    return {"modifie": True, "empreinte": empreinte, "octets": FICHIER.stat().st_size}


def ouvrir(dossier: Path | None = None) -> dict:
    dossier = Path(dossier or dossier_donnees())
    if not FICHIER.exists():
        return {"ouvert": False, "raison": "aucun coffre (premier lancement)"}
    brut = _openssl(["-d"], FICHIER.read_bytes())
    if EMPREINTE.exists() and hashlib.sha256(brut).hexdigest() != EMPREINTE.read_text().strip():
        raise SystemExit("Empreinte du coffre incohérente : fichier corrompu ou modifié.")
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(brut)), mode="r") as tar:
        for m in tar.getmembers():
            if m.name.startswith("/") or ".." in Path(m.name).parts:
                raise SystemExit(f"chemin interdit dans le coffre : {m.name}")
        tar.extractall(dossier, filter="data")
    return {"ouvert": True, "fichiers": len(list(dossier.rglob("*")))}

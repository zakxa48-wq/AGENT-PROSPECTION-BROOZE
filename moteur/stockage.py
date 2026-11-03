"""Tables JSON Lines : lecture, ajout verrouillé, réécriture atomique."""
import fcntl
import json
import os
import tempfile
from pathlib import Path


def lire_jsonl(chemin: Path) -> list[dict]:
    if not chemin.exists():
        return []
    sortie = []
    with open(chemin, encoding="utf-8") as f:
        for numero, ligne in enumerate(f, 1):
            ligne = ligne.strip()
            if not ligne:
                continue
            try:
                sortie.append(json.loads(ligne))
            except json.JSONDecodeError as e:
                raise ValueError(f"{chemin.name}, ligne {numero} illisible : {e}") from e
    return sortie


def ajouter_jsonl(chemin: Path, objets: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        for o in objets:
            f.write(json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)


def ecrire_jsonl(chemin: Path, objets: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=chemin.parent, prefix=f".{chemin.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for o in objets:
            f.write(json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, chemin)

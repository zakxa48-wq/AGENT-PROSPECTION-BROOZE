"""Chemins, fuseau et lecture des fichiers de configuration."""
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_CONFIG = RACINE / "config"
FUSEAU = ZoneInfo("Europe/Paris")


def dossier_donnees() -> Path:
    """Dossier des données privées (jamais versionné en clair)."""
    d = Path(os.environ.get("BROOZE_DONNEES", RACINE / "donnees"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def charger(nom: str) -> dict:
    with open(DOSSIER_CONFIG / f"{nom}.json", encoding="utf-8") as f:
        return json.load(f)


def pilotage(dossier: Path | None = None) -> dict:
    """Réglages écrits par le maître agent (ne peuvent que durcir les garde-fous)."""
    chemin = (dossier or dossier_donnees()) / "pilotage.json"
    if chemin.exists():
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    return {}


def ecrire_pilotage(donnees: dict, dossier: Path | None = None) -> None:
    chemin = (dossier or dossier_donnees()) / "pilotage.json"
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)

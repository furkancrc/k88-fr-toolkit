"""Sauvegarde/chargement de la couleur choisie par l'utilisateur, pour pouvoir
la réappliquer automatiquement (le clavier ne la garde pas en mémoire flash)."""

import json
import os

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "k88fr-toolkit")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def save_color(r: int, g: int, b: int) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"color": [r, g, b]}, f)


def load_color() -> tuple[int, int, int] | None:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        r, g, b = data["color"]
        return int(r), int(g), int(b)
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        return None

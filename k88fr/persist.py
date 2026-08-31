"""Applique une couleur *vraiment* persistante (sauvegardée en mémoire flash
du clavier), en rejouant la séquence USB exacte capturée depuis le vrai
logiciel officiel pour cette couleur précise.

Contrairement à k88fr.led.K88FR.set_color() (aperçu temporaire, perdu au
débranchement), ceci reproduit le mécanisme complet de sauvegarde découvert
par rétro-ingénierie (voir docs/protocol.md) : le checksum du Report 0x3f
étant un algorithme propriétaire non cassé, seules les couleurs listées
dans k88fr.presets peuvent être appliquées de façon persistante pour
l'instant.
"""

import time

import hid

from k88fr.led import KeyboardNotFoundError, _find_path
from k88fr.presets import PERSISTENT_PRESETS


def available_colors() -> list[str]:
    return sorted(PERSISTENT_PRESETS)


def apply_persistent(name: str, delay: float = 0.15) -> None:
    if name not in PERSISTENT_PRESETS:
        raise ValueError(f"Couleur persistante inconnue: {name!r} (disponibles: {available_colors()})")

    sequence = [bytes.fromhex(h) for h in PERSISTENT_PRESETS[name]["sequence"]]
    path = _find_path()

    for report in sequence:
        try:
            dev = hid.device()
            dev.open_path(path)
        except OSError as e:
            raise KeyboardNotFoundError(f"Impossible d'ouvrir le clavier: {e}") from e

        try:
            if report[0] in (0x14, 0x20, 0x3f, 0x45):
                dev.send_feature_report(report)
            else:
                dev.write(report)
        finally:
            dev.close()
        time.sleep(delay)

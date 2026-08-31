"""Sauvegarde une couleur en mémoire flash du clavier — n'importe laquelle.

Le clavier n'attend aucun « mot de passe » externe : il vérifie simplement que
le profil déposé est cohérent avec lui-même. Le rapport 0x45 porte à ses
offsets 21-22 un champ de contrôle interne (voir `k88fr.profile`) ; tant qu'il
est correct, le profil est accepté et survit au débranchement.

Séquence complète :

    Report 9    : 09 02 00…00        ouverture
    Report 0x45 : profil, fragment 1 (en-tête 00 01 12)
    Report 0x45 : profil, fragment 2 (en-tête 00 00 01)
    Report 9    : 09 07 00…00        fermeture

Chaque rapport doit partir sur un handle HID neuf, avec une courte pause : en
réutilisant un seul handle, les écritures échouent avec ERROR_GEN_FAILURE.

Le rapport 0x3f envoyé ensuite par le logiciel d'origine s'est révélé
facultatif — il n'entre pas dans la validation.
"""

import time

import hid

from k88fr.led import KeyboardNotFoundError, _find_path
from k88fr.presets import PERSISTENT_PRESETS
from k88fr.profile import with_color

# Gabarit de profil « couleur unie » : seuls la couleur et le champ interne
# sont réécrits, le reste de la structure est repris tel quel.
_TEMPLATE = [bytes.fromhex(h) for h in PERSISTENT_PRESETS["rouge"]["sequence"]]


def _send(path, report: bytes, delay: float) -> None:
    try:
        dev = hid.device()
        dev.open_path(path)
    except OSError as e:
        raise KeyboardNotFoundError(f"Impossible d'ouvrir le clavier: {e}") from e
    try:
        if report[0] in (0x14, 0x20, 0x3F, 0x45):
            dev.send_feature_report(report)
        else:
            dev.write(report)
    finally:
        dev.close()
    time.sleep(delay)


def save_color(r: int, g: int, b: int, delay: float = 0.15) -> None:
    """Écrit la couleur en mémoire du clavier : elle survit au débranchement."""
    for name, value in (("r", r), ("g", g), ("b", b)):
        if not 0 <= value <= 255:
            raise ValueError(f"{name}={value} hors de la plage 0-255")

    path = _find_path()
    for report in _TEMPLATE:
        if report[0] == 0x3F:
            continue  # facultatif : ne participe pas à la validation
        _send(path, with_color(report, (r, g, b)) if report[0] == 0x45 else report, delay)


def available_colors() -> list[str]:
    """Couleurs nommées (historique : toute couleur fonctionne désormais)."""
    return sorted(PERSISTENT_PRESETS)


def apply_persistent(name: str, delay: float = 0.15) -> None:
    """Applique une couleur nommée. Conservé pour compatibilité."""
    if name not in PERSISTENT_PRESETS:
        raise ValueError(f"Couleur inconnue: {name!r} (disponibles: {available_colors()})")
    save_color(*PERSISTENT_PRESETS[name]["rgb"], delay=delay)


def main() -> None:
    import argparse

    from k88fr.led import _parse_color

    parser = argparse.ArgumentParser(
        description="Sauvegarde une couleur dans la mémoire du clavier K88-FR."
    )
    parser.add_argument("color", type=_parse_color, help="nom connu ou hex RRGGBB")
    args = parser.parse_args()
    r, g, b = args.color
    save_color(r, g, b)
    print(f"Couleur sauvegardée dans le clavier : rgb({r}, {g}, {b})")
    print("Elle survit au débranchement.")


if __name__ == "__main__":
    main()

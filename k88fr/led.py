"""Contrôle de la couleur RGB globale (mode "contrôle complet") du K88-FR.

Protocole découvert par rétro-ingénierie (voir docs/protocol.md) :

1. Ouvrir un "mode d'édition" via un rapport Output Report ID 9
   (contenu: 0x21 suivi de zéros, complété à 64 octets).
2. Écrire le nouvel état via un rapport Feature Report ID 0x14
   (19 octets: cf. docs/protocol.md pour le détail des offsets).
3. Fermer le mode d'édition via un rapport Output Report ID 9
   (contenu: 0x22 suivi de zéros, complété à 64 octets).

Sans l'étape 1/3, l'écriture du Report 0x14 est acceptée par Windows/USB
(aucune erreur) mais silencieusement ignorée par le firmware du clavier.
"""

import argparse
import sys

import hid

VID = 0x3938
PID = 0x1150
TARGET_USAGE_PAGE = 0xFF19

REPORT9_LEN = 64
FEATURE_14_LEN = 19  # avec le Report ID

NAMED_COLORS = {
    "rouge": (255, 0, 0),
    "red": (255, 0, 0),
    "vert": (0, 255, 0),
    "green": (0, 255, 0),
    "bleu": (0, 0, 255),
    "blue": (0, 0, 255),
    "blanc": (255, 255, 255),
    "white": (255, 255, 255),
    "jaune": (255, 255, 0),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "orange": (255, 128, 0),
    "off": (0, 0, 0),
    "eteint": (0, 0, 0),
}


def _report9(first_byte: int) -> bytes:
    return bytes([0x09, first_byte]) + bytes(REPORT9_LEN - 2)


OPEN_EDIT = _report9(0x21)
CLOSE_EDIT = _report9(0x22)


class KeyboardNotFoundError(RuntimeError):
    pass


def _find_path() -> bytes:
    for info in hid.enumerate(VID, PID):
        if info["usage_page"] == TARGET_USAGE_PAGE:
            return info["path"]
    raise KeyboardNotFoundError(
        f"Clavier K88-FR introuvable (VID={VID:#06x} PID={PID:#06x}, "
        f"canal usage_page={TARGET_USAGE_PAGE:#06x}). Vérifie qu'il est bien branché."
    )


class K88FR:
    def __init__(self) -> None:
        self._dev = hid.device()
        self._dev.open_path(_find_path())

    def close(self) -> None:
        self._dev.close()

    def __enter__(self) -> "K88FR":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def get_status_report(self) -> bytes:
        """Lit le Report Feature 0x14 (état RGB global actuel)."""
        return bytes(self._dev.get_feature_report(0x14, FEATURE_14_LEN + 1))

    def set_color(self, r: int, g: int, b: int) -> None:
        """Applique une couleur unie sur l'ensemble du clavier (mode contrôle complet)."""
        for name, value in (("r", r), ("g", g), ("b", b)):
            if not 0 <= value <= 255:
                raise ValueError(f"{name}={value} hors de la plage 0-255")

        current = bytearray(self.get_status_report())
        current[6], current[7], current[8] = r, g, b

        self._dev.write(OPEN_EDIT)
        self._dev.send_feature_report(bytes(current))
        self._dev.write(CLOSE_EDIT)


def _parse_color(value: str) -> tuple[int, int, int]:
    if value.lower() in NAMED_COLORS:
        return NAMED_COLORS[value.lower()]
    if value.startswith("#"):
        value = value[1:]
    if len(value) == 6:
        try:
            return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(
        f"couleur invalide: {value!r} (attendu: nom connu, ou hex RRGGBB / #RRGGBB)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Change la couleur RGB globale du clavier AmazonBasics K88-FR."
    )
    parser.add_argument(
        "color",
        type=_parse_color,
        help=f"couleur: {', '.join(sorted(set(NAMED_COLORS)))}, ou hex RRGGBB",
    )
    args = parser.parse_args()
    r, g, b = args.color

    try:
        with K88FR() as kb:
            kb.set_color(r, g, b)
    except KeyboardNotFoundError as e:
        print(f"Erreur: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Couleur appliquée: rgb({r}, {g}, {b})")


if __name__ == "__main__":
    main()

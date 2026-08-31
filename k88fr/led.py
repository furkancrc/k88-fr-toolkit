"""Contrôle de la couleur RGB globale (mode "contrôle complet") du K88-FR.

Protocole découvert par rétro-ingénierie (voir docs/protocol.md) :

1. Ouvrir un "mode d'édition" via un rapport Output Report ID 9
   (contenu: 0x21 suivi de zéros, complété à 64 octets).
2. Écrire le nouvel état via un rapport Feature Report ID 0x14
   (19 octets: cf. FEATURE_14_LAYOUT ci-dessous).
3. Fermer le mode d'édition via un rapport Output Report ID 9
   (contenu: 0x22 suivi de zéros, complété à 64 octets).

Sans l'étape 1/3, l'écriture du Report 0x14 est acceptée par Windows/USB
(aucune erreur) mais silencieusement ignorée par le firmware du clavier.
"""

import hid

VID = 0x3938
PID = 0x1150
TARGET_USAGE_PAGE = 0xFF19

REPORT9_LEN = 64


def _report9(first_byte: int) -> bytes:
    return bytes([0x09, first_byte]) + bytes(REPORT9_LEN - 2)


OPEN_EDIT = _report9(0x21)
CLOSE_EDIT = _report9(0x22)


def _find_path() -> bytes:
    for info in hid.enumerate(VID, PID):
        if info["usage_page"] == TARGET_USAGE_PAGE:
            return info["path"]
    raise RuntimeError(f"Clavier K88-FR (VID={VID:#06x} PID={PID:#06x}) introuvable")


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
        return bytes(self._dev.get_feature_report(0x14, 20))

    def set_color(self, r: int, g: int, b: int) -> None:
        """Applique une couleur unie sur l'ensemble du clavier (mode contrôle complet)."""
        current = bytearray(self.get_status_report())
        current[6], current[7], current[8] = r, g, b

        self._dev.write(OPEN_EDIT)
        self._dev.send_feature_report(bytes(current))
        self._dev.write(CLOSE_EDIT)


def main() -> None:
    import sys

    if len(sys.argv) != 4:
        print("Usage: python -m k88fr.led <R> <G> <B>   (valeurs 0-255)")
        sys.exit(1)
    r, g, b = (int(x) for x in sys.argv[1:4])
    with K88FR() as kb:
        kb.set_color(r, g, b)
    print(f"Couleur appliquée: rgb({r}, {g}, {b})")


if __name__ == "__main__":
    main()

"""Rejoue une séquence de rapports HID Output capturée (Wireshark) sur le canal
vendor-spécifique du K88-FR (Col06, usage_page=0xFF19), pour vérifier si le
clavier répond réellement aux commandes qu'on a interceptées.
"""

import sys
import time

import hid

VID = 0x3938
PID = 0x1150
TARGET_USAGE_PAGE = 0xFF19

# Séquence capturée dans led_click.pcapng (groupe 1: frames 7, 11, 15)
# Chaque entrée = contenu du "Data Fragment" HID (report id inclus en 1er octet).
SEQUENCE = [
    bytes.fromhex(
        "09210000000000000000000000000000000000000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000"
    ),
    bytes.fromhex(
        "0905000013010002010103ff00000301000100000002418100000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000"
    ),
    bytes.fromhex(
        "09220000000000000000000000000000000000000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000"
    ),
]


def find_target_path() -> bytes:
    for info in hid.enumerate(VID, PID):
        if info["usage_page"] == TARGET_USAGE_PAGE:
            return info["path"]
    raise RuntimeError(
        f"Aucun device VID={VID:#06x} PID={PID:#06x} avec usage_page={TARGET_USAGE_PAGE:#06x} trouvé. "
        "Le clavier est-il branché ?"
    )


def main() -> None:
    path = find_target_path()
    print(f"Ouverture de {path!r}")

    dev = hid.device()
    dev.open_path(path)
    try:
        for i, report in enumerate(SEQUENCE, 1):
            n = len(report)
            print(f"[{i}/{len(SEQUENCE)}] write {n} octets: {report[:12].hex()}...")
            written = dev.write(report)
            print(f"    -> {written} octets écrits")
            time.sleep(0.3)
    finally:
        dev.close()

    print("Terminé. Regarde si les LEDs du clavier ont changé.")


if __name__ == "__main__":
    sys.exit(main())

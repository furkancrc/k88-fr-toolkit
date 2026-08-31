"""Teste si on peut appliquer une couleur ARBITRAIRE de facon persistante en
patchant simplement les octets RGB de la sequence 0x45 capturee, sans savoir
calculer le checksum du Report 0x3f.

Trois strategies testables :
  --keep-checksum  : on renvoie le checksum de la couleur d'origine (rouge)
  --no-checksum    : on omet completement l'ecriture du Report 0x3f
  --zero-checksum  : on envoie 3f 00 00

Usage: python -m k88fr.tools.try_patch_color <R> <G> <B> [strategie]
"""

import sys
import time

import hid

from k88fr.led import _find_path
from k88fr.presets import PERSISTENT_PRESETS

RGB_OFFSETS = (10, 11, 12)  # positions des octets R,G,B dans le Report 0x45


def build_sequence(r: int, g: int, b: int, strategy: str) -> list[bytes]:
    template = [bytes.fromhex(h) for h in PERSISTENT_PRESETS["rouge"]["sequence"]]
    out = []
    for report in template:
        if report[0] == 0x45:
            patched = bytearray(report)
            patched[RGB_OFFSETS[0]] = r
            patched[RGB_OFFSETS[1]] = g
            patched[RGB_OFFSETS[2]] = b
            out.append(bytes(patched))
        elif report[0] == 0x3F:
            if strategy == "no-checksum":
                continue
            if strategy == "zero-checksum":
                out.append(bytes([0x3F, 0x00, 0x00]))
            elif strategy == "computed":
                from k88fr.checksum import checksum_report

                out.append(checksum_report(r, g, b))
            else:  # keep-checksum
                out.append(report)
        else:
            out.append(report)
    return out


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    r, g, b = (int(x) for x in sys.argv[1:4])
    strategy = sys.argv[4] if len(sys.argv) > 4 else "keep-checksum"
    strategy = strategy.lstrip("-")

    sequence = build_sequence(r, g, b, strategy)
    print(f"Couleur cible: rgb({r}, {g}, {b})  strategie: {strategy}")

    # 1) changement VISIBLE (Report 0x14, encadre par 0x21/0x22) - connu pour marcher
    from k88fr.led import K88FR

    with K88FR() as kb:
        kb.set_color(r, g, b)
    print("Couleur live appliquee (Report 0x14). Le clavier doit deja avoir change.")
    time.sleep(0.3)

    # 2) tentative de SAUVEGARDE FLASH (Report 0x45 patche + checksum)
    path = _find_path()
    for i, report in enumerate(sequence, 1):
        dev = hid.device()
        dev.open_path(path)
        print(f"[{i}/{len(sequence)}] {len(report):3d} octets: {report[:14].hex()}...")
        if report[0] in (0x14, 0x20, 0x3F, 0x45):
            ret = dev.send_feature_report(report)
        else:
            ret = dev.write(report)
        print(f"    -> {ret}  error={dev.error()}")
        dev.close()
        time.sleep(0.15)
    print("Termine. Verifie la couleur, puis debranche/rebranche pour tester la persistance.")


if __name__ == "__main__":
    main()

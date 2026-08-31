"""Mesure la contribution d'un octet au checksum, directement sur le materiel.

Principe : on part de la sequence rouge (checksum connu 0xc4f6), on modifie
UN octet couvert, et on essaie une petite liste de deltas plausibles pour le
checksum. Celui qui est accepte revele le poids de cet octet.

Un poids de +1 signifie une somme d'octets ; +256 signifie que l'octet est
l'octet de poids fort d'un mot de 16 bits.
"""

import sys
import time

import hid

from k88fr.led import _find_path
from k88fr.presets import PERSISTENT_PRESETS
from k88fr.tools.test_checksum_candidates import _read_color

BASE_CHECKSUM = 0xC4F6
BASE_RGB = (0xFF, 0x00, 0x00)
GREEN = (0, 255, 0)

CANDIDATE_DELTAS = [1, 0x100, 2, 0x200, 0xFF, 0xFF00, -1, -0x100, 3, 0x300, 4, 0x400]


def build(offset: int, byte_delta: int, checksum: int) -> list[bytes]:
    out = []
    for report in (bytes.fromhex(h) for h in PERSISTENT_PRESETS["rouge"]["sequence"]):
        if report[0] == 0x45:
            p = bytearray(report)
            p[offset] = (p[offset] + byte_delta) & 0xFF
            out.append(bytes(p))
        elif report[0] == 0x3F:
            out.append(bytes([0x3F, (checksum >> 8) & 0xFF, checksum & 0xFF]))
        else:
            out.append(report)
    return out


def attempt(path, offset, byte_delta, checksum) -> bool:
    # un handle neuf par rapport, avec pause : c'est le seul rythme que le
    # firmware accepte de facon fiable
    for rep in build(offset, byte_delta, checksum):
        dev = hid.device()
        dev.open_path(path)
        try:
            if rep[0] in (0x3F, 0x45):
                dev.send_feature_report(rep)
            else:
                dev.write(rep)
        finally:
            dev.close()
        time.sleep(0.12)
    time.sleep(0.2)
    return _read_color(path) == BASE_RGB


def main() -> None:
    offset = int(sys.argv[1]) if len(sys.argv) > 1 else 13
    byte_delta = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    path = _find_path()
    print(f"Controle : sequence rouge intacte -> ", end="", flush=True)
    ok = attempt(path, offset, 0, BASE_CHECKSUM)
    print("OK" if ok else "ECHEC (oracle non fiable)")
    if not ok:
        return

    print(f"\nOctet {offset} modifie de +{byte_delta}. Essai des deltas de checksum :")
    for d in CANDIDATE_DELTAS:
        cks = (BASE_CHECKSUM + d) & 0xFFFF
        hit = attempt(path, offset, byte_delta, cks)
        print(f"  delta {d:+6d} -> checksum {cks:#06x}  {'*** ACCEPTE ***' if hit else 'rejete'}")
        if hit:
            print(f"\nPoids de l'octet {offset} = {d}")
            return
    print("\nAucun delta simple ne convient pour cet octet.")


if __name__ == "__main__":
    main()

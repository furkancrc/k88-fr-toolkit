"""Cartographie les octets du Report 0x45 reellement couverts par le checksum.

Pour chaque offset, on rejoue la sequence rouge (checksum connu 0xc4f6) en
modifiant ce seul octet :
  - rejete  -> l'octet est COUVERT par le checksum
  - accepte -> l'octet est ignore

Cela delimite precisement la zone protegee, ce qui restreint enormement les
algorithmes possibles.
"""

import time

import hid

from k88fr.led import _find_path
from k88fr.presets import PERSISTENT_PRESETS
from k88fr.tools.test_checksum_candidates import _read_color, _send

MAX_OFFSET = 40
GREEN = (0, 255, 0)


def build(offset: int | None) -> list[bytes]:
    out = []
    for report in (bytes.fromhex(h) for h in PERSISTENT_PRESETS["rouge"]["sequence"]):
        if report[0] == 0x45 and offset is not None:
            patched = bytearray(report)
            patched[offset] ^= 0x01
            out.append(bytes(patched))
        else:
            out.append(report)
    return out


def run(path, offset):
    for report in build(offset):
        _send(path, report)
    time.sleep(0.2)
    return _read_color(path)


def main() -> None:
    path = _find_path()

    got = run(path, None)
    print(f"Controle rouge: 0x14 = {got}  {'OK' if got == (255, 0, 0) else 'PROBLEME'}")
    if got != (255, 0, 0):
        return

    covered, ignored = [], []
    print(f"\nBalayage des offsets 1..{MAX_OFFSET - 1} (bit 0 inverse):")
    for offset in range(1, MAX_OFFSET):
        got = run(path, offset)
        rejected = got == GREEN
        (covered if rejected else ignored).append(offset)
        tag = "COUVERT" if rejected else "ignore"
        print(f"  offset {offset:3d}: 0x14={str(got):16s} {tag}")

    print(f"\nOctets couverts : {covered}")
    print(f"Octets ignores  : {ignored}")


if __name__ == "__main__":
    main()

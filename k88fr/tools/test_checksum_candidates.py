"""Teste sur le materiel les checksums candidats issus de l'analyse lineaire.

Oracle : apres une ecriture flash, le registre 0x14 reflete la couleur du
profil stocke. Si le checksum est bon, il contient la couleur demandee ; s'il
est mauvais, le firmware invalide le profil et 0x14 repasse au vert d'usine.
Cela permet de tester sans debrancher le clavier.

IMPORTANT : le logiciel officiel doit etre completement ferme.
"""

import time

import hid

from k88fr.led import _find_path
from k88fr.presets import PERSISTENT_PRESETS

RGB_OFFSETS_45 = (10, 11, 12)
RGB_OFFSETS_14 = (6, 7, 8)

CANDIDATES = [
    0x9552, 0xFD4B, 0x9681, 0x8FD8, 0x5696, 0xB522, 0x96E7, 0x1568,
    0xF8A4, 0x64A8, 0x7A54, 0x776C, 0x7474, 0x6C66, 0x6B4E, 0xE1A4,
]

TARGET = (0xFF, 0x00, 0xFF)  # magenta


def _send(path, report, delay=0.06):
    dev = hid.device()
    dev.open_path(path)
    try:
        if report[0] in (0x14, 0x20, 0x3F, 0x45):
            dev.send_feature_report(report)
        else:
            dev.write(report)
    finally:
        dev.close()
    time.sleep(delay)


def _read_color(path) -> tuple[int, int, int]:
    dev = hid.device()
    dev.open_path(path)
    try:
        buf = bytes(dev.get_feature_report(0x14, 20))
    finally:
        dev.close()
    return tuple(buf[i] for i in RGB_OFFSETS_14)


def build(rgb, checksum) -> list[bytes]:
    out = []
    for report in (bytes.fromhex(h) for h in PERSISTENT_PRESETS["rouge"]["sequence"]):
        if report[0] == 0x45:
            patched = bytearray(report)
            for off, v in zip(RGB_OFFSETS_45, rgb):
                patched[off] = v
            out.append(bytes(patched))
        elif report[0] == 0x3F:
            out.append(bytes([0x3F, (checksum >> 8) & 0xFF, checksum & 0xFF]))
        else:
            out.append(report)
    return out


def try_checksum(path, rgb, checksum) -> tuple[int, int, int]:
    for report in build(rgb, checksum):
        _send(path, report)
    time.sleep(0.2)
    return _read_color(path)


def main() -> None:
    path = _find_path()

    print("Controle de l'oracle avec le rouge (checksum connu 0xc4f6)...")
    got = try_checksum(path, (0xFF, 0x00, 0x00), 0xC4F6)
    print(f"  0x14 lu = {got}  {'OK' if got == (0xFF, 0, 0) else 'ORACLE NON FIABLE'}")
    if got != (0xFF, 0, 0):
        print("Arret : l'oracle ne se comporte pas comme attendu.")
        return

    print(f"\nTest des {len(CANDIDATES)} candidats pour le magenta {TARGET}:")
    for checksum in CANDIDATES:
        got = try_checksum(path, TARGET, checksum)
        hit = got == TARGET
        print(f"  {checksum:#06x} -> 0x14 = {got}  {'*** TROUVE ***' if hit else ''}")
        if hit:
            print(f"\nCHECKSUM VALIDE : {checksum:#06x}")
            return

    print("\nAucun candidat ne convient : le checksum n'est pas un CRC16 de cette famille.")


if __name__ == "__main__":
    main()

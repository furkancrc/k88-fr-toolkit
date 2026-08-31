"""Cherche un Report lisible dont le contenu reflete le profil LED stocke.

Objectif : disposer d'un "oracle" permettant de savoir si une ecriture flash a
ete acceptee, SANS avoir a debrancher/rebrancher le clavier a chaque essai.

Methode : on lit tous les Reports lisibles, on applique un profil connu
(preset rouge, dont on sait qu'il persiste), on relit, et on affiche les
octets qui ont change.
"""

import time

import hid

from k88fr.led import _find_path
from k88fr.persist import apply_persistent

READABLE = [
    (0x10, 8),
    (0x11, 257),
    (0x12, 133),
    (0x13, 400),
    (0x14, 19),
    (0x15, 402),
    (0x42, 2053),
    (0x43, 2053),
    (0x44, 261),
    (0x45, 261),
]


def snapshot() -> dict[int, bytes]:
    path = _find_path()
    out = {}
    for report_id, size in READABLE:
        try:
            dev = hid.device()
            dev.open_path(path)
            out[report_id] = bytes(dev.get_feature_report(report_id, size + 1))
            dev.close()
        except Exception:
            pass
        time.sleep(0.05)
    return out


def main() -> None:
    print("Lecture de l'etat initial...")
    before = snapshot()

    print("Application du preset 'rouge' (persistant connu)...")
    apply_persistent("rouge")
    time.sleep(0.5)

    print("Relecture...\n")
    after = snapshot()

    for report_id in sorted(before):
        if report_id not in after:
            continue
        b, a = before[report_id], after[report_id]
        if b == a:
            print(f"Report {report_id:#04x}: inchange")
            continue
        diffs = [(i, b[i], a[i]) for i in range(min(len(a), len(b))) if a[i] != b[i]]
        print(f"Report {report_id:#04x}: {len(diffs)} octets modifies")
        for i, ob, nb in diffs[:24]:
            print(f"    offset {i:4d}: {ob:02x} -> {nb:02x}")
        if len(diffs) > 24:
            print(f"    ... et {len(diffs) - 24} autres")


if __name__ == "__main__":
    main()

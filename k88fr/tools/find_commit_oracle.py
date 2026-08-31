"""Cherche comment detecter, SANS debrancher, qu'un checksum a ete accepte.

Depuis qu'on depose le profil une seule fois puis qu'on enchaine les essais
legers, le registre 0x14 ne sert plus d'indicateur : il affiche la couleur des
le depot, avant toute validation. Il faut donc trouver un autre octet, qui ne
change QU'au moment ou la sauvegarde est reellement validee.

Methode : on photographie tous les rapports lisibles apres un checksum faux,
puis apres le bon, et on compare.
"""

import time

import hid

from k88fr.led import _find_path
from k88fr.persist import apply_persistent
from k88fr.tools.test_staging import checksum_report, parts, send

READABLE = [
    (0x10, 8), (0x11, 257), (0x12, 133), (0x13, 400), (0x14, 19),
    (0x15, 402), (0x42, 2053), (0x43, 2053), (0x44, 261), (0x45, 261),
]

CORRECT = 0xC4F6


def snapshot(path) -> dict[int, bytes]:
    out = {}
    for rid, size in READABLE:
        try:
            dev = hid.device()
            dev.open_path(path)
            out[rid] = bytes(dev.get_feature_report(rid, size + 1))
            dev.close()
        except Exception:
            pass
        time.sleep(0.02)
    return out


def diff(a: dict, b: dict, label: str) -> None:
    print(f"\n--- {label} ---")
    total = 0
    for rid in sorted(a):
        if rid not in b or a[rid] == b[rid]:
            continue
        positions = [i for i in range(min(len(a[rid]), len(b[rid]))) if a[rid][i] != b[rid][i]]
        total += len(positions)
        apercu = ", ".join(f"{i}:{a[rid][i]:02x}->{b[rid][i]:02x}" for i in positions[:6])
        print(f"  rapport {rid:#04x}: {len(positions)} octet(s) — {apercu}")
    if total == 0:
        print("  aucun changement")


def main() -> None:
    path = _find_path()

    print("1) profil VERT valide en flash (reference)")
    apply_persistent("vert")
    time.sleep(0.5)

    print("2) depot du profil ROUGE (sans checksum)")
    for r in parts():
        send(path, r)
    time.sleep(0.3)
    apres_depot = snapshot(path)

    print("3) checksum FAUX")
    send(path, checksum_report(0x0001))
    time.sleep(0.3)
    apres_faux = snapshot(path)

    print("4) checksum CORRECT")
    send(path, checksum_report(CORRECT))
    time.sleep(0.4)
    apres_bon = snapshot(path)

    diff(apres_depot, apres_faux, "depot -> checksum faux (bruit de fond a ignorer)")
    diff(apres_faux, apres_bon, "checksum faux -> checksum correct (INDICATEUR RECHERCHE)")


if __name__ == "__main__":
    main()

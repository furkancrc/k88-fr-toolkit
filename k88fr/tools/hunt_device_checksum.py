"""Cherche si le clavier expose lui-meme le checksum du profil courant.

Le firmware doit calculer ce checksum pour le verifier. S'il le garde dans un
rapport lisible, on peut le lui demander au lieu de deviner l'algorithme --
et l'outil devient totalement autonome, sans logiciel officiel.

Methode : on applique une couleur dont on connait le checksum (rouge =
0xc4f6, vert = 0x4627, bleu = 0xbeca), puis on relit tous les rapports en
cherchant cette valeur. Si elle apparait au meme offset pour les trois
couleurs, on tient la source.
"""

import time

import hid

from k88fr.led import _find_path
from k88fr.persist import apply_persistent

READABLE = [
    (0x10, 8), (0x11, 257), (0x12, 133), (0x13, 400), (0x14, 19),
    (0x15, 402), (0x42, 2053), (0x43, 2053), (0x44, 261), (0x45, 261),
]

KNOWN = {"rouge": 0xC4F6, "vert": 0x4627, "bleu": 0xBECA}


def snapshot(path) -> dict[int, bytes]:
    out = {}
    for report_id, size in READABLE:
        try:
            dev = hid.device()
            dev.open_path(path)
            out[report_id] = bytes(dev.get_feature_report(report_id, size + 1))
            dev.close()
        except Exception:
            pass
        time.sleep(0.03)
    return out


def locate(buf: bytes, value: int) -> list[tuple[int, str]]:
    be = bytes([value >> 8, value & 0xFF])
    le = bytes([value & 0xFF, value >> 8])
    hits = []
    for i in range(len(buf) - 1):
        if buf[i : i + 2] == be:
            hits.append((i, "BE"))
        elif buf[i : i + 2] == le:
            hits.append((i, "LE"))
    return hits


def main() -> None:
    path = _find_path()
    positions = {}

    for name, checksum in KNOWN.items():
        print(f"\n=== application de {name} (checksum connu {checksum:#06x}) ===")
        apply_persistent(name)
        time.sleep(0.4)
        snap = snapshot(path)

        found = {}
        for report_id, buf in snap.items():
            hits = locate(buf, checksum)
            if hits:
                found[report_id] = hits
                print(f"  Report {report_id:#04x}: {checksum:#06x} present aux offsets {hits[:6]}")
        if not found:
            print("  valeur absente de tous les rapports lisibles")
        positions[name] = found

    common = set.intersection(
        *[{(rid, off, order) for rid, hits in f.items() for off, order in hits}
          for f in positions.values()]
    ) if all(positions.values()) else set()

    print("\n=== emplacements communs aux trois couleurs ===")
    if common:
        for rid, off, order in sorted(common):
            print(f"  Report {rid:#04x} offset {off} ({order})  <-- source du checksum")
    else:
        print("  aucun : le clavier n'expose pas le checksum tel quel")


if __name__ == "__main__":
    main()

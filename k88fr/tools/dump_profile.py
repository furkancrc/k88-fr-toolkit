"""Photographie l'etat du profil courant du clavier.

Sert a comparer les 5 profils d'usine entre eux : ce sont des profils que le
clavier considere forcement comme valides. Si l'un d'eux contient une couleur
melangee, on decouvre comment un profil valide l'encode -- ce qui manque
aujourd'hui, puisqu'un profil bricole avec deux canaux allumes est refuse quel
que soit son checksum.

Usage : lancer une fois par profil, en appuyant sur le bouton du clavier entre
chaque appel.
    python -m k88fr.tools.dump_profile 1
"""

import json
import os
import sys
import time

import hid

from k88fr.led import _find_path

REPORTS = [(0x10, 8), (0x11, 257), (0x12, 133), (0x13, 400),
           (0x14, 19), (0x15, 402), (0x42, 2053)]

OUT_DIR = os.path.join(os.path.dirname(__file__), "_profils")


def snapshot(path) -> dict[int, bytes]:
    out = {}
    for rid, size in REPORTS:
        try:
            dev = hid.device()
            dev.open_path(path)
            out[rid] = bytes(dev.get_feature_report(rid, size + 1))
            dev.close()
        except Exception:
            pass
        time.sleep(0.03)
    return out


def main() -> None:
    numero = sys.argv[1] if len(sys.argv) > 1 else "?"
    os.makedirs(OUT_DIR, exist_ok=True)
    path = _find_path()

    snap = snapshot(path)
    couleur = tuple(snap[0x14][i] for i in (6, 7, 8)) if 0x14 in snap else None

    print(f"=== profil {numero} ===")
    print(f"  couleur (rapport 0x14, offsets 6-8) : {couleur}")
    if 0x14 in snap:
        print(f"  rapport 0x14 complet : {snap[0x14].hex()}")
    for rid in (0x10, 0x12):
        if rid in snap:
            print(f"  rapport {rid:#04x} : {snap[rid][:24].hex()}…")

    with open(os.path.join(OUT_DIR, f"profil{numero}.json"), "w") as f:
        json.dump({hex(k): v.hex() for k, v in snap.items()}, f)
    print(f"  enregistre dans _profils/profil{numero}.json")


if __name__ == "__main__":
    main()

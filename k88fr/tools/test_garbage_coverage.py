"""Determine si le checksum 0x3f couvre la 'traine' du Report 0x45.

Les trames 0x45 capturees contiennent, apres les ~23 octets utiles, une longue
zone qui ressemble a de la memoire de pile non initialisee du logiciel (elle
differe d'une capture a l'autre). Question : le checksum la couvre-t-il ?

Methode : on rejoue la sequence rouge EXACTE (checksum 0xc4f6 connu bon) mais
en modifiant un seul octet loin dans la traine.
  - accepte  -> la traine n'est PAS couverte, seul le prefixe utile compte
  - rejete   -> la traine EST couverte, et les differences entre captures
                rendaient toute analyse par differences invalide
"""

import time

import hid

from k88fr.led import _find_path
from k88fr.presets import PERSISTENT_PRESETS
from k88fr.tools.test_checksum_candidates import _read_color, _send

TAIL_OFFSET = 200  # bien au-dela de la zone utile (~23 octets)


def build(flip_tail: bool) -> list[bytes]:
    out = []
    for report in (bytes.fromhex(h) for h in PERSISTENT_PRESETS["rouge"]["sequence"]):
        if report[0] == 0x45 and flip_tail:
            patched = bytearray(report)
            patched[TAIL_OFFSET] ^= 0xFF
            out.append(bytes(patched))
        else:
            out.append(report)
    return out


def run(path, flip_tail: bool):
    for report in build(flip_tail):
        _send(path, report)
    time.sleep(0.2)
    return _read_color(path)


def main() -> None:
    path = _find_path()

    print("1) Sequence rouge intacte (controle)...")
    got = run(path, flip_tail=False)
    print(f"   0x14 = {got}  {'OK' if got == (255, 0, 0) else 'PROBLEME'}")
    if got != (255, 0, 0):
        print("   Oracle non fiable, arret.")
        return

    print(f"\n2) Meme sequence, mais octet {TAIL_OFFSET} de la traine inverse...")
    got = run(path, flip_tail=True)
    if got == (255, 0, 0):
        print(f"   0x14 = {got}  -> ACCEPTE")
        print("\n=> La traine n'est PAS couverte par le checksum.")
        print("   Seul le prefixe utile compte : l'analyse par differences etait valide.")
    else:
        print(f"   0x14 = {got}  -> REJETE")
        print("\n=> La traine EST couverte par le checksum.")
        print("   Les captures ayant des traines differentes, toutes les differences")
        print("   calculees jusqu'ici etaient polluees : il faut repartir de deltas")
        print("   propres (meme buffer, seuls les octets RGB changent).")


if __name__ == "__main__":
    main()

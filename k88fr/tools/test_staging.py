"""Le profil reste-t-il "en attente" apres un checksum refuse ?

Enjeu : jusqu'ici, chaque essai renvoyait toute la sequence (dont les deux
gros rapports 0x45 qui ecrivent le profil). Si le clavier conserve le profil
depose apres un checksum faux, on peut le deposer UNE fois puis n'envoyer que
les 2 octets a tester. Les essais deviennent legers, et probablement sans
ecriture flash tant qu'aucun n'est correct -- ce qui rendrait la force brute
viable sans user la memoire.

Test : on depose le rouge, on envoie un checksum faux, puis le BON checksum
sans rien redeposer.
  - le clavier passe au rouge  -> le depot survit : essais legers possibles
  - il reste au vert           -> le depot est detruit, tout est a refaire
"""

import time

import hid

from k88fr.led import _find_path
from k88fr.presets import PERSISTENT_PRESETS
from k88fr.tools.test_checksum_candidates import _read_color

CORRECT = 0xC4F6
RED = (255, 0, 0)


def parts():
    seq = [bytes.fromhex(h) for h in PERSISTENT_PRESETS["rouge"]["sequence"]]
    staging = [r for r in seq if r[0] != 0x3F]
    return staging


def send(path, report, delay=0.12):
    dev = hid.device()
    dev.open_path(path)
    try:
        if report[0] in (0x3F, 0x45):
            dev.send_feature_report(report)
        else:
            dev.write(report)
    finally:
        dev.close()
    time.sleep(delay)


def checksum_report(value: int) -> bytes:
    return bytes([0x3F, (value >> 8) & 0xFF, value & 0xFF])


def main() -> None:
    path = _find_path()
    staging = parts()

    print("1) depot du profil rouge (sans checksum)")
    for r in staging:
        send(path, r)

    print("2) envoi d'un checksum FAUX (0x0000)")
    send(path, checksum_report(0x0000))
    time.sleep(0.25)
    print(f"   0x14 = {_read_color(path)}  (vert attendu : refus)")

    print("3) envoi du BON checksum, SANS redeposer le profil")
    send(path, checksum_report(CORRECT))
    time.sleep(0.3)
    couleur = _read_color(path)
    print(f"   0x14 = {couleur}")

    print()
    if couleur == RED:
        print("=> LE DEPOT SURVIT : on peut deposer une fois puis enchainer les")
        print("   essais de checksum seuls. La force brute devient legere.")
    else:
        print("=> Le depot est detruit par un checksum faux : chaque essai impose")
        print("   de renvoyer tout le profil (et donc d'ecrire en flash).")


if __name__ == "__main__":
    main()

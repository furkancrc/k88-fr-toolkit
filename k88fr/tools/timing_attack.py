"""Attaque par mesure de temps sur la verification du checksum.

Si le firmware compare les deux octets du checksum successivement en
s'arretant au premier faux, une valeur dont l'octet de poids fort est correct
sera rejetee LEGEREMENT plus tard. Cette fuite ramenerait la recherche de
65536 essais a environ 512 (256 par octet), ce qui devient indolore pour la
memoire flash.

On teste sur le rouge, dont on connait le checksum correct (0xc4f6) :
  - groupe A : octet de poids fort correct (0xc4??), poids faible faux
  - groupe B : octet de poids fort faux
Si le temps median de A depasse nettement celui de B, la fuite existe.
"""

import statistics
import time

import hid

from k88fr.led import _find_path
from k88fr.presets import PERSISTENT_PRESETS

CORRECT = 0xC4F6
SAMPLES = 40


def build(checksum: int) -> list[bytes]:
    out = []
    for report in (bytes.fromhex(h) for h in PERSISTENT_PRESETS["rouge"]["sequence"]):
        if report[0] == 0x3F:
            out.append(bytes([0x3F, (checksum >> 8) & 0xFF, checksum & 0xFF]))
        else:
            out.append(report)
    return out


def timed_attempt(path, checksum: int) -> float:
    """Renvoie la duree (en ms) de l'envoi du rapport 0x3f uniquement."""
    seq = build(checksum)
    dev = hid.device()
    dev.open_path(path)
    try:
        for rep in seq[:-1]:
            if rep[0] in (0x45,):
                dev.send_feature_report(rep)
            else:
                dev.write(rep)
        t0 = time.perf_counter()
        dev.send_feature_report(seq[-1])
        t1 = time.perf_counter()
    finally:
        dev.close()
    return (t1 - t0) * 1000


def main() -> None:
    path = _find_path()

    print("Mesure en cours (peut prendre une minute)...\n")

    groupe_a, groupe_b = [], []
    for i in range(SAMPLES):
        # A : poids fort correct (0xc4), poids faible faux
        low = (i * 7 + 1) & 0xFF
        if low == (CORRECT & 0xFF):
            low ^= 1
        groupe_a.append(timed_attempt(path, (0xC4 << 8) | low))

        # B : poids fort faux
        high = (0xC4 + 1 + i) & 0xFF
        groupe_b.append(timed_attempt(path, (high << 8) | low))

    for nom, vals in (("A (poids fort CORRECT)", groupe_a), ("B (poids fort faux)   ", groupe_b)):
        print(f"{nom} : mediane {statistics.median(vals):7.3f} ms   "
              f"moyenne {statistics.mean(vals):7.3f} ms   "
              f"min {min(vals):7.3f}  max {max(vals):7.3f}")

    ecart = statistics.median(groupe_a) - statistics.median(groupe_b)
    bruit = statistics.pstdev(groupe_a + groupe_b)
    print(f"\nEcart des medianes : {ecart:+.3f} ms   (bruit type : {bruit:.3f} ms)")
    if abs(ecart) > 2 * bruit and bruit > 0:
        print("=> FUITE DETECTEE : le temps depend de la justesse de l'octet fort.")
        print("   La recherche tombe a ~512 essais au lieu de 65536.")
    else:
        print("=> Aucune fuite exploitable : la verification est a temps constant.")


if __name__ == "__main__":
    main()

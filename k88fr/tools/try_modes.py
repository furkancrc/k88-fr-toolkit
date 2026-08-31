"""Essaie différentes valeurs du byte 'mode' (offset 5) du Report 0x14 pour
voir si ça déclenche des animations prédéfinies (respiration, vague, etc.).
Un mode est appliqué toutes les 3 secondes, en boucle non interactive."""

import time

from k88fr.led import CLOSE_EDIT, OPEN_EDIT, K88FR


def main() -> None:
    with K88FR() as kb:
        base = bytearray(kb.get_status_report())
        print(f"État de départ: {base.hex()}")

        for mode in range(0, 16):
            report = bytearray(base)
            report[5] = mode

            print(f"mode={mode:2d}  ->  {bytes(report).hex()}")
            kb._dev.write(OPEN_EDIT)
            kb._dev.send_feature_report(bytes(report))
            kb._dev.write(CLOSE_EDIT)

            time.sleep(3)

        # remet l'état d'origine à la fin
        kb._dev.write(OPEN_EDIT)
        kb._dev.send_feature_report(bytes(base))
        kb._dev.write(CLOSE_EDIT)
        print("Restauré à l'état d'origine.")


if __name__ == "__main__":
    main()

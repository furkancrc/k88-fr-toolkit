"""Teste si l'enveloppe 0x02/0x07 (au lieu de 0x21/0x22) rend l'écriture du
Report 0x14 persistante (sauvegardée en mémoire flash du clavier)."""

from k88fr.led import K88FR, _report9

OPEN_B = _report9(0x02)
CLOSE_B = _report9(0x07)


def main() -> None:
    with K88FR() as kb:
        current = bytearray(kb.get_status_report())
        print(f"Avant: {current.hex()}")

        # Magenta, pour bien voir la différence avec les tests précédents
        current[6], current[7], current[8] = 255, 0, 255
        print(f"Envoi (enveloppe 02/07): {bytes(current).hex()}")

        kb._dev.write(OPEN_B)
        kb._dev.send_feature_report(bytes(current))
        kb._dev.write(CLOSE_B)

        after = bytes(kb.get_status_report())
        print(f"Après: {after.hex()}")


if __name__ == "__main__":
    main()

"""Analyse la structure d'un Report Feature: histogramme des valeurs,
recherche de motifs répétés (utile pour distinguer un bitmask binaire
d'une vraie table RGB)."""

import sys
from collections import Counter

import hid

VID = 0x3938
PID = 0x1150
TARGET_USAGE_PAGE = 0xFF19


def find_target_path() -> bytes:
    for info in hid.enumerate(VID, PID):
        if info["usage_page"] == TARGET_USAGE_PAGE:
            return info["path"]
    raise RuntimeError("Device Col06 introuvable")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m k88fr.analyze_report <report_id_hex> <taille_totale>")
        sys.exit(1)
    report_id = int(sys.argv[1], 16)
    total_len = int(sys.argv[2])

    path = find_target_path()
    dev = hid.device()
    dev.open_path(path)
    try:
        buf = bytes(dev.get_feature_report(report_id, total_len + 1))
    finally:
        dev.close()

    data = buf[1:]  # sans le report id
    c = Counter(data)
    n_distinct = len(c)
    print(f"Report {report_id:#04x}: {len(data)} octets de data, {n_distinct} valeurs distinctes")
    print("Top 10 valeurs les plus fréquentes:", c.most_common(10))
    print(f"Min={min(data)} Max={max(data)}")

    # affiche par blocs de 4 et de 3 pour repérer un pattern RGB(A)/RGB
    print("\nPar blocs de 3 (RGB?), 20 premiers:")
    for i in range(0, min(60, len(data)), 3):
        print(data[i:i+3].hex(), end="  ")
    print("\n\nPar blocs de 4 (RGBx?), 20 premiers:")
    for i in range(0, min(80, len(data)), 4):
        print(data[i:i+4].hex(), end="  ")
    print()


if __name__ == "__main__":
    main()

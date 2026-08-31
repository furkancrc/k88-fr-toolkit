"""Lit (GET_FEATURE) plusieurs Report IDs candidats sur le canal Col06 (0xFF19)
et affiche leur contenu, pour repérer celui qui contient l'état RGB actuel
(le clavier a actuellement des LED vertes -> on cherche un motif 00 FF 00 répété).
"""

import hid

VID = 0x3938
PID = 0x1150
TARGET_USAGE_PAGE = 0xFF19

# (report_id, taille totale attendue avec l'ID)
CANDIDATES = [
    (0x10, 8),
    (0x11, 257),
    (0x12, 133),
    (0x13, 400),
    (0x14, 19),
    (0x15, 402),
    (0x20, 400),
    (0x30, 5),
    (0x40, 5),
    (0x41, 5),
    (0x42, 2053),
    (0x43, 2053),
    (0x44, 261),
    (0x45, 261),
]


def find_target_path() -> bytes:
    for info in hid.enumerate(VID, PID):
        if info["usage_page"] == TARGET_USAGE_PAGE:
            return info["path"]
    raise RuntimeError("Device Col06 introuvable")


def main() -> None:
    path = find_target_path()
    dev = hid.device()
    dev.open_path(path)
    try:
        for report_id, total_len in CANDIDATES:
            data_len = total_len  # get_feature_report attend report_id + longueur max buffer
            try:
                buf = dev.get_feature_report(report_id, data_len + 1)
            except Exception as e:
                print(f"Report {report_id:#04x}: erreur {e}")
                continue
            b = bytes(buf)
            print(f"\n=== Report {report_id:#04x}  ({len(b)} octets lus) ===")
            print(b.hex())
    finally:
        dev.close()


if __name__ == "__main__":
    main()

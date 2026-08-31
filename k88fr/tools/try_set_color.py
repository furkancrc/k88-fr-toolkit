"""Essaie de modifier la couleur globale via SET_FEATURE sur le Report ID 0x14,
en changeant juste les octets RGB (vert actuel -> rouge) dans le rapport lu."""

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
    path = find_target_path()
    OPEN = bytes.fromhex(
        "09210000000000000000000000000000000000000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000"
    )
    CLOSE = bytes.fromhex(
        "09220000000000000000000000000000000000000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000"
    )

    dev = hid.device()
    dev.open_path(path)
    try:
        current = bytes(dev.get_feature_report(0x14, 20))
        print(f"Avant: {current.hex()}")

        # offsets 6,7,8 = R,G,B (actuellement 00 ff 00 = vert)
        new_report = bytearray(current)
        new_report[6] = 0xFF  # R
        new_report[7] = 0x00  # G
        new_report[8] = 0x00  # B
        print(f"Envoi: {bytes(new_report).hex()}")

        print("-> open (report 9, 0x21)")
        dev.write(OPEN)

        ret = dev.send_feature_report(bytes(new_report))
        print(f"send_feature_report -> {ret}")

        print("-> close (report 9, 0x22)")
        dev.write(CLOSE)

        after = bytes(dev.get_feature_report(0x14, 20))
        print(f"Après: {after.hex()} ({len(after)} octets)")
    finally:
        dev.close()


if __name__ == "__main__":
    main()

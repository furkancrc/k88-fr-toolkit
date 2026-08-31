"""Teste si le clavier calcule lui-meme le checksum du Report 0x3f apres
qu'on ecrit un nouveau Report 0x45, ou s'il faut le calculer nous-memes."""

import time

import hid

VID = 0x3938
PID = 0x1150
TARGET_USAGE_PAGE = 0xFF19


def find_target_path() -> bytes:
    for info in hid.enumerate(VID, PID):
        if info["usage_page"] == TARGET_USAGE_PAGE:
            return info["path"]
    raise RuntimeError("Device Col06 introuvable")


def open_dev():
    dev = hid.device()
    dev.open_path(find_target_path())
    return dev


def main() -> None:
    dev = open_dev()
    current45 = bytearray(dev.get_feature_report(0x45, 261))
    dev.close()
    print(f"0x45 actuel (offset 9-11 = RGB): {current45[9]:02x} {current45[10]:02x} {current45[11]:02x}")

    dev = open_dev()
    current3f_before = bytes(dev.get_feature_report(0x3f, 3))
    dev.close()
    print(f"0x3f avant modification: {current3f_before.hex()}")

    # Vert
    new45 = bytearray(current45)
    new45[9], new45[10], new45[11] = 0x00, 0xFF, 0x00

    OPEN = bytes([0x09, 0x02]) + bytes(62)
    CLOSE = bytes([0x09, 0x07]) + bytes(62)

    dev = open_dev()
    dev.write(OPEN)
    dev.close()
    time.sleep(0.15)

    dev = open_dev()
    dev.send_feature_report(bytes(new45))
    dev.close()
    time.sleep(0.15)

    dev = open_dev()
    dev.write(CLOSE)
    dev.close()
    time.sleep(0.15)

    # On NE touche PAS au 0x3f -> on regarde si le clavier l'a mis a jour tout seul
    dev = open_dev()
    current3f_after = bytes(dev.get_feature_report(0x3f, 3))
    dev.close()
    print(f"0x3f apres (sans qu'on l'ait ecrit): {current3f_after.hex()}")
    print("Identique a avant ?" , current3f_after == current3f_before)


if __name__ == "__main__":
    main()

"""Récupère et affiche le HID Report Descriptor brut de chaque collection du K88-FR."""

import hid

VID = 0x3938
PID = 0x1150


def main() -> None:
    for info in hid.enumerate(VID, PID):
        path = info["path"]
        dev = hid.device()
        try:
            dev.open_path(path)
        except OSError as e:
            print(f"{path!r}: impossible d'ouvrir ({e})")
            continue
        try:
            desc = dev.get_report_descriptor()
        except Exception as e:
            desc = None
            print(f"{path!r}: get_report_descriptor a échoué ({e})")
        finally:
            dev.close()
        if desc:
            print(f"\n=== {info['product_string']} usage_page={info['usage_page']:#06x} usage={info['usage']:#04x} ===")
            print(f"path={path!r}")
            print(f"len={len(desc)}")
            print(bytes(desc).hex())


if __name__ == "__main__":
    main()

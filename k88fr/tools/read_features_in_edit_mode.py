"""Relit les Report Feature qui échouaient (0x20, 0x30, 0x40, 0x41, 0x3f),
cette fois en étant en 'mode édition' (ouvert via Report 9 / 0x21) au cas où
le firmware refuse ces lectures hors de ce mode."""

from k88fr.led import CLOSE_EDIT, OPEN_EDIT, _find_path

import hid

CANDIDATES = [
    (0x20, 400),
    (0x30, 5),
    (0x3f, 3),
    (0x40, 5),
    (0x41, 5),
]


def main() -> None:
    dev = hid.device()
    dev.open_path(_find_path())
    try:
        dev.write(OPEN_EDIT)
        for report_id, total_len in CANDIDATES:
            try:
                buf = bytes(dev.get_feature_report(report_id, total_len + 1))
                print(f"Report {report_id:#04x}: {buf.hex()}")
            except Exception as e:
                print(f"Report {report_id:#04x}: erreur {e} / dev.error()={dev.error()}")
        dev.write(CLOSE_EDIT)
    finally:
        dev.close()


if __name__ == "__main__":
    main()

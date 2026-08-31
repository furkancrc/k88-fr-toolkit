"""Parseur minimal de HID Report Descriptor : liste les Report IDs et leur
type (Input/Output/Feature) + taille, pour repérer les canaux inexplorés.
"""

import sys

MAIN_INPUT = 0x80
MAIN_OUTPUT = 0x90
MAIN_FEATURE = 0xB0
MAIN_COLLECTION = 0xA0
MAIN_END_COLLECTION = 0xC0

TYPE_NAMES = {MAIN_INPUT: "Input", MAIN_OUTPUT: "Output", MAIN_FEATURE: "Feature"}


def parse(desc: bytes):
    i = 0
    report_size = 0
    report_count = 0
    report_id = 0
    results = []
    while i < len(desc):
        prefix = desc[i]
        size = prefix & 0x03
        size = {0: 0, 1: 1, 2: 2, 3: 4}[size]
        tag = prefix & 0xFC
        i += 1
        data = desc[i : i + size]
        i += size
        value = int.from_bytes(data, "little") if data else 0

        if tag == 0x74:  # Report Size
            report_size = value
        elif tag == 0x94:  # Report Count
            report_count = value
        elif tag == 0x84:  # Report ID
            report_id = value
        elif tag in (MAIN_INPUT, MAIN_OUTPUT, MAIN_FEATURE):
            total_bits = report_size * report_count
            total_bytes = (total_bits + 7) // 8
            results.append(
                {
                    "report_id": report_id,
                    "type": TYPE_NAMES[tag],
                    "data_bytes": total_bytes,
                    "total_bytes_incl_id": total_bytes + (1 if report_id else 0),
                }
            )
    return results


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m k88fr.parse_hid_descriptor <hex_descriptor>")
        sys.exit(1)
    desc = bytes.fromhex(sys.argv[1])
    for r in parse(desc):
        print(
            f"Report ID {r['report_id']:#04x} ({r['report_id']:3d})  "
            f"{r['type']:8s}  {r['data_bytes']:3d} octets de data "
            f"({r['total_bytes_incl_id']:3d} avec ID)"
        )


if __name__ == "__main__":
    main()

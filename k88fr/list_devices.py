"""Liste tous les périphériques HID connectés pour repérer le K88-FR."""

import hid


def main() -> None:
    for info in hid.enumerate():
        print(
            f"VID={info['vendor_id']:#06x} PID={info['product_id']:#06x} "
            f"iface={info['interface_number']} "
            f"usage_page={info.get('usage_page')} usage={info.get('usage')} "
            f"product={info.get('product_string')!r} "
            f"manufacturer={info.get('manufacturer_string')!r} "
            f"path={info['path']!r}"
        )


if __name__ == "__main__":
    main()

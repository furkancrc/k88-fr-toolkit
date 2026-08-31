"""Extrait toutes les sequences de sauvegarde persistante d'une capture.

Permet de recolter plusieurs couleurs en UNE seule session Wireshark : il
suffit d'appliquer les couleurs les unes apres les autres dans le logiciel
officiel pendant que la capture tourne.

Usage:
    python -m k88fr.tools.harvest_captures capture1.pcapng [capture2.pcapng ...]

Affiche un bloc pret a coller dans k88fr/presets.py.
"""

import subprocess
import sys

TSHARK = r"C:\Program Files\Wireshark\tshark.exe"

RGB_OFFSETS = (10, 11, 12)


def read_writes(path: str) -> list[bytes]:
    """Retourne les charges utiles SET_REPORT de la capture, dans l'ordre."""
    out = subprocess.run(
        [TSHARK, "-r", path, "-Y", '_ws.col.info contains "SET_REPORT Request"',
         "-T", "fields", "-e", "usb.data_fragment"],
        capture_output=True, text=True, check=True,
    )
    payloads = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line:
            try:
                payloads.append(bytes.fromhex(line))
            except ValueError:
                pass
    return payloads


def extract_sequences(payloads: list[bytes]) -> list[dict]:
    """Repere les blocs  open(09 02) / 0x45 / 0x45 / close(09 07) / 0x3f."""
    results = []
    i = 0
    while i < len(payloads):
        p = payloads[i]
        if p[:2] == b"\x09\x02":
            block = [p]
            j = i + 1
            while j < len(payloads) and len(block) < 6:
                block.append(payloads[j])
                if payloads[j][0] == 0x3F:
                    break
                j += 1
            ids = [b[0] for b in block]
            if ids.count(0x45) == 2 and block[-1][0] == 0x3F:
                chunk = next(b for b in block if b[0] == 0x45)
                rgb = tuple(chunk[o] for o in RGB_OFFSETS)
                checksum = (block[-1][1] << 8) | block[-1][2]
                results.append({"rgb": rgb, "checksum": checksum,
                                "sequence": [b.hex() for b in block]})
            i = j + 1
        else:
            i += 1
    return results


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    found = {}
    for path in sys.argv[1:]:
        try:
            seqs = extract_sequences(read_writes(path))
        except subprocess.CalledProcessError as e:
            print(f"{path}: erreur tshark ({e})", file=sys.stderr)
            continue
        print(f"{path}: {len(seqs)} sequence(s)")
        for s in seqs:
            r, g, b = s["rgb"]
            print(f"    rgb({r:3d}, {g:3d}, {b:3d})  checksum={s['checksum']:#06x}")
            found[s["rgb"]] = s

    if not found:
        return

    print(f"\n{len(found)} couleur(s) distincte(s). Bloc pour k88fr/presets.py :\n")
    for rgb, s in sorted(found.items()):
        r, g, b = rgb
        name = f"rgb_{r:02x}{g:02x}{b:02x}"
        print(f'    "{name}": {{')
        print(f'        "rgb": ({r}, {g}, {b}),')
        print(f'        "sequence": [')
        for h in s["sequence"]:
            print(f'            "{h}",')
        print("        ],")
        print("    },")


if __name__ == "__main__":
    main()

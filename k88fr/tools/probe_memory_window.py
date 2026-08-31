"""Teste si le clavier expose une fenetre de lecture memoire.

Indices : les rapports 0x40 et 0x41 font 4 octets (taille d'une adresse) et
sont en ecriture seule ; 0x42 et 0x43 font 2052 octets et renvoient des
donnees stables. C'est la forme habituelle d'une interface de lecture
memoire : on ecrit une adresse d'un cote, on lit le contenu de l'autre.

Si c'est confirme, on peut extraire le firmware du clavier et y trouver la
routine de verification du checksum -- sans jamais toucher au logiciel
officiel.
"""

import time

import hid

from k88fr.led import _find_path

WINDOWS = (0x42, 0x43, 0x44, 0x45)
ADDRESS_REGS = (0x40, 0x41, 0x30)


def read_window(path, report_id, size=2053):
    dev = hid.device()
    dev.open_path(path)
    try:
        return bytes(dev.get_feature_report(report_id, size))
    except Exception:
        return None
    finally:
        dev.close()


def write_reg(path, report_id, value: int, width: int = 4) -> bool:
    dev = hid.device()
    dev.open_path(path)
    try:
        payload = bytes([report_id]) + value.to_bytes(width, "little")
        dev.send_feature_report(payload)
        return True
    except Exception:
        return False
    finally:
        dev.close()
        time.sleep(0.08)


def main() -> None:
    path = _find_path()

    print("Etat de reference des fenetres :")
    base = {}
    for rid in WINDOWS:
        size = 2053 if rid in (0x42, 0x43) else 261
        data = read_window(path, rid, size)
        base[rid] = data
        if data:
            print(f"  {rid:#04x}: {len(data)} octets, debut {data[1:13].hex()}")

    print("\nEcriture d'adresses dans les registres candidats, puis relecture :")
    for reg in ADDRESS_REGS:
        for addr in (0x0000, 0x1000, 0x8000):
            ok = write_reg(path, reg, addr)
            if not ok:
                print(f"  registre {reg:#04x} <- {addr:#06x} : ecriture refusee")
                continue
            changed = []
            for rid in WINDOWS:
                size = 2053 if rid in (0x42, 0x43) else 261
                data = read_window(path, rid, size)
                if data and base[rid] and data != base[rid]:
                    diff = sum(1 for a, b in zip(data, base[rid]) if a != b)
                    changed.append(f"{rid:#04x} ({diff} octets differents)")
            verdict = ", ".join(changed) if changed else "aucun changement"
            print(f"  registre {reg:#04x} <- {addr:#06x} : {verdict}")

    print("\nSi une fenetre change selon l'adresse ecrite, on peut extraire le firmware.")


if __name__ == "__main__":
    main()

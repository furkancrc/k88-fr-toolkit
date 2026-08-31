"""Cherche une commande "enregistre l'etat courant" dans le clavier.

Si elle existe, le firmware calcule lui-meme son checksum et on n'a plus
besoin de le connaitre : on applique n'importe quelle couleur par le chemin
volatile (qui accepte tout), puis on demande la sauvegarde.

Protocole du test :
  1. on met le flash a une couleur temoin connue (rouge)
  2. on applique du magenta en volatile (impossible a sauvegarder autrement)
  3. on envoie une serie de commandes candidates
  4. un seul debranchement suffit : si le clavier revient en MAGENTA, l'une
     d'elles a declenche la sauvegarde -> on la retrouve ensuite par dichotomie

Les commandes testees ont toutes ete observees dans les captures du logiciel
officiel : on n'envoie pas d'opcode inconnu au hasard, pour ne pas risquer de
basculer le clavier dans un mode indesirable.
"""

import time

import hid

from k88fr.led import CLOSE_EDIT, OPEN_EDIT, K88FR, _find_path, _report9

TARGET = (0xFF, 0x00, 0xFF)  # magenta


def candidates() -> list[tuple[str, bytes]]:
    out = []
    # opcodes du rapport 9 vus dans les captures
    for op in (0x01, 0x02, 0x07, 0x21, 0x22):
        out.append((f"report9 opcode {op:#04x}", _report9(op)))
    # rapport 0x19 (1 octet) vu en boucle autour des sauvegardes
    for v in (0x00, 0x01):
        out.append((f"feature 0x19 = {v:#04x}", bytes([0x19, v])))
    # rapports 1 octet voisins, lisibles donc existants
    for rid in (0x16, 0x17):
        for v in (0x00, 0x01):
            out.append((f"feature {rid:#04x} = {v:#04x}", bytes([rid, v])))
    return out


def send(path, report: bytes) -> None:
    dev = hid.device()
    dev.open_path(path)
    try:
        if report[0] == 0x09:
            dev.write(report)
        else:
            dev.send_feature_report(report)
    except Exception as e:
        print(f"      (echec: {e})")
    finally:
        dev.close()
    time.sleep(0.12)


def main() -> None:
    from k88fr.persist import apply_persistent

    path = _find_path()

    print("1) flash mis au rouge temoin")
    apply_persistent("rouge")
    time.sleep(0.4)

    print("2) magenta applique en volatile")
    with K88FR() as kb:
        kb.set_color(*TARGET)
    time.sleep(0.3)

    print("3) envoi des commandes candidates :")
    for name, report in candidates():
        print(f"   -> {name}")
        send(path, report)
        # on remet le magenta au cas ou la commande l'aurait reinitialise
        with K88FR() as kb:
            kb.set_color(*TARGET)
        time.sleep(0.1)

    print()
    print(">>> DEBRANCHE puis REBRANCHE le clavier.")
    print("    MAGENTA  -> une commande sauvegarde l'etat courant : on tient la solution")
    print("    ROUGE    -> aucune ne sauvegarde, le temoin a survecu")


if __name__ == "__main__":
    main()

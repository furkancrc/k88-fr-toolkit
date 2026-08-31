"""Retrouve le checksum d'une couleur par dichotomie, avec le clavier seul.

Repose sur trois proprietes etablies au banc d'essai :
  1. le profil depose (rapports 0x45) survit a un checksum refuse, donc on
     peut le deposer une fois puis enchainer des essais legers (~3 ms) ;
  2. une sauvegarde validee survit aux checksums faux envoyes ensuite, donc on
     peut tester tout un LOT de candidats avant de verifier ;
  3. la reussite n'est visible qu'au rebranchement (aucun rapport lisible ne
     change), d'ou un debranchement par tour.

Deroulement d'un tour : on remet une couleur de reference en flash, on depose
la couleur cible, on envoie la moitie des candidats restants, puis tu
debranches. Si la cible a survecu, le bon checksum etait dans cette moitie.
16 tours suffisent pour isoler une valeur parmi 65536.

Usage :
    python -m k88fr.tools.crack_checksum start <R> <G> <B>
    python -m k88fr.tools.crack_checksum oui      # la cible a survecu
    python -m k88fr.tools.crack_checksum non      # la reference a survecu
"""

import json
import os
import sys
import time

import hid

from k88fr.led import _find_path
from k88fr.persist import apply_persistent
from k88fr.presets import PERSISTENT_PRESETS

STATE = os.path.join(os.path.dirname(__file__), "_crack_state.json")
RGB_OFFSETS = (10, 11, 12)


def staging_reports(rgb) -> list[bytes]:
    """Sequence de depot du profil (tout sauf le checksum), couleur patchee.

    Le champ de controle interne du rapport 0x45 est recalcule : sans cela le
    profil est structurellement invalide et le firmware le refuse quel que
    soit le checksum externe.
    """
    from k88fr.profile import with_color

    out = []
    for report in (bytes.fromhex(h) for h in PERSISTENT_PRESETS["rouge"]["sequence"]):
        if report[0] == 0x3F:
            continue
        out.append(with_color(report, rgb) if report[0] == 0x45 else report)
    return out


def send_one(path, report, delay=0.1):
    dev = hid.device()
    dev.open_path(path)
    try:
        if report[0] in (0x3F, 0x45):
            dev.send_feature_report(report)
        else:
            dev.write(report)
    finally:
        dev.close()
    time.sleep(delay)


def send_batch(path, values) -> float:
    """Envoie une salve de checksums sur un handle unique (rapide)."""
    t0 = time.perf_counter()
    dev = hid.device()
    dev.open_path(path)
    try:
        for v in values:
            dev.send_feature_report(bytes([0x3F, (v >> 8) & 0xFF, v & 0xFF]))
    finally:
        dev.close()
    return time.perf_counter() - t0


def run_round(state) -> None:
    path = _find_path()
    rgb = tuple(state["rgb"])
    reference = state["reference"]
    lo, hi = state["lo"], state["hi"]

    milieu = (lo + hi) // 2
    batch = list(range(lo, milieu + 1))
    state["sent"] = [lo, milieu]

    print(f"Tour {state['round']} — {hi - lo + 1} candidats restants "
          f"([{lo:#06x}, {hi:#06x}])")
    print(f"  reference {reference} remise en flash…")
    apply_persistent(reference)
    time.sleep(0.5)

    print(f"  depot du profil cible rgb{rgb}…")
    for r in staging_reports(rgb):
        send_one(path, r)
    time.sleep(0.2)

    print(f"  envoi de {len(batch)} candidats [{lo:#06x} … {milieu:#06x}]…")
    duree = send_batch(path, batch)
    print(f"  fait en {duree:.1f}s ({duree / max(len(batch), 1) * 1000:.1f} ms/essai)")

    state["round"] += 1
    with open(STATE, "w") as f:
        json.dump(state, f)

    print()
    print(">>> DEBRANCHE puis REBRANCHE le clavier, et relance avec :")
    print(f"      python -m k88fr.tools.crack_checksum oui   (si le clavier est rgb{rgb})")
    print(f"      python -m k88fr.tools.crack_checksum non   (s'il est {reference})")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "start":
        r, g, b = (int(x) for x in sys.argv[2:5])
        reference = "vert" if (r, g, b) != (0, 255, 0) else "rouge"
        state = {"rgb": [r, g, b], "reference": reference,
                 "lo": 0x0000, "hi": 0xFFFF, "round": 1}
        run_round(state)
        return

    if cmd not in ("oui", "non", "refaire"):
        print(__doc__)
        sys.exit(1)

    with open(STATE) as f:
        state = json.load(f)

    if cmd == "refaire":
        # rejoue le tour courant a l'identique (utile si l'etat du clavier a
        # ete perturbe entre l'envoi et la verification)
        state["round"] -= 1
        run_round(state)
        return

    lo, milieu = state["sent"]
    if cmd == "oui":
        state["lo"], state["hi"] = lo, milieu          # le bon etait dans le lot
    else:
        state["lo"], state["hi"] = milieu + 1, state["hi"]

    if state["lo"] == state["hi"]:
        valeur = state["lo"]
        rgb = tuple(state["rgb"])
        print(f"\n*** CHECKSUM TROUVE pour rgb{rgb} : {valeur:#06x} ***\n")
        print("Ajoute-le aux mesures connues pour retrouver la formule.")
        return

    run_round(state)


if __name__ == "__main__":
    main()

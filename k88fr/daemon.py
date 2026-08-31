"""Démon de persistance : réapplique en continu la couleur choisie par
l'utilisateur, pour compenser le fait que le clavier ne la sauvegarde pas
en mémoire flash (elle revient au vert par défaut au débranchement ou à
un appui sur une touche d'effet).

Conçu pour tourner en fond (lancé au démarrage de Windows). N'affiche rien
et ne plante jamais silencieusement : retente en boucle si le clavier
n'est pas branché ou disparaît.
"""

import sys
import time

from k88fr.config import load_color
from k88fr.led import K88FR, KeyboardNotFoundError

POLL_INTERVAL_SECONDS = 2


def _colors_differ(current_report: bytes, r: int, g: int, b: int) -> bool:
    return len(current_report) < 9 or (current_report[6], current_report[7], current_report[8]) != (r, g, b)


def run(poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    print("k88fr daemon: surveillance de la couleur RGB démarrée.", flush=True)
    last_applied = None

    while True:
        desired = load_color()
        if desired is None:
            time.sleep(poll_interval)
            continue

        try:
            with K88FR() as kb:
                current = kb.get_status_report()
                if _colors_differ(current, *desired):
                    kb.set_color(*desired)
                    if desired != last_applied:
                        print(f"Couleur réappliquée: rgb{desired}", flush=True)
                    last_applied = desired
        except KeyboardNotFoundError:
            pass  # clavier débranché, on retentera au prochain tour
        except OSError:
            pass  # erreur transitoire d'accès au device

        time.sleep(poll_interval)


def main() -> None:
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()

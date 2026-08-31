"""Active/désactive le lancement automatique du démon de persistance au
démarrage de Windows, via un script VBS invisible dans le dossier Startup
de l'utilisateur (pas besoin de droits admin, ni de dépendance pywin32)."""

import os
import sys

STARTUP_DIR = os.path.join(
    os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
)
STARTUP_SCRIPT = os.path.join(STARTUP_DIR, "k88fr-daemon.vbs")


def _launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --daemon'
    return f'"{sys.executable}" -m k88fr.gui --daemon'


def is_enabled() -> bool:
    return os.path.exists(STARTUP_SCRIPT)


def enable() -> None:
    os.makedirs(STARTUP_DIR, exist_ok=True)
    cmd = _launch_command().replace('"', '""')
    vbs = f'CreateObject("WScript.Shell").Run "{cmd}", 0, False\n'
    with open(STARTUP_SCRIPT, "w", encoding="utf-8") as f:
        f.write(vbs)


def disable() -> None:
    if os.path.exists(STARTUP_SCRIPT):
        os.remove(STARTUP_SCRIPT)

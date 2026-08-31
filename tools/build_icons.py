"""Prépare les déclinaisons du logo à partir du fichier source.

Produit trois fichiers dans `assets/` :

- `logo.png`  : le logo d'origine, recadré sur son contenu
- `icon.ico`  : icône multi-tailles pour la fenêtre et la barre des tâches
- `tray.png`  : variante à trait clair pour la zone de notification, dont le
  fond est sombre sous Windows — le V noir du logo y serait invisible

Usage : python tools/build_icons.py <chemin du logo source>
"""

import os
import sys

from PIL import Image

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
TRAY_STROKE = (235, 237, 242)  # gris très clair, lisible sur barre sombre


def trim(image: Image.Image) -> Image.Image:
    """Recadre sur les pixels non transparents, avec une marge relative."""
    bbox = image.getbbox()
    if not bbox:
        return image
    image = image.crop(bbox)
    marge = max(image.size) // 20
    carre = max(image.size) + 2 * marge
    fond = Image.new("RGBA", (carre, carre), (0, 0, 0, 0))
    fond.paste(image, ((carre - image.width) // 2, (carre - image.height) // 2))
    return fond


def lighten_dark_strokes(image: Image.Image, seuil: int = 90) -> Image.Image:
    """Remplace les traits sombres par un gris clair, en gardant les couleurs."""
    out = image.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = pixels[x, y]
            if a > 20 and max(r, g, b) < seuil:
                pixels[x, y] = (*TRAY_STROKE, a)
    return out


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else None
    if not source or not os.path.exists(source):
        print(__doc__)
        sys.exit(1)

    os.makedirs(ASSETS, exist_ok=True)
    logo = trim(Image.open(source).convert("RGBA"))

    logo.save(os.path.join(ASSETS, "logo.png"))
    print(f"logo.png  {logo.size[0]}x{logo.size[1]}")

    logo.save(os.path.join(ASSETS, "icon.ico"),
              sizes=[(s, s) for s in ICO_SIZES])
    print(f"icon.ico  tailles {ICO_SIZES}")

    tray = lighten_dark_strokes(logo.resize((256, 256), Image.LANCZOS))
    tray.save(os.path.join(ASSETS, "tray.png"))
    print("tray.png  256x256, traits éclaircis pour barre sombre")


if __name__ == "__main__":
    main()

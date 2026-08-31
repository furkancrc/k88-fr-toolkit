"""Prépare les déclinaisons du logo à partir du fichier source.

Produit dans `assets/` :

- `logo.png`  : le logo d'origine, recadré sur son contenu (pour le README)
- `icon.ico`  : icône multi-tailles, chaque taille rendue séparément
- `tray.png`  : image de la zone de notification

Deux décisions prises après contrôle visuel agrandi :

- **le V est recoloré en gris neutre** dans les icônes. Le noir d'origine est
  invisible sur une barre des tâches sombre, et un gris clair disparaîtrait
  sur une barre claire ; un gris moyen tient sur les deux.
- **chaque taille est rendue individuellement** (Lanczos puis renforcement de
  netteté) plutôt que de laisser l'encodeur réduire l'image d'origine, qui
  rendait les petites tailles floues.

Une variante recadrée sur les seules plumes a été essayée pour les petites
tailles : elle laisse des moignons noirs là où la découpe coupe le V, et le
logo entier reste lisible à 16 px. Abandonnée.

Usage : python tools/build_icons.py <chemin du logo source>
"""

import os
import sys

from PIL import Image, ImageFilter

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
STROKE = (154, 160, 170)   # gris neutre, lisible sur barre claire comme sombre
DARK_THRESHOLD = 90


def trim(image: Image.Image, margin_ratio: float = 0.02) -> Image.Image:
    """Recadre sur les pixels visibles et centre dans un carré."""
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    marge = int(max(image.size) * margin_ratio)
    cote = max(image.size) + 2 * marge
    fond = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
    fond.paste(image, ((cote - image.width) // 2, (cote - image.height) // 2))
    return fond


def recolor_dark(image: Image.Image, couleur=STROKE) -> Image.Image:
    """Remplace les traits sombres, en laissant les couleurs intactes."""
    out = image.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = pixels[x, y]
            if a > 20 and max(r, g, b) < DARK_THRESHOLD:
                pixels[x, y] = (*couleur, a)
    return out


def render(image: Image.Image, size: int) -> Image.Image:
    """Rend une taille, en restaurant la netteté perdue à la réduction."""
    out = image.resize((size, size), Image.LANCZOS)
    if size <= 64:
        rayon = 0.6 if size <= 24 else 1.0
        out = out.filter(ImageFilter.UnsharpMask(radius=rayon, percent=140, threshold=2))
    return out


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else None
    if not source or not os.path.exists(source):
        print(__doc__)
        sys.exit(1)

    os.makedirs(ASSETS, exist_ok=True)
    logo = trim(Image.open(source).convert("RGBA"))
    icone = recolor_dark(logo)

    logo.save(os.path.join(ASSETS, "logo.png"))
    print(f"logo.png  {logo.size[0]}x{logo.size[1]}  (original, pour le README)")

    frames = [render(icone, s) for s in ICO_SIZES]
    frames[-1].save(os.path.join(ASSETS, "icon.ico"), format="ICO",
                    sizes=[(s, s) for s in ICO_SIZES], append_images=frames[:-1])
    print(f"icon.ico  {ICO_SIZES}  (V en gris neutre, netteté renforcée)")

    render(icone, 64).save(os.path.join(ASSETS, "tray.png"))
    print("tray.png  64x64")

    # planche de contrôle : tailles réelles agrandies, sur fond clair et sombre
    tailles, zoom = (16, 24, 32, 48), 7
    largeur = sum(t * zoom + 18 for t in tailles) + 20
    hauteur = 48 * zoom + 30
    planche = Image.new("RGBA", (largeur, hauteur * 2), (0, 0, 0, 0))
    for i, fond in (((0), (30, 31, 36, 255)), ((1), (245, 245, 247, 255))):
        bande = Image.new("RGBA", (largeur, hauteur), fond)
        x = 16
        for t in tailles:
            bande.alpha_composite(
                render(icone, t).resize((t * zoom, t * zoom), Image.NEAREST), (x, 14))
            x += t * zoom + 18
        planche.alpha_composite(bande, (0, i * hauteur))
    planche.save(os.path.join(ASSETS, "apercu_icones.png"))
    print("apercu_icones.png  (contrôle visuel agrandi)")


if __name__ == "__main__":
    main()

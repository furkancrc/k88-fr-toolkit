"""Interface graphique pour piloter et sauvegarder la couleur du K88-FR."""

import threading
import tkinter
import tkinter.colorchooser

import customtkinter

from k88fr import persist
from k88fr.config import load_color, save_color
from k88fr.led import K88FR, KeyboardNotFoundError

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

PRESETS = [
    ("Rouge", "#FF0000"), ("Vert", "#00FF00"), ("Bleu", "#0000FF"),
    ("Blanc", "#FFFFFF"), ("Jaune", "#FFFF00"), ("Cyan", "#00FFFF"),
    ("Magenta", "#FF00FF"), ("Orange", "#FF8800"), ("Violet", "#8000FF"),
    ("Rose", "#FF0080"), ("Turquoise", "#00FF80"), ("Vert pomme", "#80FF00"),
]


class App(customtkinter.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("K88-FR — Contrôle RGB")
        self.geometry("500x620")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            self, text="AmazonBasics K88-FR",
            font=customtkinter.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, pady=(24, 0))

        customtkinter.CTkLabel(
            self, text="Toute couleur, sauvegardée dans le clavier",
            font=customtkinter.CTkFont(size=13), text_color="#888888",
        ).grid(row=1, column=0, pady=(0, 18))

        self.preview = customtkinter.CTkFrame(
            self, width=110, height=110, corner_radius=55, fg_color="#00FF00"
        )
        self.preview.grid(row=2, column=0, pady=(0, 20))
        self.preview.grid_propagate(False)

        palette = customtkinter.CTkFrame(self, fg_color="transparent")
        palette.grid(row=3, column=0, padx=24, pady=(0, 12), sticky="ew")
        palette.grid_columnconfigure((0, 1, 2, 3), weight=1)

        for i, (name, hexval) in enumerate(PRESETS):
            customtkinter.CTkButton(
                palette, text=name, fg_color=hexval, hover_color=hexval,
                text_color=self._contrast_text(hexval), corner_radius=10,
                command=lambda h=hexval: self.apply(h),
            ).grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky="ew")

        customtkinter.CTkButton(
            self, text="Choisir une couleur personnalisée…",
            command=self.open_color_picker, corner_radius=10,
        ).grid(row=4, column=0, padx=24, pady=(8, 6), sticky="ew")

        customtkinter.CTkButton(
            self, text="Éteindre", fg_color="#333333", hover_color="#444444",
            command=lambda: self.apply("#000000"), corner_radius=10,
        ).grid(row=5, column=0, padx=24, pady=(0, 16), sticky="ew")

        info = customtkinter.CTkFrame(self, corner_radius=10)
        info.grid(row=6, column=0, padx=24, pady=(0, 8), sticky="ew")
        info.grid_columnconfigure(0, weight=1)
        customtkinter.CTkLabel(
            info,
            text=("✓ La couleur est écrite dans la mémoire du clavier.\n"
                  "Elle survit au débranchement et au redémarrage,\n"
                  "sans qu'aucun logiciel ait besoin de tourner."),
            font=customtkinter.CTkFont(size=11), text_color="#4CAF50",
            justify="left",
        ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.status = customtkinter.CTkLabel(
            self, text="Prêt.", text_color="#888888",
            font=customtkinter.CTkFont(size=12),
        )
        self.status.grid(row=7, column=0, pady=(4, 14))

        saved = load_color()
        if saved:
            self.preview.configure(fg_color="#{:02x}{:02x}{:02x}".format(*saved))

    @staticmethod
    def _contrast_text(hexval: str) -> str:
        r, g, b = (int(hexval[i : i + 2], 16) for i in (1, 3, 5))
        return "#000000" if 0.299 * r + 0.587 * g + 0.114 * b > 140 else "#FFFFFF"

    def open_color_picker(self) -> None:
        result = tkinter.colorchooser.askcolor(title="Choisir une couleur")
        if result and result[1]:
            self.apply(result[1])

    def apply(self, hexval: str) -> None:
        r, g, b = (int(hexval[i : i + 2], 16) for i in (1, 3, 5))
        self.preview.configure(fg_color=hexval)
        self.status.configure(text="Écriture dans le clavier…", text_color="#888888")
        self.update_idletasks()
        save_color(r, g, b)

        def worker() -> None:
            try:
                with K88FR() as kb:
                    kb.set_color(r, g, b)      # effet immédiat
                persist.save_color(r, g, b)    # puis sauvegarde durable
                self.after(0, lambda: self.status.configure(
                    text=f"rgb({r}, {g}, {b}) sauvegardé dans le clavier",
                    text_color="#4CAF50"))
            except KeyboardNotFoundError as e:
                self.after(0, lambda: self.status.configure(
                    text=f"Erreur : {e}", text_color="#F44336"))
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self.status.configure(
                    text=f"Erreur inattendue : {e}", text_color="#F44336"))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()

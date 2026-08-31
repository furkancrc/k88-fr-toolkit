"""Interface graphique moderne pour piloter la couleur RGB du K88-FR."""

import sys
import threading
import tkinter
import tkinter.colorchooser

import customtkinter

from k88fr import autostart, persist
from k88fr.config import load_color, save_color
from k88fr.led import K88FR, KeyboardNotFoundError

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

PERSISTENT_COLORS = [
    ("Rouge", "rouge", "#FF0000"),
    ("Vert", "vert", "#00FF00"),
    ("Bleu", "bleu", "#0000FF"),
]

PREVIEW_PRESETS = [
    ("Blanc", "#FFFFFF"),
    ("Jaune", "#FFFF00"),
    ("Cyan", "#00FFFF"),
    ("Magenta", "#FF00FF"),
    ("Orange", "#FF8800"),
]


class App(customtkinter.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("K88-FR — Contrôle RGB")
        self.geometry("500x760")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)

        header = customtkinter.CTkLabel(
            self,
            text="AmazonBasics K88-FR",
            font=customtkinter.CTkFont(size=22, weight="bold"),
        )
        header.grid(row=0, column=0, pady=(24, 0))

        subheader = customtkinter.CTkLabel(
            self,
            text="Contrôle RGB (couleur unie, tout le clavier)",
            font=customtkinter.CTkFont(size=13),
            text_color="#888888",
        )
        subheader.grid(row=1, column=0, pady=(0, 16))

        self.preview = customtkinter.CTkFrame(
            self, width=100, height=100, corner_radius=50, fg_color="#00FF00"
        )
        self.preview.grid(row=2, column=0, pady=(0, 16))
        self.preview.grid_propagate(False)

        # --- Couleurs persistantes ---
        persist_section = customtkinter.CTkFrame(self, corner_radius=10)
        persist_section.grid(row=3, column=0, padx=24, pady=(0, 12), sticky="ew")
        persist_section.grid_columnconfigure((0, 1, 2), weight=1)

        customtkinter.CTkLabel(
            persist_section,
            text="✓ Couleurs persistantes (sauvegardées dans le clavier)",
            font=customtkinter.CTkFont(size=13, weight="bold"),
            text_color="#4CAF50",
        ).grid(row=0, column=0, columnspan=3, padx=12, pady=(10, 2), sticky="w")

        customtkinter.CTkLabel(
            persist_section,
            text="Survivent au débranchement — vraie sauvegarde flash du clavier.",
            font=customtkinter.CTkFont(size=11),
            text_color="#888888",
        ).grid(row=1, column=0, columnspan=3, padx=12, pady=(0, 10), sticky="w")

        for i, (name, key, hexval) in enumerate(PERSISTENT_COLORS):
            btn = customtkinter.CTkButton(
                persist_section,
                text=name,
                fg_color=hexval,
                hover_color=hexval,
                text_color=self._contrast_text(hexval),
                corner_radius=10,
                command=lambda k=key, h=hexval: self.apply_persistent_color(k, h),
            )
            btn.grid(row=2, column=i, padx=6, pady=(0, 12), sticky="ew")

        # --- Aperçu libre (temporaire) ---
        preview_section = customtkinter.CTkFrame(self, corner_radius=10)
        preview_section.grid(row=4, column=0, padx=24, pady=(0, 12), sticky="ew")
        preview_section.grid_columnconfigure((0, 1, 2, 3), weight=1)

        customtkinter.CTkLabel(
            preview_section,
            text="Aperçu libre (temporaire)",
            font=customtkinter.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, padx=12, pady=(10, 2), sticky="w")

        customtkinter.CTkLabel(
            preview_section,
            text="Toute couleur possible, mais revient au dernier profil\npersistant au débranchement (sauf si démarrage auto activé).",
            font=customtkinter.CTkFont(size=11),
            text_color="#888888",
            justify="left",
        ).grid(row=1, column=0, columnspan=4, padx=12, pady=(0, 10), sticky="w")

        for i, (name, hexval) in enumerate(PREVIEW_PRESETS):
            btn = customtkinter.CTkButton(
                preview_section,
                text=name,
                fg_color=hexval,
                hover_color=hexval,
                text_color=self._contrast_text(hexval),
                corner_radius=10,
                command=lambda h=hexval: self.apply_preview_color(h),
            )
            btn.grid(row=2, column=i % 4, padx=6, pady=(0, 8), sticky="ew")

        picker_btn = customtkinter.CTkButton(
            preview_section,
            text="Choisir une couleur personnalisée…",
            command=self.open_color_picker,
            corner_radius=10,
        )
        picker_btn.grid(row=3, column=0, columnspan=4, padx=12, pady=(0, 8), sticky="ew")

        off_btn = customtkinter.CTkButton(
            preview_section,
            text="Éteindre",
            fg_color="#333333",
            hover_color="#444444",
            command=lambda: self.apply_preview_color("#000000"),
            corner_radius=10,
        )
        off_btn.grid(row=4, column=0, columnspan=4, padx=12, pady=(0, 12), sticky="ew")

        # --- Persistance logicielle (pour l'aperçu libre) ---
        auto_section = customtkinter.CTkFrame(self, corner_radius=10)
        auto_section.grid(row=5, column=0, padx=24, pady=(0, 8), sticky="ew")
        auto_section.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            auto_section,
            text=(
                "Pour une couleur personnalisée (aperçu libre), la sauvegarde\n"
                "matérielle n'est pas cassée : cette option relance un petit\n"
                "programme au démarrage de Windows pour la réappliquer."
            ),
            font=customtkinter.CTkFont(size=11),
            text_color="#888888",
            justify="left",
        ).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self.autostart_switch = customtkinter.CTkSwitch(
            auto_section,
            text="Démarrer avec Windows (garder ma couleur personnalisée)",
            command=self.toggle_autostart,
        )
        self.autostart_switch.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")
        if autostart.is_enabled():
            self.autostart_switch.select()

        self.status = customtkinter.CTkLabel(
            self, text="Prêt.", text_color="#888888", font=customtkinter.CTkFont(size=12)
        )
        self.status.grid(row=6, column=0, pady=(8, 16))

    @staticmethod
    def _contrast_text(hexval: str) -> str:
        r, g, b = (int(hexval[i : i + 2], 16) for i in (1, 3, 5))
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "#000000" if luminance > 140 else "#FFFFFF"

    def toggle_autostart(self) -> None:
        if self.autostart_switch.get():
            autostart.enable()
            self.status.configure(text="Démarrage automatique activé.", text_color="#4CAF50")
        else:
            autostart.disable()
            self.status.configure(text="Démarrage automatique désactivé.", text_color="#888888")

    def open_color_picker(self) -> None:
        result = tkinter.colorchooser.askcolor(title="Choisir une couleur")
        if result and result[1]:
            self.apply_preview_color(result[1])

    def apply_persistent_color(self, key: str, hexval: str) -> None:
        self.preview.configure(fg_color=hexval)
        self.status.configure(text="Sauvegarde en cours (mémoire flash du clavier)…", text_color="#888888")
        self.update_idletasks()

        def worker() -> None:
            try:
                persist.apply_persistent(key)
                self.after(0, lambda: self.status.configure(
                    text=f"Couleur '{key}' sauvegardée dans le clavier ✓", text_color="#4CAF50"
                ))
            except KeyboardNotFoundError as e:
                self.after(0, lambda: self.status.configure(text=f"Erreur: {e}", text_color="#F44336"))
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self.status.configure(text=f"Erreur inattendue: {e}", text_color="#F44336"))

        threading.Thread(target=worker, daemon=True).start()

    def apply_preview_color(self, hexval: str) -> None:
        r, g, b = (int(hexval[i : i + 2], 16) for i in (1, 3, 5))
        self.preview.configure(fg_color=hexval)
        self.status.configure(text="Envoi en cours (aperçu temporaire)…", text_color="#888888")
        self.update_idletasks()

        save_color(r, g, b)

        def worker() -> None:
            try:
                with K88FR() as kb:
                    kb.set_color(r, g, b)
                self.after(0, lambda: self.status.configure(
                    text=f"Aperçu appliqué: rgb({r}, {g}, {b}) — temporaire", text_color="#4CAF50"
                ))
            except KeyboardNotFoundError as e:
                self.after(0, lambda: self.status.configure(text=f"Erreur: {e}", text_color="#F44336"))
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self.status.configure(text=f"Erreur inattendue: {e}", text_color="#F44336"))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    if "--daemon" in sys.argv:
        from k88fr.daemon import main as daemon_main

        daemon_main()
        return

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

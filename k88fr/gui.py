"""Interface graphique du K88-FR : aperçu immédiat et sauvegarde durable."""

import threading
import tkinter
import tkinter.colorchooser

import customtkinter

from k88fr import persist
from k88fr.config import load_color, save_color as remember_color
from k88fr.led import K88FR, KeyboardNotFoundError

customtkinter.set_appearance_mode("dark")

BG = "#15161A"
CARD = "#1E2027"
BORDER = "#2A2D36"
TEXT = "#E8E9ED"
MUTED = "#7D818C"
ACCENT = "#4C8DFF"
ACCENT_HOVER = "#3B7AE8"
SUCCESS = "#34D399"
DANGER = "#F87171"

PRESETS = [
    ("#FF0000", "Rouge"), ("#FF8800", "Orange"), ("#FFFF00", "Jaune"),
    ("#80FF00", "Citron"), ("#00FF00", "Vert"), ("#00FF80", "Menthe"),
    ("#00FFFF", "Cyan"), ("#0080FF", "Azur"), ("#0000FF", "Bleu"),
    ("#8000FF", "Violet"), ("#FF00FF", "Magenta"), ("#FF0080", "Rose"),
]


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _readable_on(hexval: str) -> str:
    r, g, b = _hex_to_rgb(hexval)
    return "#000000" if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "#FFFFFF"


class Card(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=14, fg_color=CARD,
                         border_width=1, border_color=BORDER, **kwargs)


class App(customtkinter.CTk):
    def __init__(self) -> None:
        super().__init__(fg_color=BG)

        self.title("K88-FR — Contrôle RGB")
        self.geometry("560x780")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)

        self._rgb = load_color() or (0, 255, 0)
        self._pending = None

        self._build_header()
        self._build_preview()
        self._build_sliders()
        self._build_palette()
        self._build_actions()

        self.status = customtkinter.CTkLabel(
            self, text="Prêt.", text_color=MUTED,
            font=customtkinter.CTkFont(size=12),
        )
        self.status.grid(row=5, column=0, pady=(4, 16))

        self._refresh_preview()
        self.after(200, self._check_keyboard)

    # ------------------------------------------------------------------ vues

    def _build_header(self) -> None:
        header = customtkinter.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=26, pady=(24, 18), sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        dot = customtkinter.CTkFrame(header, width=44, height=44, corner_radius=22,
                                     fg_color=ACCENT)
        dot.grid(row=0, column=0, rowspan=2, padx=(0, 14))
        dot.grid_propagate(False)
        customtkinter.CTkLabel(dot, text="K", text_color="#FFFFFF",
                               font=customtkinter.CTkFont(size=19, weight="bold")
                               ).place(relx=0.5, rely=0.5, anchor="center")

        customtkinter.CTkLabel(
            header, text="AmazonBasics K88-FR", text_color=TEXT, anchor="w",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=1, sticky="w")

        customtkinter.CTkLabel(
            header, text="Éclairage RGB · sauvegarde dans le clavier",
            text_color=MUTED, anchor="w", font=customtkinter.CTkFont(size=12),
        ).grid(row=1, column=1, sticky="w")

        self.pill = customtkinter.CTkFrame(header, corner_radius=11, height=24,
                                           fg_color="#2A2D36")
        self.pill.grid(row=0, column=2, rowspan=2, sticky="e")
        self.pill_label = customtkinter.CTkLabel(
            self.pill, text="  ● recherche…  ", text_color=MUTED,
            font=customtkinter.CTkFont(size=11, weight="bold"),
        )
        self.pill_label.pack(padx=4, pady=3)

    def _build_preview(self) -> None:
        card = Card(self)
        card.grid(row=1, column=0, padx=26, pady=(0, 14), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        self.swatch = customtkinter.CTkFrame(card, height=132, corner_radius=10,
                                             fg_color="#00FF00")
        self.swatch.grid(row=0, column=0, padx=14, pady=(14, 10), sticky="ew")
        self.swatch.grid_propagate(False)

        self.swatch_hex = customtkinter.CTkLabel(
            self.swatch, text="#00FF00",
            font=customtkinter.CTkFont(size=26, weight="bold"),
        )
        self.swatch_hex.place(relx=0.5, rely=0.5, anchor="center")

        self.swatch_rgb = customtkinter.CTkLabel(
            card, text="", text_color=MUTED, font=customtkinter.CTkFont(size=12),
        )
        self.swatch_rgb.grid(row=1, column=0, pady=(0, 14))

    def _build_sliders(self) -> None:
        card = Card(self)
        card.grid(row=2, column=0, padx=26, pady=(0, 14), sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        self.sliders = {}
        self.values = {}
        for i, (canal, couleur) in enumerate((("R", "#FF4D4D"),
                                              ("G", "#4DFF88"),
                                              ("B", "#4D8DFF"))):
            customtkinter.CTkLabel(
                card, text=canal, text_color=couleur, width=18,
                font=customtkinter.CTkFont(size=13, weight="bold"),
            ).grid(row=i, column=0, padx=(16, 8), pady=(14 if i == 0 else 6,
                                                        14 if i == 2 else 6))

            slider = customtkinter.CTkSlider(
                card, from_=0, to=255, number_of_steps=255,
                progress_color=couleur, button_color=couleur,
                button_hover_color=couleur, fg_color="#2A2D36",
                command=lambda v, c=canal: self._on_slider(c, v),
            )
            slider.grid(row=i, column=1, sticky="ew", pady=6)
            self.sliders[canal] = slider

            value = customtkinter.CTkLabel(
                card, text="0", text_color=TEXT, width=38,
                font=customtkinter.CTkFont(size=13),
            )
            value.grid(row=i, column=2, padx=(10, 16))
            self.values[canal] = value

    def _build_palette(self) -> None:
        card = Card(self)
        card.grid(row=3, column=0, padx=26, pady=(0, 14), sticky="ew")
        for col in range(6):
            card.grid_columnconfigure(col, weight=1)

        customtkinter.CTkLabel(
            card, text="PALETTE", text_color=MUTED, anchor="w",
            font=customtkinter.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, columnspan=6, padx=16, pady=(12, 6), sticky="w")

        for i, (hexval, nom) in enumerate(PRESETS):
            customtkinter.CTkButton(
                card, text="", width=58, height=38, corner_radius=9,
                fg_color=hexval, hover_color=hexval, border_width=0,
                command=lambda h=hexval: self.set_color(h),
            ).grid(row=1 + i // 6, column=i % 6, padx=5,
                   pady=(4, 14 if i >= 6 else 4))

    def _build_actions(self) -> None:
        row = customtkinter.CTkFrame(self, fg_color="transparent")
        row.grid(row=4, column=0, padx=26, pady=(0, 6), sticky="ew")
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=0)
        row.grid_columnconfigure(2, weight=0)

        customtkinter.CTkButton(
            row, text="Sauvegarder dans le clavier", height=44, corner_radius=11,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=customtkinter.CTkFont(size=14, weight="bold"),
            command=self.save_to_keyboard,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        customtkinter.CTkButton(
            row, text="Palette…", width=92, height=44, corner_radius=11,
            fg_color="#2A2D36", hover_color="#343843",
            command=self.open_color_picker,
        ).grid(row=0, column=1, padx=(0, 8))

        customtkinter.CTkButton(
            row, text="Éteindre", width=92, height=44, corner_radius=11,
            fg_color="#2A2D36", hover_color="#343843",
            command=lambda: self.set_color("#000000"),
        ).grid(row=0, column=2)

    # ------------------------------------------------------------- mécanique

    def _check_keyboard(self) -> None:
        def worker() -> None:
            try:
                with K88FR():
                    pass
                self.after(0, lambda: self._set_pill("● connecté", SUCCESS))
            except Exception:
                self.after(0, lambda: self._set_pill("● absent", DANGER))

        threading.Thread(target=worker, daemon=True).start()

    def _set_pill(self, text: str, color: str) -> None:
        self.pill_label.configure(text=f"  {text}  ", text_color=color)

    def _refresh_preview(self) -> None:
        r, g, b = self._rgb
        hexval = _rgb_to_hex(r, g, b)
        self.swatch.configure(fg_color=hexval)
        self.swatch_hex.configure(text=hexval, text_color=_readable_on(hexval))
        self.swatch_rgb.configure(text=f"R {r}   ·   G {g}   ·   B {b}")
        for canal, valeur in zip("RGB", (r, g, b)):
            self.sliders[canal].set(valeur)
            self.values[canal].configure(text=str(valeur))

    def _on_slider(self, canal: str, value: float) -> None:
        index = "RGB".index(canal)
        rgb = list(self._rgb)
        rgb[index] = int(value)
        self._rgb = tuple(rgb)
        self._refresh_preview()

        # on ne bombarde pas le clavier à chaque pixel de déplacement
        if self._pending is not None:
            self.after_cancel(self._pending)
        self._pending = self.after(120, self._push_live)

    def _push_live(self) -> None:
        self._pending = None
        rgb = self._rgb

        def worker() -> None:
            try:
                with K88FR() as kb:
                    kb.set_color(*rgb)
                self.after(0, lambda: self._say("Aperçu appliqué — non sauvegardé", MUTED))
            except Exception:
                self.after(0, lambda: self._say("Clavier introuvable", DANGER))

        threading.Thread(target=worker, daemon=True).start()

    def _say(self, text: str, color: str) -> None:
        self.status.configure(text=text, text_color=color)

    # ------------------------------------------------------------- actions

    def set_color(self, hexval: str) -> None:
        self._rgb = _hex_to_rgb(hexval)
        self._refresh_preview()
        self._push_live()

    def open_color_picker(self) -> None:
        result = tkinter.colorchooser.askcolor(title="Choisir une couleur")
        if result and result[1]:
            self.set_color(result[1])

    def save_to_keyboard(self) -> None:
        rgb = self._rgb
        self._say("Écriture dans la mémoire du clavier…", MUTED)
        remember_color(*rgb)

        def worker() -> None:
            try:
                persist.save_color(*rgb)
                self.after(0, lambda: self._say(
                    f"{_rgb_to_hex(*rgb)} sauvegardé — survit au débranchement", SUCCESS))
            except KeyboardNotFoundError as e:
                self.after(0, lambda: self._say(f"Erreur : {e}", DANGER))
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self._say(f"Erreur inattendue : {e}", DANGER))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()

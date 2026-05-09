"""
game_state.py — Tillstånd för en Yatzy-runda.

Ansvar:
    Hålla koll på kastantal, tärningsvärden och låsstatus.
    Exponera metoder för att registrera ett kast och starta ny runda.

Denna modul innehåller INGEN spellogik (poängberäkning, kategori-val)
och ingen renderingskod.
"""


class GameState:
    """Håller tillståndet för en aktiv spelrunda."""

    MAX_ROLLS = 3

    def __init__(self):
        self.roll_count:     int        = 0
        self.dice_values:    list       = ["-"] * 5   # bekräftade värden från senaste kast
        self.locked_dice:    list[bool] = [False] * 5
        self.show_score_menu: bool      = False        # True → visa popup, pausa kast

        self._live_values: list = ["-"] * 5            # YOLO-läsning från senaste frame

    # ------------------------------------------------------------------
    # Anropas varje frame av main.py
    # ------------------------------------------------------------------

    def update_live(self, values: list) -> None:
        """Spara senaste YOLO-detektioner för att kunna läsas in vid nästa kast."""
        self._live_values = values

    # ------------------------------------------------------------------
    # Kasthändelse (SPACE)
    # ------------------------------------------------------------------

    def roll(self) -> bool:
        """
        Registrera ett kast. Kopierar live-värden till dice_values för olåsta slots.

        Returnerar True om kastet godkändes, False om max antal kast uppnåtts.
        """
        if not self.can_roll():
            return False

        self.roll_count += 1
        for i, val in enumerate(self._live_values):
            if not self.locked_dice[i]:
                self.dice_values[i] = val

        return True

    def can_roll(self) -> bool:
        return self.roll_count < self.MAX_ROLLS

    # ------------------------------------------------------------------
    # Ny runda
    # ------------------------------------------------------------------

    def start_new_round(self) -> None:
        """Återställ allt inför en ny runda."""
        self.roll_count      = 0
        self.dice_values     = ["-"] * 5
        self.locked_dice     = [False] * 5
        self.show_score_menu = False
        self._live_values    = ["-"] * 5

    # ------------------------------------------------------------------
    # UI-hjälp
    # ------------------------------------------------------------------

    @property
    def roll_label(self) -> str:
        """Textsträng som beskriver rundans nuvarande fas."""
        if self.roll_count == 0:
            return "SPACE = kasta"
        if self.roll_count < self.MAX_ROLLS:
            return f"Kast {self.roll_count}/{self.MAX_ROLLS}  |  SPACE = kasta igen"
        return f"Kast {self.MAX_ROLLS}/{self.MAX_ROLLS}  -  Valj poangkategori"

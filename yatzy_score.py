"""
yatzy_score.py — Poängsystem för Yatzy, övre sektion.

Ansvar:
    Beräkna och lagra poäng för Ettor–Sexor, Summa och Bonus.
    Exponera raddata för rendering och ta emot kategori-val.

Denna modul innehåller INGEN renderingskod och INGEN kastlogik.
Den nedre sektionen implementeras som en separat klass senare.
"""


# Övre sektionens kategorier i visningsordning.
# Varje tuple: (intern nyckel, visningsnamn, tärningsvärde, snabbtangent)
UPPER_CATEGORIES: list[tuple[str, str, int, str]] = [
    ("ettor",  "Ettor",  1, "1"),
    ("tvaor",  "Tvaor",  2, "2"),
    ("treor",  "Treor",  3, "3"),
    ("fyror",  "Fyror",  4, "4"),
    ("femmor", "Femmor", 5, "5"),
    ("sexor",  "Sexor",  6, "6"),
]

# Snabbtangent → intern nyckel  (t.ex. "1" → "ettor")
HOTKEY_MAP: dict[str, str] = {
    hotkey: key for key, _, _, hotkey in UPPER_CATEGORIES
}


class YatzyScoreUpper:
    """Håller poängdata för övre sektionen i Yatzy."""

    BONUS_THRESHOLD = 63
    BONUS_POINTS    = 50

    def __init__(self):
        # None = ej vald, int = registrerad poäng
        self._scores: dict[str, int | None] = {
            key: None for key, _, _, _ in UPPER_CATEGORIES
        }

    # ------------------------------------------------------------------
    # Beräkning
    # ------------------------------------------------------------------

    def calculate(self, key: str, dice: list) -> int:
        """
        Beräkna potentiell poäng för en kategori mot givna tärningsvärden.

        Ignorerar "-"-platshållare (ej detekterade tärningar).
        """
        face = next(f for k, _, f, _ in UPPER_CATEGORIES if k == key)
        return sum(d for d in dice if isinstance(d, int) and d == face)

    # ------------------------------------------------------------------
    # Registrering
    # ------------------------------------------------------------------

    def register(self, key: str, dice: list) -> bool:
        """
        Lås in poäng för en kategori.

        Returnerar True om registreringen lyckades, False om kategorin
        redan är vald.
        """
        if self.is_locked(key):
            return False
        self._scores[key] = self.calculate(key, dice)
        return True

    def is_locked(self, key: str) -> bool:
        """Returnerar True om kategorin redan har ett registrerat värde."""
        return self._scores[key] is not None

    # ------------------------------------------------------------------
    # Summor
    # ------------------------------------------------------------------

    @property
    def total(self) -> int:
        """Summa av alla registrerade kategorier i övre sektionen."""
        return sum(v for v in self._scores.values() if v is not None)

    @property
    def bonus(self) -> int:
        """50 poäng bonus om total >= 63, annars 0."""
        return self.BONUS_POINTS if self.total >= self.BONUS_THRESHOLD else 0

    @property
    def bonus_progress(self) -> int:
        """Hur många poäng som saknas för bonus. 0 om bonus redan uppnådd."""
        return max(0, self.BONUS_THRESHOLD - self.total)

    # ------------------------------------------------------------------
    # Raddata för rendering
    # ------------------------------------------------------------------

    def rows(self, dice: list) -> list[dict]:
        """
        Returnerar en lista med en dict per kategori, redo för rendering.

        Varje dict:
            key     — intern nyckel
            label   — visningsnamn
            score   — registrerad poäng ELLER potentiell poäng mot nuvarande kast
            locked  — True om kategorin redan valts
            hotkey  — snabbtangent som sträng ("1"–"6")
        """
        result = []
        for key, label, _, hotkey in UPPER_CATEGORIES:
            locked = self.is_locked(key)
            score  = self._scores[key] if locked else self.calculate(key, dice)
            result.append({
                "key":    key,
                "label":  label,
                "score":  score,
                "locked": locked,
                "hotkey": hotkey,
            })
        return result

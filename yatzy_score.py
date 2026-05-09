"""
yatzy_score.py — Poängsystem för Yatzy, övre och nedre sektion.

Ansvar:
    Beräkna och lagra poäng för båda sektionerna.
    Exponera raddata för rendering och ta emot kategori-val.

Denna modul innehåller INGEN renderingskod och INGEN kastlogik.
"""

from collections import Counter


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

    def is_complete(self) -> bool:
        """True när alla 6 övre kategorier har ett värde (spelet kan avslutas)."""
        return all(v is not None for v in self._scores.values())

    def reset(self) -> None:
        """Återställ alla kategorier — används vid omstart av spelet."""
        self._scores = {key: None for key, _, _, _ in UPPER_CATEGORIES}

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
    def upper_total(self) -> int:
        """Övre sektionens slutpoäng: Summa + Bonus."""
        return self.total + self.bonus

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
            valid   — alltid True för övre sektionen
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
                "valid":  True,
                "hotkey": hotkey,
            })
        return result


# ==========================================================================
# Nedre sektionens kategorier
# Varje tuple: (intern nyckel, visningsnamn, snabbtangent)
# ==========================================================================

LOWER_CATEGORIES: list[tuple[str, str, str]] = [
    ("ett_par",     "Ett par",     "a"),
    ("tva_par",     "Tva par",     "b"),
    ("tretal",      "Tretal",      "c"),
    ("fyrtal",      "Fyrtal",      "d"),
    ("kok",         "Kok",         "e"),
    ("liten_stege", "Liten stege", "f"),
    ("stor_stege",  "Stor stege",  "g"),
    ("chans",       "Chans",       "h"),
    ("yatzy",       "Yatzy",       "i"),
]

LOWER_HOTKEY_MAP: dict[str, str] = {
    hotkey: key for key, _, hotkey in LOWER_CATEGORIES
}


class YatzyScoreLower:
    """Håller poängdata för nedre sektionen i Yatzy."""

    def __init__(self):
        self._scores: dict[str, int | None] = {
            key: None for key, _, _ in LOWER_CATEGORIES
        }
        self._struck: set[str] = set()   # kategorier som stryks (0 poäng, permanent låsta)

    # ------------------------------------------------------------------
    # Beräkning
    # ------------------------------------------------------------------

    def calculate(self, key: str, dice: list) -> tuple[int, bool]:
        """
        Beräknar (poäng, valbar) för en kategori mot givna tärningsvärden.

        Returnerar (0, False) om kombinationen inte är möjlig eller om
        inte exakt 5 heltalsvärden finns.
        """
        ints = [d for d in dice if isinstance(d, int)]
        if len(ints) < 5:
            return (0, False)

        counts = Counter(ints)

        if key == "ett_par":
            pairs = [v for v, c in counts.items() if c >= 2]
            if pairs:
                return (max(pairs) * 2, True)
            return (0, False)

        if key == "tva_par":
            # Kräver minst två OLIKA värden som båda förekommer minst två gånger
            pair_values = sorted([v for v, c in counts.items() if c >= 2], reverse=True)
            if len(pair_values) >= 2:
                return (pair_values[0] * 2 + pair_values[1] * 2, True)
            return (0, False)

        if key == "tretal":
            triples = [v for v, c in counts.items() if c >= 3]
            if triples:
                return (max(triples) * 3, True)
            return (0, False)

        if key == "fyrtal":
            quads = [v for v, c in counts.items() if c >= 4]
            if quads:
                return (max(quads) * 4, True)
            return (0, False)

        if key == "kok":
            # Exakt ett tretal + exakt ett par — Yatzy (5 lika) räknas inte
            has_triple = any(c == 3 for c in counts.values())
            has_pair   = any(c == 2 for c in counts.values())
            if has_triple and has_pair:
                return (sum(ints), True)
            return (0, False)

        if key == "liten_stege":
            if sorted(ints) == [1, 2, 3, 4, 5]:
                return (15, True)
            return (0, False)

        if key == "stor_stege":
            if sorted(ints) == [2, 3, 4, 5, 6]:
                return (20, True)
            return (0, False)

        if key == "chans":
            return (sum(ints), True)

        if key == "yatzy":
            if len(counts) == 1:
                return (50, True)
            return (0, False)

        return (0, False)

    # ------------------------------------------------------------------
    # Registrering
    # ------------------------------------------------------------------

    def register(self, key: str, dice: list) -> bool:
        """
        Lås in poäng för en kategori.

        Returnerar False om kategorin redan är vald eller ej valbar.
        """
        if self.is_locked(key):
            return False
        score, valid = self.calculate(key, dice)
        if not valid:
            return False
        self._scores[key] = score
        return True

    def strike(self, key: str) -> bool:
        """
        Struk en kategori — sätter poäng till 0 och låser den permanent.

        Returnerar False om kategorin redan är vald eller struken.
        """
        if self.is_locked(key):
            return False
        self._struck.add(key)
        self._scores[key] = 0
        return True

    def is_locked(self, key: str) -> bool:
        return self._scores[key] is not None

    def is_struck(self, key: str) -> bool:
        return key in self._struck

    def is_complete(self) -> bool:
        """True när alla 9 nedre kategorier har ett värde (spelet kan avslutas)."""
        return all(v is not None for v in self._scores.values())

    def reset(self) -> None:
        """Återställ alla kategorier och stryk — används vid omstart av spelet."""
        self._scores = {key: None for key, _, _ in LOWER_CATEGORIES}
        self._struck = set()

    # ------------------------------------------------------------------
    # Summor
    # ------------------------------------------------------------------

    @property
    def total(self) -> int:
        return sum(v for v in self._scores.values() if v is not None)

    # ------------------------------------------------------------------
    # Raddata för rendering
    # ------------------------------------------------------------------

    def rows(self, dice: list) -> list[dict]:
        """
        Returnerar en lista med en dict per kategori, redo för rendering.

        Varje dict:
            key     — intern nyckel
            label   — visningsnamn
            score   — registrerad poäng ELLER potentiell poäng
            locked  — True om kategorin redan valts
            valid   — False om kombinationen ej är möjlig (grå, ej valbar)
            hotkey  — snabbtangent ("a"–"i")
        """
        result = []
        for key, label, hotkey in LOWER_CATEGORIES:
            locked = self.is_locked(key)
            struck = self.is_struck(key)
            if locked:
                score, valid = self._scores[key], True
            else:
                score, valid = self.calculate(key, dice)
            result.append({
                "key":    key,
                "label":  label,
                "score":  score,
                "locked": locked,
                "struck": struck,
                "valid":  valid,
                "hotkey": hotkey,
            })
        return result

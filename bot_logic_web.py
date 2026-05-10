"""
bot_logic_web.py — Ren beslutslogik för bot (webbversionen).

Ingen timing, ingen state-maskin. Flask-endpointen anropar dessa funktioner
synkront och returnerar resultatet direkt. JavaScript-sidan hanterar alla
animationsförseningar med setTimeout och CSS-transitions.

Samma prioriteringsstrategi som bot_logic.py:
  1. Bonus-jakt      (övre kategori med count >= 2, 6 → 1)
  2. Starka komb.    (Yatzy → Kåk → Stegor → Fyrtal → Tretal → Två par → Par)
  3. Övre sektion    (högst poäng bland tillgängliga)
  4. Chans           (sista alternativ med faktisk poäng)
  5. Stryk / Fallback
"""

import random
from collections import Counter

from yatzy_score import UPPER_CATEGORIES, LOWER_CATEGORIES

# ── Uppslagstabeller (byggs en gång vid import) ──────────────────────────────
_FACE_TO_KEY   = {face: key   for key, _lbl, face, _hk in UPPER_CATEGORIES}
_FACE_TO_LABEL = {face: label for _k,  label, face, _hk in UPPER_CATEGORIES}
_LOWER_LABEL   = {key: label  for key, label, _hk       in LOWER_CATEGORIES}

_STRONG_LOWER_PRIORITY = [
    "yatzy", "kok", "stor_stege", "liten_stege",
    "fyrtal", "tretal", "tva_par", "ett_par",
]


# ── Publika funktioner ────────────────────────────────────────────────────────

def roll_dice() -> list[int]:
    """Generera 5 slumptärningar (1–6) för boten."""
    return [random.randint(1, 6) for _ in range(5)]


def choose_category(game_state) -> tuple[str, str, str]:
    """
    Välj bästa kategori enligt prioritetsordning.

    Returnerar (section, key, label_str):
      section = "upper" | "lower" | "stryk"
      key     = intern kategorinyckel (tom vid stryk)
      label   = läsbar text, t.ex. "Kåk  (25 p)"
    """
    p      = game_state.current_player
    dice   = game_state.dice_values
    ints   = [d for d in dice if isinstance(d, int)]
    counts = Counter(ints)

    # 1. Bonus-jakt
    if p.score_upper.bonus_progress > 0:
        for face in [6, 5, 4, 3, 2, 1]:
            if counts.get(face, 0) >= 2:
                key = _FACE_TO_KEY[face]
                if not p.score_upper.is_locked(key):
                    score = p.score_upper.calculate(key, dice)
                    if score > 0:
                        return ("upper", key,
                                f"{_FACE_TO_LABEL[face]}  ({score} p)")

    # 2. Starka kombinationer
    for key in _STRONG_LOWER_PRIORITY:
        if not p.score_lower.is_locked(key):
            score, valid = p.score_lower.calculate(key, dice)
            if valid and score > 0:
                return ("lower", key, f"{_LOWER_LABEL[key]}  ({score} p)")

    # 3. Övre sektion — välj med högst poäng
    best_key, best_score = None, 0
    for face in [6, 5, 4, 3, 2, 1]:
        key = _FACE_TO_KEY[face]
        if not p.score_upper.is_locked(key):
            score = p.score_upper.calculate(key, dice)
            if score > best_score:
                best_score, best_key = score, key
    if best_key and best_score > 0:
        face = next(f for k, _, f, _ in UPPER_CATEGORIES if k == best_key)
        return ("upper", best_key,
                f"{_FACE_TO_LABEL[face]}  ({best_score} p)")

    # 4. Chans
    if not p.score_lower.is_locked("chans"):
        score, valid = p.score_lower.calculate("chans", dice)
        if valid and score > 0:
            return ("lower", "chans", f"Chans  ({score} p)")

    # 5. Stryk
    return ("stryk", "", "Stryker")


def execute_choice(game_state, section: str, key: str) -> None:
    """Registrera botens val direkt i game_state."""
    p    = game_state.current_player
    dice = game_state.dice_values

    if section == "upper":
        p.score_upper.register(key, dice)

    elif section == "lower":
        p.score_lower.register(key, dice)

    elif section == "stryk":
        # Stryk första lediga nedre kategori
        for row in p.score_lower.rows(dice):
            if not row["locked"]:
                p.score_lower.strike(row["key"])
                return
        # Fallback: registrera första lediga övre med 0
        for row in p.score_upper.rows(dice):
            if not row["locked"]:
                p.score_upper.register(row["key"], dice)
                return

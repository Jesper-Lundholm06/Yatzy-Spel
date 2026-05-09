"""
bot_logic.py — Regelbaserad prioritets-bot för Yatzy.

PRIORITETSORDNING FÖR KATEGORIVAL:

  1. Bonus-jakt      — om bonus ej uppnådd, välj övre kategori med count >= 2
                        i ordning 6 → 5 → 4 → 3 → 2 → 1
  2. Starka komb.    — Yatzy → Kåk → Stor stege → Liten stege →
                        Fyrtal → Tretal → Två par → Par
  3. Övre sektion    — välj högsta poäng (även med count == 1)
  4. Chans           — sista alternativ med faktisk poäng
  5. Stryk / Fallback— om ingenting annat ger poäng

FAS-MASKIN PER BOT-TUR:

  Fas 1  Generera slumptärningar, visa dem 4.5 s (ingen popup).
  Fas 2  Öppna popup, vänta 0.8 s.
  Fas 3  Välj kategori, stäng popup, visa "BOT VALDE" 2.5 s.
  Fas 4  Anropa on_registered() → nästa spelare.

Boten läser ALDRIG från _live_values / YOLO.
"""

import time
import random
from collections import Counter

from yatzy_score import UPPER_CATEGORIES, LOWER_CATEGORIES

# ── Fördröjningar ─────────────────────────────────────────────────────────────
_BOT_ROLL_DISPLAY_DELAY:   float = 4.5   # visa tärningar
_BOT_PICK_DELAY:           float = 0.8   # vänta i popup
_BOT_CHOICE_DISPLAY_DELAY: float = 2.5   # visa vad som valdes

# ── Uppslagningstabeller (byggs en gång vid import) ───────────────────────────
_FACE_TO_KEY   = {face: key   for key, _lbl, face, _hk in UPPER_CATEGORIES}
_FACE_TO_LABEL = {face: label for _k,  label, face, _hk in UPPER_CATEGORIES}
_LOWER_LABEL   = {key: label  for key, label, _hk       in LOWER_CATEGORIES}

# Prioritetsordning för nedre sektion (Chans hanteras separat som sista utväg)
_STRONG_LOWER_PRIORITY = [
    "yatzy",
    "kok",
    "stor_stege",
    "liten_stege",
    "fyrtal",
    "tretal",
    "tva_par",
    "ett_par",
]

# ── Tillståndsvariabler ───────────────────────────────────────────────────────
_bot_dice:           list[int]      = []
_bot_rolling:        bool           = False   # Fas 1 → 2
_choice_made:        bool           = False   # Fas 3 → 4
_last_choice_label:  str            = ""      # visas i draw_bot_choice
_pending_registered                 = None    # sparad callback för Fas 4
_last_action:        float          = 0.0


# ── Publika funktioner ────────────────────────────────────────────────────────

def reset_timer() -> None:
    """Återställ all state — anropas när botens tur börjar."""
    global _last_action, _bot_rolling, _choice_made, _pending_registered
    _last_action        = time.time()
    _bot_rolling        = False
    _choice_made        = False
    _pending_registered = None


def is_bot_rolling() -> bool:
    """True medan tärningarna visas (Fas 1, ingen popup)."""
    return _bot_rolling


def is_bot_showing_choice() -> bool:
    """True direkt efter valet, under 'BOT VALDE'-bannern (Fas 4)."""
    return _choice_made


def get_choice_label() -> str:
    """Textetikett för det senaste kategorivalet, t.ex. 'Kåk  (25 p)'."""
    return _last_choice_label


def bot_act(game_state, on_registered) -> None:
    """
    Kör bot-logik en gång per frame.
    Gör ingenting om det inte är botens tur eller spelet är slut.
    Timing hanteras per fas.
    """
    if not game_state.current_player.is_bot:
        return
    if game_state.game_over:
        return
    _execute(game_state, on_registered)


# ── Intern fas-maskin ─────────────────────────────────────────────────────────

def _execute(game_state, on_registered) -> None:
    global _last_action, _bot_rolling, _choice_made, _pending_registered
    now = time.time()

    # ── Fas 1: Generera slumptärningar, visa dem (ingen popup) ───────────
    if not _bot_rolling and not _choice_made and \
       not game_state.show_score_menu and game_state.roll_count == 0:
        _bot_roll(game_state)
        _bot_rolling = True
        _last_action = now
        return

    # ── Fas 2: Tärningar visas → öppna popup efter 4.5 s ─────────────────
    if _bot_rolling:
        if now - _last_action >= _BOT_ROLL_DISPLAY_DELAY:
            _bot_rolling = False
            game_state.show_score_menu = True
            _last_action = now
        return  # vänta

    # ── Fas 3: Popup öppen → välj kategori efter 0.8 s ───────────────────
    if game_state.show_score_menu and not game_state.can_roll() and not _choice_made:
        if now - _last_action >= _BOT_PICK_DELAY:
            _pending_registered = on_registered
            _pick_and_store(game_state)          # väljer kategori, sätter _choice_made
            game_state.show_score_menu = False
            _last_action = now
        return  # vänta

    # ── Fas 4: Visa "BOT VALDE" → avancera efter 2.5 s ───────────────────
    if _choice_made:
        if now - _last_action >= _BOT_CHOICE_DISPLAY_DELAY:
            fn              = _pending_registered
            _choice_made    = False
            _pending_registered = None
            fn()             # → on_registered() → next_player()
        return


# ── Kast ──────────────────────────────────────────────────────────────────────

def _bot_roll(game_state) -> None:
    """
    Generera 5 slumptärningar (1–6) isolerat från kameran.
    Skriver direkt till dice_values — _live_values rörs ALDRIG.
    roll_count = MAX_ROLLS direkt (ett kast, ingen om-kastlogik).
    """
    global _bot_dice
    _bot_dice = [random.randint(1, 6) for _ in range(5)]
    game_state.dice_values = list(_bot_dice)
    game_state.roll_count  = game_state.MAX_ROLLS


# ── Kategorival ───────────────────────────────────────────────────────────────

def _pick_and_store(game_state) -> None:
    """Välj kategori och lagra läsbar etikett i _last_choice_label."""
    global _choice_made, _last_choice_label

    section, key, label = _choose_category(game_state)
    p    = game_state.current_player
    dice = game_state.dice_values

    if section == "upper":
        p.score_upper.register(key, dice)
        _last_choice_label = label
    elif section == "lower":
        p.score_lower.register(key, dice)
        _last_choice_label = label
    elif section == "stryk":
        # Stryk första lediga nedre kategori
        for row in p.score_lower.rows(dice):
            if not row["locked"]:
                p.score_lower.strike(row["key"])
                _last_choice_label = f"Stryker {row['label']}"
                break
        else:
            # Fallback: registrera första lediga övre med 0
            for row in p.score_upper.rows(dice):
                if not row["locked"]:
                    p.score_upper.register(row["key"], dice)
                    _last_choice_label = f"{row['label']}  (0 p)"
                    break

    _choice_made = True


def _choose_category(game_state) -> tuple[str, str, str]:
    """
    Välj kategori enligt prioritetsordning.

    Returnerar (section, key, label_str) där:
      section = "upper" | "lower" | "stryk"
      key     = intern kategorinyckel (tom vid stryk)
      label   = läsbar text, t.ex. "Kåk  (25 p)"
    """
    p      = game_state.current_player
    dice   = game_state.dice_values
    ints   = [d for d in dice if isinstance(d, int)]
    counts = Counter(ints)

    # ─────────────────────────────────────────────
    # 1. Bonus-jakt — prioritera övre sektionen
    #    Triggas om bonus ej uppnådd och minst 2 av samma sida finns
    # ─────────────────────────────────────────────
    if p.score_upper.bonus_progress > 0:
        for face in [6, 5, 4, 3, 2, 1]:
            if counts.get(face, 0) >= 2:
                key = _FACE_TO_KEY[face]
                if not p.score_upper.is_locked(key):
                    score = p.score_upper.calculate(key, dice)
                    if score > 0:
                        label = f"{_FACE_TO_LABEL[face]}  ({score} p)"
                        return ("upper", key, label)

    # ─────────────────────────────────────────────
    # 2. Starka kombinationer (Yatzy → Kåk → Stegor → ... → Par)
    #    Undvik chans tidigt — den hanteras i steg 4
    # ─────────────────────────────────────────────
    for key in _STRONG_LOWER_PRIORITY:
        if not p.score_lower.is_locked(key):
            score, valid = p.score_lower.calculate(key, dice)
            if valid and score > 0:
                label = f"{_LOWER_LABEL[key]}  ({score} p)"
                return ("lower", key, label)

    # ─────────────────────────────────────────────
    # 3. Övre sektion — välj högsta poäng oavsett count
    # ─────────────────────────────────────────────
    best_upper_key   = None
    best_upper_score = 0
    for face in [6, 5, 4, 3, 2, 1]:
        key = _FACE_TO_KEY[face]
        if not p.score_upper.is_locked(key):
            score = p.score_upper.calculate(key, dice)
            if score > best_upper_score:
                best_upper_score = score
                best_upper_key   = key
    if best_upper_key and best_upper_score > 0:
        label = f"{_FACE_TO_LABEL[_key_to_face(best_upper_key)]}  ({best_upper_score} p)"
        return ("upper", best_upper_key, label)

    # ─────────────────────────────────────────────
    # 4. Chans — sista alternativ med faktisk poäng
    # ─────────────────────────────────────────────
    if not p.score_lower.is_locked("chans"):
        score, valid = p.score_lower.calculate("chans", dice)
        if valid and score > 0:
            return ("lower", "chans", f"Chans  ({score} p)")

    # ─────────────────────────────────────────────
    # 5. Stryk / Fallback — inga poängalternativ finns
    # ─────────────────────────────────────────────
    return ("stryk", "", "")


def _key_to_face(key: str) -> int:
    """Hjälp: konvertera övre kategorinyckel → tärningsvärde."""
    for k, _lbl, face, _hk in UPPER_CATEGORIES:
        if k == key:
            return face
    return 1

"""
main.py — Entry point för Yatzy AI-systemet.

Ansvar:
    Startar och koordinerar hela applikationen.

Kommer att göra:
    - Initiera kameramodul, YOLO-modul och spelmotor vid uppstart.
    - Hålla igång huvudloopen som läser kameraframes och skickar dem vidare.
    - Koppla ihop alla moduler så att data flödar korrekt genom systemet.
    - Hantera applikationens livscykel (start, körning, avslut).

Ska INTE göra:
    - Innehålla spellogik.
    - Utföra bildanalys eller tärningsdetektering direkt.
    - Hantera poängberäkning.
    - Kommunicera med AI-motståndaren direkt.
"""

from camera_module import CameraModule
from yolo_module import YoloModule
from lock_zone import LockZone
from ui_overlay import UIOverlay
from game_state import GameState
from yatzy_score import YatzyScoreUpper, YatzyScoreLower, HOTKEY_MAP, LOWER_HOTKEY_MAP

yolo        = YoloModule()
lock_zone   = LockZone()
overlay     = UIOverlay()
game_state  = GameState()
score_upper = YatzyScoreUpper()
score_lower = YatzyScoreLower()


def _on_score_registered() -> None:
    """Anropas efter varje lyckad poängregistrering eller strykning."""
    grand = score_upper.upper_total + score_lower.total
    print(f"DEBUG TOTAL: upper={score_upper.upper_total}  lower={score_lower.total}  grand={grand}")
    if score_upper.is_complete() and score_lower.is_complete():
        game_state.game_over      = True
        game_state.show_score_menu = False
        game_state.stryk_mode     = False
    else:
        game_state.start_new_round()


def frame_callback(frame):
    frame_width = frame.shape[1]

    # 1. Detektera tärningar
    detections = yolo.detect_only(frame)

    # 2. Sortera vänster → höger på bbox x1 och extrahera värden
    detections_sorted = sorted(detections, key=lambda d: d["bbox"][0])
    live_values = [d["value"] for d in detections_sorted]
    live_values += ["-"] * (5 - len(live_values))
    live_values = live_values[:5]

    # 3. Uppdatera GameState med vad kameran ser just nu
    game_state.update_live(live_values)

    # 4. Låsstatus + ritning
    processed = lock_zone.process_detections(detections, frame_width)
    lock_zone.draw_zone(frame)
    lock_zone.draw_detections(frame, processed)

    # 5. Rita header + bottom-statusrad
    overlay.draw_ui(frame, game_state)

    # 6. Rita score-popup om den är aktiv
    if game_state.show_score_menu:
        overlay.draw_score_popup(frame, score_upper, score_lower,
                                 game_state.dice_values, game_state.stryk_mode)

    # 7. Resultatskärm ovanpå allt när spelet är slut
    if game_state.game_over:
        overlay.draw_game_over(frame, score_upper, score_lower)

    return frame


def key_callback(key: int) -> None:
    hotkey = chr(key) if 0 <= key <= 127 else ""

    # ── Game over-läge: enda tillåtna åtgärd är att starta om ──────────
    if game_state.game_over:
        if key == ord(" ") or hotkey == "r":
            score_upper.reset()
            score_lower.reset()
            game_state.game_over = False
            game_state.start_new_round()
        return

    # ── Normalt spelläge ────────────────────────────────────────────────
    if game_state.show_score_menu:
        # Stryk kräver att alla 3 kast är använda och minst en ledig kategori finns
        can_stryk = (
            game_state.roll_count >= GameState.MAX_ROLLS
            and any(not score_lower.is_locked(k) for k in LOWER_HOTKEY_MAP.values())
        )

        if hotkey == "s":
            if game_state.stryk_mode:
                game_state.stryk_mode = False
            elif can_stryk:
                game_state.stryk_mode = True

        elif game_state.stryk_mode and hotkey in LOWER_HOTKEY_MAP:
            if score_lower.strike(LOWER_HOTKEY_MAP[hotkey]):
                _on_score_registered()

        elif not game_state.stryk_mode and hotkey in HOTKEY_MAP:
            if score_upper.register(HOTKEY_MAP[hotkey], game_state.dice_values):
                _on_score_registered()

        elif not game_state.stryk_mode and hotkey in LOWER_HOTKEY_MAP:
            if score_lower.register(LOWER_HOTKEY_MAP[hotkey], game_state.dice_values):
                _on_score_registered()

        elif key == ord(" ") and game_state.can_roll():
            game_state.show_score_menu = False
            game_state.stryk_mode = False

    elif key == ord(" ") and game_state.can_roll():
        game_state.roll()
        game_state.show_score_menu = True


camera = CameraModule()
camera.set_frame_callback(frame_callback)
camera.set_key_callback(key_callback)
camera.start()

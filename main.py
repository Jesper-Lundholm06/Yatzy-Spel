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

    # 6. Rita score-popup ovanpå allt om den är aktiv
    if game_state.show_score_menu:
        overlay.draw_score_popup(frame, score_upper, score_lower, game_state.dice_values)

    return frame


def key_callback(key: int) -> None:
    hotkey = chr(key) if 0 <= key <= 127 else ""

    if game_state.show_score_menu:
        if hotkey in HOTKEY_MAP:
            # Övre sektion: tangent 1–6
            if score_upper.register(HOTKEY_MAP[hotkey], game_state.dice_values):
                game_state.start_new_round()
        elif hotkey in LOWER_HOTKEY_MAP:
            # Nedre sektion: tangent a–i
            if score_lower.register(LOWER_HOTKEY_MAP[hotkey], game_state.dice_values):
                game_state.start_new_round()
        elif key == ord(" ") and game_state.can_roll():
            # Stäng popup utan att välja (bara tillåtet om kast kvar)
            game_state.show_score_menu = False
    elif key == ord(" ") and game_state.can_roll():
        # Nytt kast → öppna popup
        game_state.roll()
        game_state.show_score_menu = True


camera = CameraModule()
camera.set_frame_callback(frame_callback)
camera.set_key_callback(key_callback)
camera.start()

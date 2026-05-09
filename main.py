"""
main.py — Entry point för Yatzy AI-systemet.

Ansvar:
    Startar startmenyn, skapar spelare och koordinerar hela applikationen.

Ska INTE göra:
    - Innehålla spellogik.
    - Utföra bildanalys eller tärningsdetektering direkt.
    - Hantera poängberäkning.
"""

from camera_module import CameraModule
from yolo_module import YoloModule
from lock_zone import LockZone
from ui_overlay import UIOverlay
from game_state import GameState
from player import Player
from start_menu import show_start_menu
from yatzy_score import HOTKEY_MAP, LOWER_HOTKEY_MAP
import bot_logic

# ── Startmeny ────────────────────────────────────────────────────────────────
num_players, has_bot = show_start_menu()

players = []
for i in range(num_players):
    is_last = (i == num_players - 1)
    if has_bot and is_last:
        players.append(Player("Bot", is_bot=True))
    else:
        players.append(Player(f"Spelare {i + 1}"))

# ── Initiera moduler ──────────────────────────────────────────────────────────
yolo       = YoloModule()
lock_zone  = LockZone()
overlay    = UIOverlay()
game_state = GameState(players)

# Starta bot-timern om första spelaren är en bot
if game_state.current_player.is_bot:
    bot_logic.reset_timer()


# ── Hjälpfunktion: körs efter varje lyckad poängregistrering/strykning ───────

def _on_score_registered() -> None:
    p     = game_state.current_player
    grand = p.score_upper.upper_total + p.score_lower.total
    print(f"DEBUG TOTAL: [{p.name}] upper={p.score_upper.upper_total}  "
          f"lower={p.score_lower.total}  grand={grand}")

    all_done = all(
        pl.score_upper.is_complete() and pl.score_lower.is_complete()
        for pl in game_state.players
    )
    if all_done:
        game_state.game_over      = True
        game_state.show_score_menu = False
        game_state.stryk_mode     = False
    else:
        game_state.next_player()
        # Starta bot-timern direkt när det blir botens tur
        if game_state.current_player.is_bot:
            bot_logic.reset_timer()


# ── Callbacks ─────────────────────────────────────────────────────────────────

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
        p = game_state.current_player
        overlay.draw_score_popup(frame, p.score_upper, p.score_lower,
                                 game_state.dice_values, game_state.stryk_mode)

    # 7. Resultatskärm ovanpå allt när spelet är slut
    if game_state.game_over:
        overlay.draw_game_over(frame, game_state.players)
        return frame

    # 8. Visa botens tärningar om den befinner sig i kastfasen
    if bot_logic.is_bot_rolling():
        overlay.draw_bot_rolling(frame, game_state.dice_values)

    # 8b. Visa vad boten valde (Fas 4 — 2.5 s efter val)
    if bot_logic.is_bot_showing_choice():
        overlay.draw_bot_choice(frame, bot_logic.get_choice_label())

    # 9. Bot-logik (agerar automatiskt om det är botens tur)
    bot_logic.bot_act(game_state, _on_score_registered)

    return frame


def key_callback(key: int) -> None:
    hotkey = chr(key) if 0 <= key <= 127 else ""

    # ── Game over-läge: enda tillåtna åtgärd är att starta om ───────────
    if game_state.game_over:
        if key == ord(" ") or hotkey == "r":
            for pl in game_state.players:
                pl.score_upper.reset()
                pl.score_lower.reset()
            game_state.current_player_index = 0
            game_state.game_over = False
            game_state.start_new_round()
            if game_state.current_player.is_bot:
                bot_logic.reset_timer()
        return

    # Blockera all tangentinput under botens tur
    if game_state.current_player.is_bot:
        return

    # ── Normalt spelläge ─────────────────────────────────────────────────
    p = game_state.current_player

    if game_state.show_score_menu:
        # Stryk kräver att alla 3 kast är använda och minst en ledig kategori finns
        can_stryk = (
            game_state.roll_count >= GameState.MAX_ROLLS
            and any(not p.score_lower.is_locked(k) for k in LOWER_HOTKEY_MAP.values())
        )

        if hotkey == "s":
            if game_state.stryk_mode:
                game_state.stryk_mode = False
            elif can_stryk:
                game_state.stryk_mode = True

        elif game_state.stryk_mode and hotkey in LOWER_HOTKEY_MAP:
            if p.score_lower.strike(LOWER_HOTKEY_MAP[hotkey]):
                _on_score_registered()

        elif not game_state.stryk_mode and hotkey in HOTKEY_MAP:
            if p.score_upper.register(HOTKEY_MAP[hotkey], game_state.dice_values):
                _on_score_registered()

        elif not game_state.stryk_mode and hotkey in LOWER_HOTKEY_MAP:
            if p.score_lower.register(LOWER_HOTKEY_MAP[hotkey], game_state.dice_values):
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

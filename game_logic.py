"""
game_logic.py — Trådsäker spellogik-wrapper för webbversionen.

Wrapprar GameState, Player och yatzy_score-klasserna med ett REST-vänligt
gränssnitt. Alla publika metoder returnerar en JSON-serialiserbar dict
(speltillståndet) som Flask-endpoints direkt kan returnera med jsonify().

Trådsäkerhet: threading.RLock (reentrant) används så att get_state() kan
anropas inuti andra metoder som redan håller låset.
"""

import threading
from game_state import GameState
from player import Player
import bot_logic_web as bot


class GameLogic:
    """Hanterar all spellogik och exponerar REST-vänliga metoder."""

    def __init__(self):
        self._lock = threading.RLock()
        self._gs: GameState | None = None
        self.setup(num_players=1, has_bot=True)

    # ── Setup & Restart ──────────────────────────────────────────────────────

    def setup(self, num_players: int, has_bot: bool) -> dict:
        """Skapa nytt spel med valt antal spelare och ev. bot."""
        with self._lock:
            players = [Player(f"Spelare {i + 1}") for i in range(num_players)]
            if has_bot:
                players.append(Player("Bot", is_bot=True))
            self._gs = GameState(players)
            return self.get_state()

    def restart(self) -> dict:
        """Återställ alla spelares poäng och starta om från runda 1."""
        with self._lock:
            for pl in self._gs.players:
                pl.score_upper.reset()
                pl.score_lower.reset()
            self._gs.current_player_index = 0
            self._gs.game_over = False
            self._gs.start_new_round()
            return self.get_state()

    # ── Spelaråtgärder ───────────────────────────────────────────────────────

    def roll(self, live_values: list) -> dict:
        """
        Kasta tärningar. Kopierar kamerans live-värden till dice_values
        för olåsta slots (precis som desktop-versionen).
        """
        with self._lock:
            if not self._gs.can_roll():
                return {**self.get_state(), "error": "Max antal kast uppnatt"}
            self._gs.update_live(live_values)
            self._gs.roll()
            return self.get_state()

    def toggle_lock(self, index: int) -> dict:
        """Toggla låsstatus för tärning i position 0–4."""
        with self._lock:
            if 0 <= index < 5 and self._gs.roll_count > 0:
                self._gs.locked_dice[index] = not self._gs.locked_dice[index]
            return self.get_state()

    def register(self, section: str, key: str) -> dict:
        """Registrera poäng för en kategori (section = 'upper' eller 'lower')."""
        with self._lock:
            p    = self._gs.current_player
            dice = self._gs.dice_values
            success = False

            if section == "upper":
                success = p.score_upper.register(key, dice)
            elif section == "lower":
                success = p.score_lower.register(key, dice)

            if success:
                self._on_score_registered()
            return self.get_state()

    def strike(self, key: str) -> dict:
        """Stryka en nedre kategori (0 poäng, permanent låst)."""
        with self._lock:
            if self._gs.current_player.score_lower.strike(key):
                self._on_score_registered()
            return self.get_state()

    def toggle_stryk(self) -> dict:
        """Aktivera/avbryta strykläge (kräver att alla 3 kast är gjorda)."""
        with self._lock:
            if self._gs.roll_count >= self._gs.MAX_ROLLS:
                self._gs.stryk_mode = not self._gs.stryk_mode
            return self.get_state()

    # ── Bot-tur ──────────────────────────────────────────────────────────────

    def bot_turn(self) -> dict:
        """
        Kör botens hela tur synkront:
          1. Generera slumptärningar
          2. Välj kategori enligt prioriteringsstrategi
          3. Registrera valet och gå vidare till nästa spelare

        Returnerar vanligt speltillstånd + extra fält:
          bot_dice         → list[int]  (botens tärningar, för animation)
          bot_choice_label → str        (t.ex. "Kåk  (25 p)", för animation)

        JavaScript-sidan hanterar timing (3s tärningsvisning + 2.5s val-visning).
        """
        with self._lock:
            gs = self._gs
            if not gs.current_player.is_bot:
                return {**self.get_state(), "error": "Inte botens tur"}

            # Generera tärningar (isolerat från kameran)
            dice = bot.roll_dice()
            gs.dice_values = list(dice)
            gs.roll_count  = gs.MAX_ROLLS

            # Välj och registrera kategori
            section, key, label = bot.choose_category(gs)
            bot.execute_choice(gs, section, key)

            self._on_score_registered()

            state = self.get_state()
            state["bot_dice"]         = dice
            state["bot_choice_label"] = label if label else "Stryker"
            return state

    # ── Speltillstånd (JSON-serialiserbart) ──────────────────────────────────

    def get_state(self) -> dict:
        """
        Returnera hela speltillståndet som en JSON-serialiserbar dict.

        Inkluderar:
          - Aktuell spelare (namn, is_bot, index)
          - Tärningsvärden och låsstatus
          - Kastantal och om kast är möjligt
          - Om spelet är slut och om strykläge är aktivt
          - Alla spelares poängrader (övre + nedre), summor och totaler
        """
        with self._lock:
            gs   = self._gs
            p    = gs.current_player
            dice = gs.dice_values

            players_data = []
            for i, pl in enumerate(gs.players):
                is_current = (i == gs.current_player_index)

                # Beräkna poängrader bara för aktiv spelare
                # (andra spelares olåsta rader är irrelevanta just nu)
                if is_current:
                    upper_rows = [
                        {
                            "key":    row["key"],
                            "label":  row["label"],
                            "score":  int(row["score"]),
                            "locked": row["locked"],
                            "hotkey": row["hotkey"],
                        }
                        for row in pl.score_upper.rows(dice)
                    ]
                    lower_rows = [
                        {
                            "key":    row["key"],
                            "label":  row["label"],
                            "score":  int(row["score"]),
                            "locked": row["locked"],
                            "hotkey": row["hotkey"],
                            "valid":  row.get("valid", True),
                            "struck": row.get("struck", False),
                        }
                        for row in pl.score_lower.rows(dice)
                    ]
                else:
                    upper_rows = []
                    lower_rows = []

                players_data.append({
                    "name":    pl.name,
                    "is_bot":  pl.is_bot,
                    "upper": {
                        "rows":          upper_rows,
                        "total":         pl.score_upper.total,
                        "bonus":         pl.score_upper.bonus,
                        "upper_total":   pl.score_upper.upper_total,
                        "bonus_progress": pl.score_upper.bonus_progress,
                    },
                    "lower": {
                        "rows":  lower_rows,
                        "total": pl.score_lower.total,
                    },
                    "grand_total": pl.score_upper.upper_total + pl.score_lower.total,
                })

            return {
                "current_player_index": gs.current_player_index,
                "current_player": {
                    "name":   p.name,
                    "is_bot": p.is_bot,
                },
                "dice_values":  [str(v) for v in dice],
                "locked_dice":  list(gs.locked_dice),
                "roll_count":   gs.roll_count,
                "can_roll":     gs.can_roll(),
                "max_rolls":    gs.MAX_ROLLS,
                "game_over":    gs.game_over,
                "stryk_mode":   gs.stryk_mode,
                "players":      players_data,
            }

    # ── Intern hjälp ────────────────────────────────────────────────────────

    def _on_score_registered(self) -> None:
        """Kolla om spelet är slut, annars gå vidare till nästa spelare."""
        gs = self._gs
        all_done = all(
            pl.score_upper.is_complete() and pl.score_lower.is_complete()
            for pl in gs.players
        )
        if all_done:
            gs.game_over = True
        else:
            gs.next_player()

"""
player.py — Representerar en spelare i Yatzy.

Ansvar:
    Hålla spelarens namn, bot-status och egna poängtavlor.

Denna modul innehåller INGEN spellogik eller renderingskod.
"""

from yatzy_score import YatzyScoreUpper, YatzyScoreLower


class Player:
    """En spelare med namn, bot-flagga och individuella poängtavlor."""

    def __init__(self, name: str, is_bot: bool = False):
        self.name        = name
        self.is_bot      = is_bot
        self.score_upper = YatzyScoreUpper()
        self.score_lower = YatzyScoreLower()

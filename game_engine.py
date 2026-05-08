"""
game_engine.py — Spelmotor och flödeskontroll för Yatzy-partiet.

Ansvar:
    Styra spelets gång, turrordning och regler enligt standard-Yatzy.

Kommer att göra:
    - Hålla reda på vilket drag i turen det är (kast 1, 2 eller 3).
    - Koordinera flödet mellan spelare och AI-motståndare.
    - Signalera när ett kast är klart och vilka värden som ska skickas till score_system.
    - Hantera spelomgångarnas livscykel från start till slut.

Ska INTE göra:
    - Beräkna poäng eller avgöra kategorier.
    - Utföra bildanalys.
    - Direkt hantera tärningarnas fysiska tillstånd.
    - Rendera grafik eller UI.
"""

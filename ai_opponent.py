"""
ai_opponent.py — AI-motståndare för Yatzy.

Ansvar:
    Simulera en AI-spelare som fattar strategiska beslut under partiet.

Kommer att göra:
    - Ta emot aktuellt tärningsläge och scorekort från game_engine.
    - Besluta vilka tärningar som ska låsas inför nästa kast.
    - Välja poängkategori vid kastets slut baserat på strategi.
    - Implementera olika svårighetsgrader (enkel, medel, avancerad).

Ska INTE göra:
    - Hantera kameradetektering eller bildanalys.
    - Direkt modifiera scorekort eller spelstatus.
    - Kontrollera spelflödets turordning.
    - Interagera med UI-komponenter.
"""

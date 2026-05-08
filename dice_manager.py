"""
dice_manager.py — Hantering av tärningarnas tillstånd och historik.

Ansvar:
    Spåra vilka tärningar som är aktiva, låsta eller kastade under ett drag.

Kommer att göra:
    - Ta emot detektionsresultat från yolo_module och uppdatera tärningarnas tillstånd.
    - Hålla reda på aktuella tärningsvärden (1–6) för upp till 5 tärningar.
    - Registrera vilka tärningar som är markerade som låsta av spelaren.
    - Exponera tärningarnas nuvarande tillstånd till spellogiken.

Ska INTE göra:
    - Detektera tärningar i bild.
    - Beräkna poäng.
    - Fatta beslut om vilka tärningar som bör låsas.
    - Kommunicera med kameran direkt.
"""

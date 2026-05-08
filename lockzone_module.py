"""
lockzone_module.py — Detektering och hantering av låszoner i kamerabild.

Ansvar:
    Avgöra om en tärning befinner sig inom en definierad låszon i bilden.

Kommer att göra:
    - Definiera och hantera koordinater för låszoner i kamerabilden.
    - Ta emot tärningspositioner från yolo_module och avgöra låsstatus.
    - Signalera till dice_manager vilka tärningar som ska anses låsta.
    - Stödja konfiguration av zonernas storlek och position.

Ska INTE göra:
    - Detektera tärningar direkt.
    - Hantera spellogik eller poäng.
    - Kommunicera med kameran.
"""

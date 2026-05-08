"""
popup_menu.py — Popup-meny och visuell overlay för spelinteraktion.

Ansvar:
    Visa interaktiva menyer och information ovanpå kamerabilden med OpenCV.

Kommer att göra:
    - Rendera poängkategorier som klickbara alternativ i en overlay.
    - Visa aktuellt spelläge, poängställning och turindikator.
    - Fånga upp musklick och tangentbordsinput för menyval.
    - Kommunicera spelarens val (vald kategori, låsning av tärningar) till game_engine.

Ska INTE göra:
    - Beräkna poäng eller spellogik.
    - Detektera tärningar eller zoner.
    - Hantera kameraströmmen.
"""

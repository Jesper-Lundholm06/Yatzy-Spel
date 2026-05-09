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

yolo      = YoloModule()
lock_zone = LockZone()
overlay   = UIOverlay()


def frame_callback(frame):
    frame_width = frame.shape[1]

    # 1. Detektera tärningar (ingen ritning ännu)
    detections = yolo.detect_only(frame)

    # 2. Sortera vänster → höger baserat på bbox x1
    detections_sorted = sorted(detections, key=lambda d: d["bbox"][0])

    # 3. Extrahera värden — fyll upp till 5 slots med "-"
    dice_values = [d["value"] for d in detections_sorted]
    dice_values += ["-"] * (5 - len(dice_values))
    dice_values = dice_values[:5]

    # 4. Avgör låsstatus per tärning (osorterade detektioner för korrekt bbox)
    processed = lock_zone.process_detections(detections, frame_width)

    # 5. Rita låszonen
    lock_zone.draw_zone(frame)

    # 6. Rita bounding boxes — grön om locked, gul om fri
    lock_zone.draw_detections(frame, processed)

    # 7. Rita fast toppmeny med tärningsvärden i läsordning (v→h)
    overlay.draw_dice_panel(frame, dice_values)

    return frame


camera = CameraModule()
camera.set_frame_callback(frame_callback)
camera.start()

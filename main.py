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

yolo      = YoloModule()
lock_zone = LockZone()


def frame_callback(frame):
    frame_width = frame.shape[1]

    # 1. Detektera tärningar (ingen ritning ännu)
    detections = yolo.detect_only(frame)

    # 2. Avgör låsstatus per tärning
    processed = lock_zone.process_detections(detections, frame_width)

    # 3. Rita låszonen
    lock_zone.draw_zone(frame)

    # 4. Rita bounding boxes — grön om locked, gul om fri
    lock_zone.draw_detections(frame, processed)

    return frame


camera = CameraModule()
camera.set_frame_callback(frame_callback)
camera.start()

"""
lock_zone.py — Visuell låszon för AI Yatzy.

Ansvar:
    Rita en transparent röd zon på högra 25% av kamerabild och avgöra
    vilka tärningar (baserat på bounding box-center) som befinner sig i zonen.

Denna modul hanterar ENDAST zonlogik och zonritning.
Den fattar inga spelbeslut och känner inte till kastregler.
"""

import cv2


class LockZone:
    """Hanterar låszonens position, visualisering och detektionsfiltrering."""

    ZONE_START_RATIO = 0.75     # zonen börjar vid 75% av bildbredden
    ZONE_ALPHA       = 0.25     # transparens för den röda fyllningen
    ZONE_COLOR       = (0, 0, 180)   # röd (BGR) — fyllning
    BORDER_COLOR     = (0, 0, 255)   # röd (BGR) — kantlinje och etikett

    COLOR_LOCKED   = (0, 255, 0)    # grön bounding box — tärning i zonen
    COLOR_FREE     = (0, 200, 255)  # gul bounding box — tärning utanför zonen

    FONT       = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 0.7
    THICKNESS  = 2

    def draw_zone(self, frame) -> None:
        """Rita transparent röd zon på högra 25% av frame. Modifierar frame in-place."""
        h, w = frame.shape[:2]
        zone_x = int(w * self.ZONE_START_RATIO)

        # Transparent fyllning via addWeighted
        overlay = frame.copy()
        cv2.rectangle(overlay, (zone_x, 0), (w, h), self.ZONE_COLOR, -1)
        cv2.addWeighted(overlay, self.ZONE_ALPHA, frame, 1 - self.ZONE_ALPHA, 0, frame)

        # Tydlig kantlinje
        cv2.line(frame, (zone_x, 0), (zone_x, h), self.BORDER_COLOR, 2)

        # Etikett överst i zonen
        cv2.putText(frame, "LOCK ZONE", (zone_x + 10, 38),
                    self.FONT, 0.9, self.BORDER_COLOR, 2)

    def process_detections(self, detections: list[dict], frame_width: int) -> list[dict]:
        """
        Kontrollera om varje tärnings bounding box-center befinner sig i låszonen.

        Args:
            detections:  lista från YoloModule.detect_only()
                         [{"value": int, "confidence": float, "bbox": (x1,y1,x2,y2)}, ...]
            frame_width: bildens bredd i pixlar

        Returnerar:
            [{"value": int, "bbox": (x1,y1,x2,y2), "locked": bool}, ...]
        """
        zone_x = frame_width * self.ZONE_START_RATIO
        result = []

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            center_x = (x1 + x2) / 2
            locked = center_x > zone_x

            result.append({
                "value":  det["value"],
                "bbox":   det["bbox"],
                "locked": locked,
            })

        return result

    def draw_detections(self, frame, processed: list[dict]) -> None:
        """
        Rita bounding boxes med färg baserat på låsstatus. Modifierar frame in-place.

        Grön  = locked (tärning i låszonen)
        Gul   = fri    (tärning utanför zonen)
        """
        for det in processed:
            x1, y1, x2, y2 = det["bbox"]
            color = self.COLOR_LOCKED if det["locked"] else self.COLOR_FREE

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, self.THICKNESS)

            label = f"{det['value']}  [LOCK]" if det["locked"] else str(det["value"])
            cv2.putText(frame, label, (x1, y1 - 8),
                        self.FONT, self.FONT_SCALE, color, self.THICKNESS)

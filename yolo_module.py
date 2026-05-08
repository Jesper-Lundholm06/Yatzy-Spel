"""
yolo_module.py — Tärningsdetektering med Ultralytics YOLOv8.

Ansvar:
    Ta emot kameraframes, köra YOLOv8-inferens och returnera annoterade frames
    med bounding boxes samt en lista med detekterade tärningsvärden.

Denna modul hanterar ENDAST detektering och annotering.
Den fattar inga spelbeslut och kommunicerar inte med spellogiken.

Modell:
    Förväntar sig en tränad YOLOv8-modell (best.pt) med 6 klasser där
    klass 0 = tärningsvärde 1, klass 1 = värde 2, ..., klass 5 = värde 6.
    Placera modellen i projektets rot eller ange sökväg vid instansiering.
"""

import cv2
import torch
from ultralytics import YOLO


class YoloModule:
    """Laddar YOLOv8-modell och kör realtidsdetektering på kameraframes."""

    # Bounding box-färg och textstil
    BOX_COLOR = (0, 255, 0)
    TEXT_COLOR = (0, 255, 0)
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 0.7
    THICKNESS = 2

    def __init__(self, model_path: str = "best.pt"):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"YOLO: laddar modell '{model_path}' på {device.upper()}.")

        self.model = YOLO(model_path)
        self.model.to(device)

        # Senaste detektioner — tillgängliga för framtida moduler
        self.last_detections: list[dict] = []

    def detect_only(self, frame) -> list[dict]:
        """
        Kör inferens utan att rita något. Uppdaterar self.last_detections.

        Returnerar:
            [{"value": int, "confidence": float, "bbox": (x1, y1, x2, y2)}, ...]
        """
        results = self.model(frame, verbose=False)[0]
        self.last_detections = []

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            cls = int(box.cls[0])
            dice_value = cls + 1

            self.last_detections.append({
                "value":      dice_value,
                "confidence": round(confidence, 2),
                "bbox":       (x1, y1, x2, y2),
            })

        return self.last_detections

    def process_frame(self, frame):
        """
        Kör inferens på frame, ritar bounding boxes och returnerar annoterat frame.

        Returnerar:
            frame — samma ndarray, annoterat med boxes och etiketter.

        Lagrar även resultaten i self.last_detections:
            [{"value": int, "confidence": float, "bbox": (x1, y1, x2, y2)}, ...]
        """
        results = self.model(frame, verbose=False)[0]
        self.last_detections = []

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            cls = int(box.cls[0])

            # Modellklasser 0–5 motsvarar tärningsvärden 1–6
            dice_value = cls + 1

            self.last_detections.append({
                "value": dice_value,
                "confidence": round(confidence, 2),
                "bbox": (x1, y1, x2, y2),
            })

            # Rita bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.BOX_COLOR, self.THICKNESS)

            # Etikett: tärningsvärde + konfidens
            label = f"{dice_value}  {confidence:.0%}"
            cv2.putText(frame, label, (x1, y1 - 8),
                        self.FONT, self.FONT_SCALE, self.TEXT_COLOR, self.THICKNESS)

        return frame

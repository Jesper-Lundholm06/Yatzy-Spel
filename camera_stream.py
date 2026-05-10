"""
camera_stream.py — Trådsäker kameraström med YOLO-overlay för webbversionen.

En bakgrundstråd läser frames kontinuerligt, kör YOLO-detektering och
sparar senaste JPEG-frame + detekterade tärningsvärden i minnet.

Flask-endpoint /video_feed anropar generate_frames() som är en generator
som levererar MJPEG-stream (multipart/x-mixed-replace) till webbläsaren.
Flask-endpoint /api/roll anropar get_live_values() för att läsa kamerans
aktuella tärningsvärden när spelaren kastar.
"""

import threading
import time
import cv2

from yolo_module import YoloModule
from lock_zone import LockZone


class CameraStream:
    """
    Hanterar kameraström i en bakgrundstråd.

    Exponerar:
      get_live_values() → list[int | str]  (senaste YOLO-detektioner)
      generate_frames() → generator        (MJPEG-bytes för /video_feed)
    """

    JPEG_QUALITY = 75

    def __init__(self, camera_index: int = 1):
        self._lock        = threading.Lock()
        self._frame_bytes = None          # senaste JPEG-frame (bytes)
        self._live_values = ["-"] * 5    # senaste tärningsvärden från kameran

        self._cap       = cv2.VideoCapture(camera_index)
        self._yolo      = YoloModule()
        self._lock_zone = LockZone()

        if not self._cap.isOpened():
            print(f"VARNING: Kamera (index {camera_index}) kunde inte öppnas. "
                  "Kameraflödet visas som tomt i webbläsaren.")

        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    # ── Publik API ───────────────────────────────────────────────────────────

    def get_live_values(self) -> list:
        """Returnerar senaste kamerans tärningsvärden (trådsäkert)."""
        with self._lock:
            return list(self._live_values)

    def generate_frames(self):
        """
        Generator för MJPEG-stream.

        Skickar senaste frame var 33ms (~30 FPS).
        Används av Flask: Response(stream.generate_frames(), mimetype=...)
        """
        while True:
            with self._lock:
                frame = self._frame_bytes

            if frame is not None:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n"
                       + frame +
                       b"\r\n")
            time.sleep(0.033)

    # ── Bakgrundstråd ────────────────────────────────────────────────────────

    def _update_loop(self) -> None:
        """Körs i bakgrundstråd: läser kamera, kör YOLO, sparar frame."""
        while True:
            if not self._cap.isOpened():
                time.sleep(0.1)
                continue

            success, frame = self._cap.read()
            if not success:
                time.sleep(0.033)
                continue

            # Brusreducering (förbättrar YOLO)
            frame = cv2.GaussianBlur(frame, (3, 3), 0)

            # YOLO-detektering
            detections = self._yolo.detect_only(frame)
            detections_sorted = sorted(detections, key=lambda d: d["bbox"][0])
            live_values = [d["value"] for d in detections_sorted]
            live_values += ["-"] * (5 - len(live_values))
            live_values = live_values[:5]

            # Rita låszon och bounding boxes på frame
            self._lock_zone.draw_zone(frame)
            processed = self._lock_zone.process_detections(detections, frame.shape[1])
            self._lock_zone.draw_detections(frame, processed)

            # Koda till JPEG
            _, buffer = cv2.imencode(
                ".jpg", frame,
                [cv2.IMWRITE_JPEG_QUALITY, self.JPEG_QUALITY]
            )

            with self._lock:
                self._frame_bytes = buffer.tobytes()
                self._live_values = live_values

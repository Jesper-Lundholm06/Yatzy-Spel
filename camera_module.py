"""
camera_module.py — Kamerahantering via OpenCV.

Ansvar:
    Öppna en USB-kamera, läsa frames robust och visa dem i ett fullskärmsfönster.

Denna modul hanterar ENDAST kameravisning och frame-distribution.
Den utför ingen bildanalys, detektering eller spellogik.
"""

import sys
import cv2


class CameraModule:
    """Hanterar uppkoppling, konfiguration, visning och stängning av kameraströmmen."""

    WINDOW_TITLE  = "AI Yatzy - Camera Feed"
    WARMUP_FRAMES = 20
    MAX_READ_FAILURES = 5

    def __init__(self, camera_index: int = 1):
        self._frame_callback = None
        self._key_callback   = None
        self._mouse_callback = None
        self.capture = self._open_camera(camera_index)

    # ------------------------------------------------------------------
    # Uppstart
    # ------------------------------------------------------------------

    def _open_camera(self, camera_index: int):
        """Öppnar kameran med default backend — inga extra krav."""

        # Bekräftat fungerande för Deltaco-kameran: VideoCapture utan backend-flagga.
        # CAP_DSHOW + FOURCC + FPS-tvingning orsakar svart bild på denna kamera.
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            actual_w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"Kamera öppnad: {actual_w}x{actual_h} @ {actual_fps:.1f} FPS")
            return cap

        print(f"FEL: Kunde inte öppna kamera (index {camera_index}).")
        print("Kontrollera att USB-kameran är ansluten och inte används av annat program.")
        sys.exit(1)

    def _warmup(self):
        """Kastar bort de första frames för att stabilisera exponering och buffertar."""
        print(f"Kamera: warm-up ({self.WARMUP_FRAMES} frames)...")
        for _ in range(self.WARMUP_FRAMES):
            self.capture.grab()
        print("Kamera: redo.")

    # ------------------------------------------------------------------
    # Callback
    # ------------------------------------------------------------------

    def set_frame_callback(self, callback):
        """
        Registrerar en callback som anropas på varje frame innan visning.

        Callback-signatur: callback(frame: ndarray) -> ndarray
        Det returnerade frame visas i fönstret.
        """
        self._frame_callback = callback

    def set_key_callback(self, callback):
        """
        Registrerar en callback för tangenttryckningar (utom 'q').

        Callback-signatur: callback(key: int) -> None
        key är ASCII-värdet av den tangent som trycktes.
        """
        self._key_callback = callback

    def set_mouse_callback(self, callback):
        """
        Registrerar en callback för musklick (vänster knapp).

        Callback-signatur: callback(x: int, y: int) -> None
        """
        self._mouse_callback = callback

    # ------------------------------------------------------------------
    # Huvudloop
    # ------------------------------------------------------------------

    def start(self):
        """Startar live-feed-loopen. Avslutas när användaren trycker 'q'."""

        self._warmup()
        print("Kamera startad. Tryck 'q' för att avsluta.")

        # Skapa fönster och sätt fullskärm innan loopen startar
        cv2.namedWindow(self.WINDOW_TITLE, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.WINDOW_TITLE, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setMouseCallback(self.WINDOW_TITLE, self._on_mouse)

        consecutive_failures = 0

        while True:
            success, frame = self.capture.read()

            if not success:
                consecutive_failures += 1
                print(f"VARNING: Kunde inte läsa frame "
                      f"({consecutive_failures}/{self.MAX_READ_FAILURES}).")
                if consecutive_failures >= self.MAX_READ_FAILURES:
                    print("FEL: För många läsfel i rad. Avslutar.")
                    break
                continue

            consecutive_failures = 0

            # Lätt brusreducering — förbättrar YOLO-detektering utan märkbar suddighet
            frame = cv2.GaussianBlur(frame, (3, 3), 0)

            # Om en callback är registrerad — låt den bearbeta frame (t.ex. YOLO)
            if self._frame_callback is not None:
                frame = self._frame_callback(frame)

            cv2.imshow(self.WINDOW_TITLE, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key != 255 and self._key_callback is not None:
                self._key_callback(key)

        self._release()

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and self._mouse_callback is not None:
            self._mouse_callback(x, y)

    # ------------------------------------------------------------------
    # Avslut
    # ------------------------------------------------------------------

    def _release(self):
        """Frigör kameran och stänger alla OpenCV-fönster."""
        self.capture.release()
        cv2.destroyAllWindows()

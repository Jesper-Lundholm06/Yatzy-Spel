"""
ui_overlay.py — Visuell overlay-panel för AI Yatzy.

Ansvar:
    Rita informationspaneler direkt på kameraframen med OpenCV.

Denna modul hanterar ENDAST rendering.
Den fattar inga spelbeslut och kommunicerar inte med spellogiken.
"""

import cv2


class UIOverlay:
    """Renderar overlay-paneler ovanpå kameraframen."""

    PANEL_HEIGHT = 80
    BG_COLOR     = (30, 30, 30)
    TEXT_COLOR   = (255, 255, 255)
    FONT         = cv2.FONT_HERSHEY_SIMPLEX

    def draw_dice_panel(self, frame, dice_values: list) -> None:
        """
        Rita fast toppmeny med 5 slots ordnade vänster till höger.

        Args:
            frame:       OpenCV-frame (modifieras in-place).
            dice_values: lista med exakt 5 element — int (tärningsvärde) eller "-".
        """
        w = frame.shape[1]

        cv2.rectangle(frame, (0, 0), (w, self.PANEL_HEIGHT), self.BG_COLOR, -1)
        cv2.line(frame, (0, self.PANEL_HEIGHT), (w, self.PANEL_HEIGHT), (70, 70, 70), 1)

        slot_w = w // 5
        for i, value in enumerate(dice_values):
            text = f"T{i + 1}: {value}"
            x = slot_w * i + slot_w // 6
            cv2.putText(frame, text, (x, 52),
                        self.FONT, 0.9, self.TEXT_COLOR, 2, cv2.LINE_AA)

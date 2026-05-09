"""
ui_overlay.py — Visuell overlay för AI Yatzy.

Ansvar:
    Rita header-bar med tärningsboxar och bottom-statusrad på kameraframen.

Denna modul hanterar ENDAST rendering.
Den fattar inga spelbeslut och kommunicerar inte med spellogiken.
"""

import cv2


class UIOverlay:
    """Renderar header och statusrad ovanpå kameraframen."""

    FONT = cv2.FONT_HERSHEY_SIMPLEX

    # Header (toppen)
    HEADER_H     = 100
    HEADER_BG    = (20, 20, 20)
    BOX_FREE     = (55, 55, 55)
    BOX_LOCKED   = (140, 100, 0)    # tonad gul — används när tärning är låst
    BOX_BORDER   = (90, 90, 90)
    LABEL_COLOR  = (150, 150, 150)  # "T1" — liten grå text
    VALUE_COLOR  = (255, 255, 255)  # tärningsvärde — stor vit text

    # Bottom-statusrad
    BOTTOM_H     = 80
    BOTTOM_ALPHA = 0.70             # transparens på bakgrundsoverlayen

    # Färger för kaststatustext
    COLOR_CAN_ROLL  = (60, 220, 60)   # grön — kast kvar
    COLOR_DONE      = (50, 60, 240)   # röd — 3/3 uppnått
    COLOR_STATUS    = (210, 210, 210) # grå — instruktionstext

    # ------------------------------------------------------------------
    # Publik metod
    # ------------------------------------------------------------------

    def draw_ui(self, frame, game_state) -> None:
        """
        Ritar hela UI-overlayern på frame (in-place).

        Anropas en gång per frame med aktuellt GameState.
        """
        self._draw_header(frame, game_state.dice_values, game_state.locked_dice)
        self._draw_bottom(frame, game_state.roll_count, game_state.can_roll())

    # ------------------------------------------------------------------
    # Header — 5 tärningsboxar
    # ------------------------------------------------------------------

    def _draw_header(self, frame, dice_values: list, locked_dice: list) -> None:
        w = frame.shape[1]

        # Bakgrundsfält
        cv2.rectangle(frame, (0, 0), (w, self.HEADER_H), self.HEADER_BG, -1)
        cv2.line(frame, (0, self.HEADER_H), (w, self.HEADER_H), (60, 60, 60), 1)

        # Geometri: boxar centrerade horisontellt
        box_w   = int(w * 0.13)          # 13% av bildbredden per box
        box_h   = 82
        gap     = int(w * 0.025)         # 2.5% mellanrum
        total_w = 5 * box_w + 4 * gap
        start_x = (w - total_w) // 2
        box_y   = (self.HEADER_H - box_h) // 2

        for i in range(5):
            box_x  = start_x + i * (box_w + gap)
            locked = locked_dice[i]
            bg     = self.BOX_LOCKED if locked else self.BOX_FREE

            # Fyllning + kantlinje
            cv2.rectangle(frame,
                          (box_x, box_y),
                          (box_x + box_w, box_y + box_h),
                          bg, -1)
            cv2.rectangle(frame,
                          (box_x, box_y),
                          (box_x + box_w, box_y + box_h),
                          self.BOX_BORDER, 1)

            # Etikett "T1" — liten text, övre halvan av boxen
            label = f"T{i + 1}"
            (lw, _), _ = cv2.getTextSize(label, self.FONT, 0.52, 1)
            lx = box_x + (box_w - lw) // 2
            ly = box_y + 24
            cv2.putText(frame, label, (lx, ly),
                        self.FONT, 0.52, self.LABEL_COLOR, 1, cv2.LINE_AA)

            # Värde — stor text, undre halvan av boxen
            value = str(dice_values[i])
            (vw, _), _ = cv2.getTextSize(value, self.FONT, 1.5, 2)
            vx = box_x + (box_w - vw) // 2
            vy = box_y + box_h - 12
            cv2.putText(frame, value, (vx, vy),
                        self.FONT, 1.5, self.VALUE_COLOR, 2, cv2.LINE_AA)

    # ------------------------------------------------------------------
    # Bottom-statusrad
    # ------------------------------------------------------------------

    def _draw_bottom(self, frame, roll_count: int, can_roll: bool) -> None:
        h, w = frame.shape[:2]
        bar_y = h - self.BOTTOM_H

        # Halvtransparent bakgrundsoverlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, bar_y), (w, h), (15, 15, 15), -1)
        cv2.addWeighted(overlay, self.BOTTOM_ALPHA,
                        frame,   1 - self.BOTTOM_ALPHA, 0, frame)
        cv2.line(frame, (0, bar_y), (w, bar_y), (60, 60, 60), 1)

        # Rad 1: "KAST 2 / 3" (visas efter första kastet)
        if roll_count > 0:
            roll_text  = f"KAST  {roll_count} / 3"
            roll_color = self.COLOR_CAN_ROLL if can_roll else self.COLOR_DONE
            self._put_centered(frame, roll_text, w,
                               bar_y + 30, 0.95, roll_color, 2)

        # Rad 2: instruktionstext
        if roll_count == 0:
            status = "Tryck SPACE for att kasta"
            # Centrera vertikalt i baren om det är enda raden
            self._put_centered(frame, status, w,
                               bar_y + self.BOTTOM_H // 2 + 10, 0.8, self.COLOR_STATUS, 2)
        elif can_roll:
            self._put_centered(frame, "Nytt kast: Tryck SPACE", w,
                               h - 14, 0.75, self.COLOR_STATUS, 2)
        else:
            self._put_centered(frame, "Valj poangkategori", w,
                               h - 14, 0.75, self.COLOR_STATUS, 2)

    # ------------------------------------------------------------------
    # Score-popup
    # ------------------------------------------------------------------

    def draw_score_popup(self, frame, score_upper, score_lower, dice_values: list) -> None:
        """
        Rita score-popup med övre och nedre sektionen.

        Renderas ovanpå allt annat. Radhöjd beräknas proportionellt mot
        popup-höjden så att layouten fungerar vid alla upplösningar.

        Args:
            frame:       OpenCV-frame (in-place).
            score_upper: YatzyScoreUpper-instans.
            score_lower: YatzyScoreLower-instans.
            dice_values: Aktuella tärningsvärden från GameState.
        """
        h, w = frame.shape[:2]

        # Dimma bakgrunden
        dim = frame.copy()
        cv2.rectangle(dim, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(dim, 0.55, frame, 0.45, 0, frame)

        # Popup-ruta: 52% bredd, 91% höjd
        box_w = int(w * 0.52)
        box_h = int(h * 0.91)
        bx    = (w - box_w) // 2
        by    = (h - box_h) // 2

        cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), (28, 28, 28), -1)
        cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), (110, 110, 110), 2)

        pad_l = bx + 18
        pad_r = bx + box_w - 18

        # Radhöjd: box_h - fast utrymme delat på 20 rader (6 övre + 9 nedre + 5 total-rader)
        row_h = max(22, (box_h - 165) // 20)
        y     = by + 26

        # ── ÖVRE SEKTION ─────────────────────────────────────────────
        self._put_centered(frame, "OVRE SEKTION", w, y, 0.72, (255, 255, 255), 2)
        y += 12
        cv2.line(frame, (pad_l, y), (pad_r, y), (75, 75, 75), 1)
        y += row_h - 4

        for row in score_upper.rows(dice_values):
            self._draw_score_row(frame, row, pad_l, pad_r, y, row_h)
            y += row_h

        # Övre summor
        y += 4
        cv2.line(frame, (pad_l, y), (pad_r, y), (70, 70, 70), 1)
        y += row_h - 6

        cv2.putText(frame, f"Summa:  {score_upper.total}", (pad_l, y),
                    self.FONT, 0.58, (200, 200, 200), 1, cv2.LINE_AA)
        y += row_h - 4

        bonus_col = (70, 210, 70) if score_upper.bonus > 0 else (120, 120, 120)
        bonus_txt = f"Bonus:  {score_upper.bonus}"
        cv2.putText(frame, bonus_txt, (pad_l, y),
                    self.FONT, 0.58, bonus_col, 1, cv2.LINE_AA)
        if score_upper.bonus_progress > 0:
            prog = f"({score_upper.bonus_progress} kvar)"
            (pw, _), _ = cv2.getTextSize(prog, self.FONT, 0.46, 1)
            cv2.putText(frame, prog, (pad_r - pw, y),
                        self.FONT, 0.46, (105, 105, 105), 1, cv2.LINE_AA)
        y += row_h - 4

        cv2.putText(frame, f"Ovre total:  {score_upper.upper_total}", (pad_l, y),
                    self.FONT, 0.62, (255, 210, 60), 2, cv2.LINE_AA)
        y += row_h

        # ── NEDRE SEKTION ─────────────────────────────────────────────
        cv2.line(frame, (pad_l, y), (pad_r, y), (75, 75, 75), 1)
        y += 10
        self._put_centered(frame, "NEDRE SEKTION", w, y, 0.72, (255, 255, 255), 2)
        y += 12
        cv2.line(frame, (pad_l, y), (pad_r, y), (75, 75, 75), 1)
        y += row_h - 4

        for row in score_lower.rows(dice_values):
            self._draw_score_row(frame, row, pad_l, pad_r, y, row_h)
            y += row_h

        # Nedre summor
        y += 4
        cv2.line(frame, (pad_l, y), (pad_r, y), (70, 70, 70), 1)
        y += row_h - 6

        cv2.putText(frame, f"Nedre total:  {score_lower.total}", (pad_l, y),
                    self.FONT, 0.62, (255, 210, 60), 2, cv2.LINE_AA)
        y += row_h

        # ── GRAND TOTAL ───────────────────────────────────────────────
        cv2.line(frame, (pad_l, y), (pad_r, y), (100, 100, 100), 1)
        y += row_h - 6
        grand = score_upper.upper_total + score_lower.total
        self._put_centered(frame, f"TOTALT:  {grand}", w, y, 0.80, (255, 255, 255), 2)

        # ── Instruktion ───────────────────────────────────────────────
        instr_y = by + box_h - 14
        cv2.line(frame, (pad_l, instr_y - 20), (pad_r, instr_y - 20), (60, 60, 60), 1)
        self._put_centered(frame, "1-6 / a-i = valj kategori  |  SPACE = kasta igen", w,
                           instr_y, 0.46, (145, 145, 145), 1)

    def _draw_score_row(self, frame, row: dict,
                        pad_l: int, pad_r: int, y: int, row_h: int) -> None:
        """
        Rita en kategorirad i score-popup.

        Tre tillstånd:
          locked  → grå text + [VALD]
          ej valid → grå text, ingen tangent, score "0"
          valbar  → vit label, grön score (eller grå om 0)
        """
        locked = row["locked"]
        valid  = row.get("valid", True)

        if locked:
            label_col = (85, 85, 85)
            score_col = (85, 85, 85)
            label_txt = f"  {row['label']}  [VALD]"
            score_txt = str(row["score"])
        elif not valid:
            label_col = (80, 80, 80)
            score_col = (80, 80, 80)
            label_txt = f"    {row['label']}"
            score_txt = "0"
        else:
            label_col = (215, 215, 215)
            score_col = (70, 210, 70) if row["score"] > 0 else (125, 125, 125)
            label_txt = f"[{row['hotkey']}] {row['label']}"
            score_txt = f"+{row['score']}"

        scale = 0.58
        cv2.putText(frame, label_txt, (pad_l, y),
                    self.FONT, scale, label_col, 1, cv2.LINE_AA)
        (sw, _), _ = cv2.getTextSize(score_txt, self.FONT, scale, 1)
        cv2.putText(frame, score_txt, (pad_r - sw, y),
                    self.FONT, scale, score_col, 1, cv2.LINE_AA)

    # ------------------------------------------------------------------
    # Hjälpmetod: centrera text horisontellt
    # ------------------------------------------------------------------

    @staticmethod
    def _put_centered(frame, text: str, frame_w: int,
                      y: int, scale: float, color: tuple, thickness: int) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, _), _ = cv2.getTextSize(text, font, scale, thickness)
        x = (frame_w - tw) // 2
        cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)

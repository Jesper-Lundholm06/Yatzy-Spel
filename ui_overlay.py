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
    HEADER_H     = 120   # 20 extra px för spelarnamnsrad längst upp
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
        p = game_state.current_player
        self._draw_header(frame, game_state.dice_values, game_state.locked_dice,
                          p.name, p.is_bot)
        self._draw_bottom(frame, game_state.roll_count, game_state.can_roll())

    # ------------------------------------------------------------------
    # Header — 5 tärningsboxar
    # ------------------------------------------------------------------

    def _draw_header(self, frame, dice_values: list, locked_dice: list,
                     player_name: str = "", is_bot: bool = False) -> None:
        w = frame.shape[1]

        # Bakgrundsfält
        cv2.rectangle(frame, (0, 0), (w, self.HEADER_H), self.HEADER_BG, -1)
        cv2.line(frame, (0, self.HEADER_H), (w, self.HEADER_H), (60, 60, 60), 1)

        # Spelarnamnsrad (översta 20 px av headern)
        if player_name:
            prefix     = "BOT" if is_bot else "TUR"
            name_col   = (100, 200, 100) if not is_bot else (100, 180, 230)
            prefix_col = (130, 130, 130)
            prefix_txt = f"{prefix}:"
            name_txt   = f"  {player_name}"
            (pw, _), _ = cv2.getTextSize(prefix_txt + name_txt, self.FONT, 0.52, 1)
            cx = (w - pw) // 2
            cv2.putText(frame, prefix_txt, (cx, 14),
                        self.FONT, 0.52, prefix_col, 1, cv2.LINE_AA)
            (pw2, _), _ = cv2.getTextSize(prefix_txt, self.FONT, 0.52, 1)
            cv2.putText(frame, name_txt, (cx + pw2, 14),
                        self.FONT, 0.52, name_col, 1, cv2.LINE_AA)
        cv2.line(frame, (0, 20), (w, 20), (45, 45, 45), 1)

        # Geometri: boxar centrerade i resterande utrymme (y=20 → HEADER_H)
        box_w   = int(w * 0.13)
        box_h   = 82
        gap     = int(w * 0.025)
        total_w = 5 * box_w + 4 * gap
        start_x = (w - total_w) // 2
        avail_h = self.HEADER_H - 20
        box_y   = 20 + (avail_h - box_h) // 2

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

    def draw_score_popup(self, frame, score_upper, score_lower,
                         dice_values: list, stryk_mode: bool = False) -> None:
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

        border_col = (40, 40, 200) if stryk_mode else (110, 110, 110)   # röd kant i strykläge
        cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), (28, 28, 28), -1)
        cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), border_col, 2)

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
            self._draw_score_row(frame, row, pad_l, pad_r, y, row_h, stryk_mode)
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
        if stryk_mode:
            instr_txt = "STRYK AKTIV  —  [a-i] valj kategori att stryka  |  [s] avbryt"
            instr_col = (80, 80, 210)
        else:
            instr_txt = "1-6 / a-i = valj kategori  |  [s] Stryk  |  SPACE = kasta igen"
            instr_col = (145, 145, 145)
        self._put_centered(frame, instr_txt, w, instr_y, 0.46, instr_col, 1)

    # ------------------------------------------------------------------
    # Bot-kastvisning
    # ------------------------------------------------------------------

    def draw_bot_rolling(self, frame, dice_values: list) -> None:
        """
        Visa botens slumpade tärningar tydligt i mitten av skärmen.

        Renderas medan _bot_rolling == True (innan popup öppnas).
        Påverkar inte kamerans värden eller spelarens dice.
        """
        h, w = frame.shape[:2]

        banner_h = 108
        banner_w = int(w * 0.58)
        bx       = (w - banner_w) // 2
        by       = int(h * 0.40)

        # Halvtransparent mörk ruta
        overlay = frame.copy()
        cv2.rectangle(overlay, (bx, by), (bx + banner_w, by + banner_h), (16, 16, 16), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
        cv2.rectangle(frame, (bx, by), (bx + banner_w, by + banner_h), (80, 200, 80), 2)

        # Rubrik
        self._put_centered(frame, "BOT KASTAR", w, by + 36,
                           0.82, (80, 210, 80), 2)

        # Tärningsvärden: [3]  [5]  [1]  [6]  [2]
        dice_str = "   ".join(f"[{v}]" for v in dice_values)
        self._put_centered(frame, dice_str, w, by + 82,
                           0.82, (230, 230, 230), 2)

    def draw_bot_choice(self, frame, label: str) -> None:
        """
        Visa vad boten valde under Fas 4 (BOT VALDE-bannern).

        Renderas medan _choice_made == True, i 2.5 s innan nästa tur börjar.
        """
        h, w = frame.shape[:2]

        banner_h = 90
        banner_w = int(w * 0.55)
        bx       = (w - banner_w) // 2
        by       = int(h * 0.40)

        overlay = frame.copy()
        cv2.rectangle(overlay, (bx, by), (bx + banner_w, by + banner_h), (16, 16, 16), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
        cv2.rectangle(frame, (bx, by), (bx + banner_w, by + banner_h), (0, 215, 255), 2)

        self._put_centered(frame, "BOT VALDE:", w, by + 32, 0.72, (130, 130, 130), 1)
        self._put_centered(frame, label,        w, by + 68, 0.82, (0, 215, 255),   2)

    # ------------------------------------------------------------------
    # Resultatskärm (game over)
    # ------------------------------------------------------------------

    def draw_game_over(self, frame, players: list) -> None:
        """
        Rita final-overlay med alla spelares poäng och vinnaren markerad.

        Anpassar boxhöjden automatiskt till antal spelare (1–4).
        Renderas ovanpå allt annat.
        """
        h, w = frame.shape[:2]

        # Kraftig dimning
        dim = frame.copy()
        cv2.rectangle(dim, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(dim, 0.74, frame, 0.26, 0, frame)

        # Beräkna grand totals och identifiera vinnaren
        totals     = [pl.score_upper.upper_total + pl.score_lower.total for pl in players]
        winner_idx = totals.index(max(totals))

        # Boxstorlek anpassad till antal spelare
        player_row_h = 36
        inner_h      = 80 + len(players) * player_row_h + 70
        box_h        = max(inner_h, int(h * 0.42))
        box_w        = int(w * 0.62)
        bx           = (w - box_w) // 2
        by           = (h - box_h) // 2

        cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), (22, 22, 22), -1)
        cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), (0, 215, 255), 2)  # guldbård

        pad_l = bx + 22
        pad_r = bx + box_w - 22
        y     = by + 40

        # Titel
        self._put_centered(frame, "SPELET AR SLUT", w, y, 0.88, (255, 255, 255), 2)
        y += 22
        cv2.line(frame, (pad_l, y), (pad_r, y), (80, 80, 80), 1)
        y += 14

        # Kolumnrubriker (Spelare | Övre | Nedre | Totalt)
        col_name  = pad_l
        col_ovre  = pad_l + int(box_w * 0.38)
        col_nedre = pad_l + int(box_w * 0.54)
        col_tot   = pad_l + int(box_w * 0.70)
        hdr_col   = (95, 95, 95)

        for txt, cx in [("Spelare", col_name), ("Ovre",  col_ovre),
                        ("Nedre",  col_nedre),  ("Totalt", col_tot)]:
            cv2.putText(frame, txt, (cx, y), self.FONT, 0.50, hdr_col, 1, cv2.LINE_AA)
        y += 6
        cv2.line(frame, (pad_l, y), (pad_r, y), (55, 55, 55), 1)
        y += player_row_h - 8

        # En rad per spelare
        for i, pl in enumerate(players):
            is_winner = (i == winner_idx)
            # Guld för vinnaren, grå för övriga
            name_col = (0, 215, 255) if is_winner else (190, 190, 190)
            val_col  = (0, 215, 255) if is_winner else (150, 150, 150)
            name_txt = pl.name + ("  [VINNARE]" if is_winner else "")

            cv2.putText(frame, name_txt,
                        (col_name,  y), self.FONT, 0.60, name_col, 1, cv2.LINE_AA)
            cv2.putText(frame, str(pl.score_upper.upper_total),
                        (col_ovre,  y), self.FONT, 0.60, val_col,  1, cv2.LINE_AA)
            cv2.putText(frame, str(pl.score_lower.total),
                        (col_nedre, y), self.FONT, 0.60, val_col,  1, cv2.LINE_AA)
            cv2.putText(frame, str(totals[i]),
                        (col_tot,   y), self.FONT, 0.60, name_col, 1, cv2.LINE_AA)
            y += player_row_h

        # Footer — separator + restart-instruktion
        y += 8
        cv2.line(frame, (pad_l, y), (pad_r, y), (60, 60, 60), 1)
        y += 22
        self._put_centered(frame, "SPACE / R  =  Spela igen", w, y, 0.55, (145, 145, 145), 1)

    def _draw_result_row(self, frame, label: str, value: str,
                         pad_l: int, pad_r: int, y: int,
                         scale: float, val_col: tuple) -> None:
        """Rita en rad med vänsterjusterad label och högerjusterat värde."""
        cv2.putText(frame, label, (pad_l, y),
                    self.FONT, scale, (150, 150, 150), 1, cv2.LINE_AA)
        (vw, _), _ = cv2.getTextSize(value, self.FONT, scale, 1)
        cv2.putText(frame, value, (pad_r - vw, y),
                    self.FONT, scale, val_col, 1, cv2.LINE_AA)

    def _draw_score_row(self, frame, row: dict,
                        pad_l: int, pad_r: int, y: int, row_h: int,
                        stryk_mode: bool = False) -> None:
        """
        Rita en kategorirad i score-popup.

        Fyra tillstånd:
          struck   → mörk röd + [STRUKEN]
          locked   → grå text + [VALD]
          ej valid → grå text, ingen tangent (men klickbar i strykläge)
          valbar   → vit label, grön score (eller grå om 0)
        """
        struck = row.get("struck", False)
        locked = row["locked"]
        valid  = row.get("valid", True)

        if struck:
            # Struken kategori — mörk röd
            label_col = (55, 55, 170)
            score_col = (55, 55, 170)
            label_txt = f"  {row['label']}  [STRUKEN]"
            score_txt = "0"
        elif locked:
            label_col = (85, 85, 85)
            score_col = (85, 85, 85)
            label_txt = f"  {row['label']}  [VALD]"
            score_txt = str(row["score"])
        elif stryk_mode:
            # Strykläge aktiv — alla olåsta kategorier är klickbara (0 poäng)
            label_col = (100, 100, 200)
            score_col = (100, 100, 200)
            label_txt = f"[{row['hotkey']}] {row['label']}"
            score_txt = "0"
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

"""
ui_overlay.py — Visuell overlay för AI Yatzy.

Ansvar:
    Rita header-bar med tärningsboxar, slide-in sidopanel (scoreboard/kategorival)
    och bottom-statusrad på kameraframen.

Denna modul hanterar ENDAST rendering.
Den fattar inga spelbeslut och kommunicerar inte med spellogiken.
"""

import cv2


class UIOverlay:
    """Renderar all UI ovanpå kameraframen."""

    FONT = cv2.FONT_HERSHEY_SIMPLEX

    # Header
    HEADER_H  = 120
    HEADER_BG = (22, 22, 22)

    # Bottom bar
    BOTTOM_H = 52

    # Side panel
    PANEL_W     = 340
    PANEL_BG    = (30, 30, 36)
    PANEL_SPEED = 30   # px per frame — animationshastighet

    # Palettkonstanter
    GOLD  = (0, 215, 255)
    GREEN = (60, 220, 60)
    GRAY  = (145, 145, 155)
    WHITE = (235, 235, 240)

    def __init__(self):
        self._panel_x    = float(-self.PANEL_W)  # animerad x-position (0 = fullt öppen)
        self._panel_open = False

    # ------------------------------------------------------------------
    # Publika metoder (anropas från main.py)
    # ------------------------------------------------------------------

    def draw_ui(self, frame, game_state) -> None:
        """Rita header, bottom-bar, side-panel och toggle-knapp."""
        p = game_state.current_player
        self._draw_header(frame, game_state.dice_values, game_state.locked_dice,
                          p.name, p.is_bot)
        self._draw_bottom(frame, game_state)
        self._advance_panel(game_state)
        self._draw_side_panel(frame, game_state)
        self._draw_toggle_button(frame)

    def handle_click(self, x: int, y: int) -> None:
        """Anropas från mus-callback. Togglar panelen om knappen klickades."""
        btn_x = int(self._panel_x) + self.PANEL_W
        if btn_x <= x <= btn_x + 32 and 70 <= y <= 120:
            self._panel_open = not self._panel_open

    def draw_bot_rolling(self, frame, dice_values: list) -> None:
        h, w = frame.shape[:2]
        bw, bh = int(w * 0.58), 108
        bx, by = (w - bw) // 2, int(h * 0.40)
        overlay = frame.copy()
        cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (16, 16, 16), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
        self._draw_rounded_rect_border(frame, bx, by, bx + bw, by + bh, 10, (80, 200, 80), 2)
        self._put_centered(frame, "BOT KASTAR", w, by + 38, 0.82, (80, 210, 80), 2)
        dice_str = "   ".join(f"[{v}]" for v in dice_values)
        self._put_centered(frame, dice_str, w, by + 82, 0.82, (230, 230, 230), 2)

    def draw_bot_choice(self, frame, label: str) -> None:
        h, w = frame.shape[:2]
        bw, bh = int(w * 0.55), 90
        bx, by = (w - bw) // 2, int(h * 0.40)
        overlay = frame.copy()
        cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (16, 16, 16), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
        self._draw_rounded_rect_border(frame, bx, by, bx + bw, by + bh, 10, self.GOLD, 2)
        self._put_centered(frame, "BOT VALDE:", w, by + 32, 0.72, (130, 130, 130), 1)
        self._put_centered(frame, label,        w, by + 68, 0.82, self.GOLD, 2)

    def draw_game_over(self, frame, players: list) -> None:
        h, w = frame.shape[:2]
        dim = frame.copy()
        cv2.rectangle(dim, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(dim, 0.74, frame, 0.26, 0, frame)

        totals     = [pl.score_upper.upper_total + pl.score_lower.total for pl in players]
        winner_idx = totals.index(max(totals))

        row_h   = 36
        inner_h = 80 + len(players) * row_h + 70
        box_h   = max(inner_h, int(h * 0.42))
        box_w   = int(w * 0.60)
        bx      = (w - box_w) // 2
        by      = (h - box_h) // 2

        self._draw_rounded_rect(frame, bx, by, bx + box_w, by + box_h, 14, (22, 22, 26))
        self._draw_rounded_rect_border(frame, bx, by, bx + box_w, by + box_h, 14, self.GOLD, 2)

        pad_l = bx + 22
        pad_r = bx + box_w - 22
        y     = by + 42

        self._put_centered(frame, "SPELET AR SLUT", w, y, 0.88, self.WHITE, 2)
        y += 22
        cv2.line(frame, (pad_l, y), (pad_r, y), (75, 75, 80), 1)
        y += 14

        col_name  = pad_l
        col_ovre  = pad_l + int(box_w * 0.38)
        col_nedre = pad_l + int(box_w * 0.54)
        col_tot   = pad_l + int(box_w * 0.70)

        for txt, cx in [("Spelare", col_name), ("Ovre", col_ovre),
                        ("Nedre", col_nedre), ("Totalt", col_tot)]:
            cv2.putText(frame, txt, (cx, y), self.FONT, 0.50, (90, 90, 95), 1, cv2.LINE_AA)
        y += 6
        cv2.line(frame, (pad_l, y), (pad_r, y), (55, 55, 60), 1)
        y += row_h - 8

        for i, pl in enumerate(players):
            is_winner = (i == winner_idx)
            nc = self.GOLD if is_winner else (185, 185, 190)
            vc = self.GOLD if is_winner else (145, 145, 150)
            name_txt = pl.name + ("  [VINNARE]" if is_winner else "")
            cv2.putText(frame, name_txt, (col_name, y), self.FONT, 0.60, nc, 1, cv2.LINE_AA)
            cv2.putText(frame, str(pl.score_upper.upper_total), (col_ovre, y), self.FONT, 0.60, vc, 1, cv2.LINE_AA)
            cv2.putText(frame, str(pl.score_lower.total), (col_nedre, y), self.FONT, 0.60, vc, 1, cv2.LINE_AA)
            cv2.putText(frame, str(totals[i]), (col_tot, y), self.FONT, 0.60, nc, 1, cv2.LINE_AA)
            y += row_h

        y += 8
        cv2.line(frame, (pad_l, y), (pad_r, y), (60, 60, 65), 1)
        y += 22
        self._put_centered(frame, "SPACE / R  =  Spela igen", w, y, 0.55, (140, 140, 145), 1)

    # ------------------------------------------------------------------
    # Header — 5 tärningsboxar med rundade hörn och skugga
    # ------------------------------------------------------------------

    def _draw_header(self, frame, dice_values: list, locked_dice: list,
                     player_name: str = "", is_bot: bool = False) -> None:
        w = frame.shape[1]
        cv2.rectangle(frame, (0, 0), (w, self.HEADER_H), self.HEADER_BG, -1)
        cv2.line(frame, (0, self.HEADER_H), (w, self.HEADER_H), (45, 45, 50), 1)

        # Spelarnamnsrad
        if player_name:
            prefix    = "BOT" if is_bot else "TUR"
            name_col  = (100, 200, 100) if not is_bot else (100, 180, 230)
            pre_col   = (120, 120, 130)
            pre_txt   = f"{prefix}:"
            name_txt  = f"  {player_name}"
            (pw, _), _ = cv2.getTextSize(pre_txt + name_txt, self.FONT, 0.52, 1)
            cx = (w - pw) // 2
            cv2.putText(frame, pre_txt, (cx, 14), self.FONT, 0.52, pre_col, 1, cv2.LINE_AA)
            (pw2, _), _ = cv2.getTextSize(pre_txt, self.FONT, 0.52, 1)
            cv2.putText(frame, name_txt, (cx + pw2, 14), self.FONT, 0.52, name_col, 1, cv2.LINE_AA)
        cv2.line(frame, (0, 20), (w, 20), (38, 38, 44), 1)

        # Tärningsboxar
        box_w   = int(w * 0.13)
        box_h   = 82
        gap     = int(w * 0.025)
        total_w = 5 * box_w + 4 * gap
        start_x = (w - total_w) // 2
        box_y   = 20 + (self.HEADER_H - 20 - box_h) // 2
        r       = 10

        for i in range(5):
            bx     = start_x + i * (box_w + gap)
            locked = locked_dice[i]

            # Skugga (förskjuten mörkare kopia)
            self._draw_rounded_rect(frame, bx + 3, box_y + 4,
                                    bx + box_w + 3, box_y + box_h + 4, r, (8, 8, 10))

            # Bakgrund
            bg = (95, 65, 0) if locked else (40, 40, 48)
            self._draw_rounded_rect(frame, bx, box_y, bx + box_w, box_y + box_h, r, bg)

            # Kant
            border = (195, 155, 0) if locked else (65, 65, 80)
            self._draw_rounded_rect_border(frame, bx, box_y, bx + box_w, box_y + box_h, r, border, 1)

            # Etikett "T1"
            lbl = f"T{i + 1}"
            (lw, _), _ = cv2.getTextSize(lbl, self.FONT, 0.46, 1)
            cv2.putText(frame, lbl, (bx + (box_w - lw) // 2, box_y + 22),
                        self.FONT, 0.46, (110, 110, 125), 1, cv2.LINE_AA)

            # Värde
            val     = str(dice_values[i])
            val_col = (255, 205, 50) if locked else (235, 235, 240)
            (vw, _), _ = cv2.getTextSize(val, self.FONT, 1.4, 2)
            cv2.putText(frame, val, (bx + (box_w - vw) // 2, box_y + box_h - 14),
                        self.FONT, 1.4, val_col, 2, cv2.LINE_AA)

    # ------------------------------------------------------------------
    # Bottom-statusrad
    # ------------------------------------------------------------------

    def _draw_bottom(self, frame, game_state) -> None:
        h, w = frame.shape[:2]
        by = h - self.BOTTOM_H

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, by), (w, h), (14, 14, 18), -1)
        cv2.addWeighted(overlay, 0.84, frame, 0.16, 0, frame)
        cv2.line(frame, (0, by), (w, by), (45, 45, 55), 1)

        p          = game_state.current_player
        roll_count = game_state.roll_count
        can_roll   = game_state.can_roll()
        stryk_mode = game_state.stryk_mode

        # Vänster: spelarnamn
        nc = (100, 200, 100) if not p.is_bot else (100, 180, 230)
        cv2.putText(frame, p.name, (14, by + 34), self.FONT, 0.68, nc, 1, cv2.LINE_AA)

        # Mitten: fastext
        if stryk_mode:
            mid_txt = "STRYKLAGE — valj kategori att stryka"
            mid_col = (80, 80, 200)
        elif roll_count == 0:
            mid_txt = "SPACE = kasta"
            mid_col = self.GRAY
        elif can_roll:
            mid_txt = f"Kast {roll_count} / 3   ·   SPACE = kasta igen"
            mid_col = self.GREEN
        else:
            mid_txt = "Kast 3 / 3   ·   Valj kategori i panelen"
            mid_col = (80, 150, 255)
        self._put_centered(frame, mid_txt, w, by + 34, 0.60, mid_col, 1)

        # Höger: totalpoäng
        total     = p.score_upper.upper_total + p.score_lower.total
        score_txt = f"{total} p"
        (sw, _), _ = cv2.getTextSize(score_txt, self.FONT, 0.68, 1)
        cv2.putText(frame, score_txt, (w - sw - 14, by + 34), self.FONT, 0.68, self.GOLD, 1, cv2.LINE_AA)

    # ------------------------------------------------------------------
    # Side-panel — animerad slide-in
    # ------------------------------------------------------------------

    def _advance_panel(self, game_state) -> None:
        """Flytta panel_x mot mål. Auto-öppna när score-menyn är aktiv."""
        if game_state.show_score_menu:
            self._panel_open = True
        target = 0.0 if self._panel_open else float(-self.PANEL_W)
        diff   = target - self._panel_x
        if abs(diff) <= self.PANEL_SPEED:
            self._panel_x = target
        else:
            self._panel_x += self.PANEL_SPEED if diff > 0 else -self.PANEL_SPEED

    def _draw_toggle_button(self, frame) -> None:
        px  = int(self._panel_x)
        bx  = px + self.PANEL_W
        by  = 70
        bw  = 28
        bh  = 50

        self._draw_rounded_rect(frame, bx, by, bx + bw, by + bh, 6, (36, 36, 44))
        self._draw_rounded_rect_border(frame, bx, by, bx + bw, by + bh, 6, (65, 65, 80), 1)
        arrow = "<" if self._panel_open else ">"
        (aw, _), _ = cv2.getTextSize(arrow, self.FONT, 0.62, 2)
        cv2.putText(frame, arrow, (bx + (bw - aw) // 2, by + bh // 2 + 8),
                    self.FONT, 0.62, (170, 170, 190), 2, cv2.LINE_AA)

    def _draw_side_panel(self, frame, game_state) -> None:
        px = int(self._panel_x)
        if px <= -self.PANEL_W:
            return

        h, w  = frame.shape[:2]
        pw    = self.PANEL_W
        x1    = max(0, px)
        x2    = min(w, px + pw)
        top   = self.HEADER_H
        bot   = h - self.BOTTOM_H

        # Panel-bakgrund
        cv2.rectangle(frame, (x1, top), (x2, bot), self.PANEL_BG, -1)
        cv2.line(frame, (x2, top), (x2, bot), (55, 55, 68), 1)
        cv2.line(frame, (x1, top), (x2, top), (55, 55, 68), 1)

        pad_l = px + 16
        pad_r = px + pw - 16
        y     = top + 22

        if game_state.show_score_menu:
            self._panel_score(frame, game_state, px, pw, pad_l, pad_r, y, bot)
        else:
            self._panel_scoreboard(frame, game_state, px, pw, pad_l, pad_r, y, bot)

    def _panel_scoreboard(self, frame, game_state, px, pw, pad_l, pad_r, y, panel_bot) -> None:
        self._panel_title(frame, "POÄNGTAVLA", px, pw, y)
        y += 10
        cv2.line(frame, (pad_l, y), (pad_r, y), (50, 50, 62), 1)
        y += 20

        for i, pl in enumerate(game_state.players):
            is_active = (i == game_state.current_player_index)
            total     = pl.score_upper.upper_total + pl.score_lower.total

            # Rad-highlight
            if is_active:
                self._draw_rounded_rect(frame, pad_l - 6, y - 16,
                                        pad_r + 6, y + 50, 8, (42, 42, 54))
                self._draw_rounded_rect_border(frame, pad_l - 6, y - 16,
                                               pad_r + 6, y + 50, 8, (62, 62, 82), 1)

            nc = self.GOLD if is_active else (165, 165, 175)
            prefix = "> " if is_active else "  "
            cv2.putText(frame, prefix + pl.name, (pad_l, y),
                        self.FONT, 0.56, nc, 1, cv2.LINE_AA)

            tot_txt = f"{total} p"
            (tw, _), _ = cv2.getTextSize(tot_txt, self.FONT, 0.56, 1)
            cv2.putText(frame, tot_txt, (pad_r - tw, y), self.FONT, 0.56, nc, 1, cv2.LINE_AA)

            sc = (115, 115, 128) if not is_active else (150, 150, 165)
            cv2.putText(frame, f"Ovre {pl.score_upper.upper_total}", (pad_l + 8, y + 22),
                        self.FONT, 0.44, sc, 1, cv2.LINE_AA)
            cv2.putText(frame, f"Nedre {pl.score_lower.total}", (pad_l + 120, y + 22),
                        self.FONT, 0.44, sc, 1, cv2.LINE_AA)
            y += 72

    def _panel_score(self, frame, game_state, px, pw, pad_l, pad_r, y, panel_bot) -> None:
        p          = game_state.current_player
        dice       = game_state.dice_values
        stryk_mode = game_state.stryk_mode

        # ── Adaptiv layout ────────────────────────────────────────────
        # Mät tillgänglig höjd och fördela på 15 rader + fast overhead.
        # Fast overhead: titel(26) + sektion×2(32) + sep×3(12) + summor(30) + totalt(24) + instr(20) ≈ 144
        avail  = panel_bot - y - 8           # 8px bottenmarginal
        row_h  = max(13, min(28, (avail - 144) // 15))
        g_sm   = max(4,  row_h // 4)         # litet gap (runt separatorer)
        g_med  = max(10, row_h - 6)          # mellanstort gap (sektionsrubrik)
        fscale = 0.40 if row_h >= 18 else 0.36   # rubrik-/summafont
        rscale = 0.42 if row_h >= 18 else 0.37   # radfont (skickas till _panel_row)

        self._panel_title(frame, "VALJ KATEGORI", px, pw, y)
        y += g_sm + 6
        cv2.line(frame, (pad_l, y), (pad_r, y), (50, 50, 62), 1)
        y += g_sm + 6

        # ── Övre ──────────────────────────────────────────────────────
        cv2.putText(frame, "OVRE", (pad_l, y), self.FONT, fscale, (90, 90, 105), 1, cv2.LINE_AA)
        y += g_med
        for row in p.score_upper.rows(dice):
            self._panel_row(frame, row, pad_l, pad_r, y, False, rscale)
            y += row_h

        y += g_sm
        cv2.line(frame, (pad_l, y), (pad_r, y), (48, 48, 60), 1)
        y += g_sm + 4

        # Övre summor (kompakt: allt på en rad)
        summa_txt = f"Summa {p.score_upper.total}  +Bonus {p.score_upper.bonus}"
        if p.score_upper.bonus_progress > 0:
            summa_txt += f"  ({p.score_upper.bonus_progress} kvar)"
        cv2.putText(frame, summa_txt, (pad_l, y), self.FONT, fscale - 0.04,
                    (100, 100, 115), 1, cv2.LINE_AA)
        y += g_med

        # ── Nedre ─────────────────────────────────────────────────────
        cv2.putText(frame, "NEDRE", (pad_l, y), self.FONT, fscale, (90, 90, 105), 1, cv2.LINE_AA)
        y += g_med
        for row in p.score_lower.rows(dice):
            self._panel_row(frame, row, pad_l, pad_r, y, stryk_mode, rscale)
            y += row_h

        # ── Totalt ────────────────────────────────────────────────────
        y += g_sm
        cv2.line(frame, (pad_l, y), (pad_r, y), (65, 65, 80), 1)
        y += g_sm + 6
        grand = p.score_upper.upper_total + p.score_lower.total
        cv2.putText(frame, f"TOTALT  {grand} p", (pad_l, y),
                    self.FONT, 0.58, self.GOLD, 2, cv2.LINE_AA)

        # ── Instruktion ───────────────────────────────────────────────
        y += g_med
        if stryk_mode:
            cv2.putText(frame, "[a-i] stryka   [s] avbryt",
                        (pad_l, y), self.FONT, fscale - 0.04, (80, 80, 200), 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, "1-6 / a-i = valj   [s] stryk",
                        (pad_l, y), self.FONT, fscale - 0.04, (95, 95, 110), 1, cv2.LINE_AA)

    def _panel_title(self, frame, text: str, px: int, pw: int, y: int) -> None:
        """Centrera rubrik inom panelens bredd."""
        (tw, _), _ = cv2.getTextSize(text, self.FONT, 0.60, 2)
        x = px + (pw - tw) // 2
        cv2.putText(frame, text, (x, y), self.FONT, 0.60, (195, 195, 205), 2, cv2.LINE_AA)

    def _panel_row(self, frame, row: dict, pad_l: int, pad_r: int,
                   y: int, stryk_mode: bool = False, scale: float = 0.44) -> None:
        struck = row.get("struck", False)
        locked = row["locked"]
        valid  = row.get("valid", True)

        if struck:
            lbl = f"  {row['label']}"
            val = "[STRUKEN]"
            lc = sc = (75, 50, 50)
        elif locked:
            lbl = f"  {row['label']}"
            val = str(row["score"])
            lc = sc = (72, 72, 85)
        elif stryk_mode:
            lbl = f"[{row['hotkey']}] {row['label']}"
            val = "0"
            lc = sc = (95, 95, 195)
        elif not valid:
            lbl = f"    {row['label']}"
            val = "-"
            lc = sc = (62, 62, 76)
        else:
            lbl = f"[{row['hotkey']}] {row['label']}"
            val = f"+{row['score']}"
            lc  = (205, 205, 215)
            sc  = (55, 205, 55) if row["score"] > 0 else (95, 95, 110)

        cv2.putText(frame, lbl, (pad_l, y), self.FONT, scale, lc, 1, cv2.LINE_AA)
        (sw, _), _ = cv2.getTextSize(val, self.FONT, scale, 1)
        cv2.putText(frame, val, (pad_r - sw, y), self.FONT, scale, sc, 1, cv2.LINE_AA)

    # ------------------------------------------------------------------
    # Rundade hörn — hjälpmetoder
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_rounded_rect(frame, x1, y1, x2, y2, r, color) -> None:
        cv2.rectangle(frame, (x1 + r, y1), (x2 - r, y2), color, -1)
        cv2.rectangle(frame, (x1, y1 + r), (x2, y2 - r), color, -1)
        cv2.circle(frame, (x1 + r, y1 + r), r, color, -1)
        cv2.circle(frame, (x2 - r, y1 + r), r, color, -1)
        cv2.circle(frame, (x1 + r, y2 - r), r, color, -1)
        cv2.circle(frame, (x2 - r, y2 - r), r, color, -1)

    @staticmethod
    def _draw_rounded_rect_border(frame, x1, y1, x2, y2, r, color, t) -> None:
        cv2.line(frame, (x1 + r, y1),     (x2 - r, y1),     color, t)
        cv2.line(frame, (x1 + r, y2),     (x2 - r, y2),     color, t)
        cv2.line(frame, (x1,     y1 + r), (x1,     y2 - r), color, t)
        cv2.line(frame, (x2,     y1 + r), (x2,     y2 - r), color, t)
        cv2.ellipse(frame, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, t)
        cv2.ellipse(frame, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, t)
        cv2.ellipse(frame, (x1 + r, y2 - r), (r, r), 90,  0, 90, color, t)
        cv2.ellipse(frame, (x2 - r, y2 - r), (r, r), 0,   0, 90, color, t)

    # ------------------------------------------------------------------
    # Hjälp: centrera text på hela frame-bredden
    # ------------------------------------------------------------------

    @staticmethod
    def _put_centered(frame, text: str, frame_w: int,
                      y: int, scale: float, color: tuple, thickness: int) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, _), _ = cv2.getTextSize(text, font, scale, thickness)
        x = (frame_w - tw) // 2
        cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)

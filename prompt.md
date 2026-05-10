# Prompt Logg

---

## 2026-05-10 — Konvertering till webbapp (Flask + HTML/CSS/JS)

### Prompt (sammanfattning)
"Jag vill nu konvertera mitt nuvarande Yatzy-projekt (Python + AI + kamera) till en webbapplikation. Kraven: AI-bot med egna slumptärningar, prioriteringsstrategi, visa botens tärningar, 3 kast per runda, övre + nedre poängtabell, bonus, modulärt. Kamera + YOLO ska vara kvar. Teknikval: Flask (Python) + HTML/CSS/JS."

### Vad som gjordes
Hela spelet portades till en webbapplikation utan att ändra spellogiken (`game_state.py`, `player.py`, `yatzy_score.py`).

**Nya filer:**
- `bot_logic_web.py` — Synkron bot: `roll_dice`, `choose_category`, `execute_choice`. Ingen state-maskin — server beslutar, JS animerar.
- `camera_stream.py` — Bakgrundstråd (daemon) som läser kamera och kör YOLO kontinuerligt. Exponerar `get_live_values()` och `generate_frames()` (MJPEG-generator för Flask).
- `game_logic.py` — Trådsäker wrapper med `threading.RLock`. Alla metoder returnerar JSON-dict med hela speltillståndet. `bot_turn()` returnerar extra fält `bot_dice` och `bot_choice_label`.
- `web_app.py` — Flask-server med 9 endpoints: `/api/start`, `/api/roll`, `/api/toggle_lock`, `/api/register`, `/api/strike`, `/api/toggle_stryk`, `/api/bot_turn`, `/api/restart`, `/video_feed` (MJPEG).
- `templates/index.html` — Startmodal (spelarantal + bot-toggle), bot-overlay med tärningsvisning + valtext, game-over-overlay, spelkontainer (kamera + sidopanel med poängtabell).
- `static/css/style.css` — Mörkt speltema med CSS-variabler. Stilar för modal, tärningsboxar (låst=guldbård), poängrader (locked/struck/invalid/stryk), bot-overlay, spelarmarkörer.
- `static/js/game.js` — Spelklient. `runBotTurn()`: anropar `/api/bot_turn`, visar botens tärningar 3s, sedan val 2.5s, sedan renderar nytt state. `renderState()` renderar alla UI-delar. `buildScoreRow()` hanterar alla radtillstånd (locked/struck/invalid/preview/strykbar).
- `requirements.txt` — Flask + opencv-python + ultralytics + torch/torchvision.

### Tekniska beslut
- Trådsäkerhet: `threading.Lock` i `CameraStream`, `threading.RLock` (reentrant) i `GameLogic` så `get_state()` kan anropas inifrån låsta metoder.
- Bot-timing: server fattar alla beslut direkt, JS hanterar animationsförseningar (3000ms + 2500ms) med `setTimeout`.
- MJPEG: `<img src="/video_feed">` i HTML streamas direkt via Flask `Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")`.
- Speltillstånd skickas alltid komplett från server — ingen partiell uppdatering.

### Ändrade/skapade filer
`bot_logic_web.py` (ny), `camera_stream.py` (ny), `game_logic.py` (ny), `web_app.py` (ny), `templates/index.html` (ny), `static/css/style.css` (ny), `static/js/game.js` (ny), `requirements.txt` (ny)

---

## 2026-05-10 — Bugfix: Sidopanelen kapas i höjdled

### Problem
Kategorivalet i sidopanelen klipptes av längst ner — de sista nedre kategorierna (Chans, Yatzy m.fl.) syntes inte. Orsak: radhöjden `row_h = 23` var hårdkodad och tog inte hänsyn till skärmens faktiska höjd.

### Fix
`row_h` beräknas nu dynamiskt utifrån faktisk tillgänglig panelhöjd:
```python
avail  = panel_bot - y - 8        # faktisk höjd att fördela
row_h  = max(13, min(28, (avail - 144) // 15))   # 15 rader delar på utrymmet
```
Alla mellanrum (gaps) skalas proportionellt med `row_h` via `g_sm` och `g_med`, så att ingenting kapas oavsett kameraupplösning (480p–1080p). Bonus-raden komprimerades till en enda rad istället för två.

### Ändrade filer
- `ui_overlay.py` — `_panel_score` + `_panel_row` (ny `scale`-parameter)
- `CLAUDE.md`, `prompt.md`

---

## 2026-05-10 — UI-uppgradering: slide-in panel, rundade tärningar, modern statusrad

### Syfte
Modernt, rent och spel-likt UI utan att ändra spellogiken. Score-popup ersatt med
animerad slide-in sidopanel till vänster. Tärningsboxar fick rundade hörn och skugga.

### Ändringar
- `ui_overlay.py` komplett omskrivning:
  - `__init__`: animationsstate `_panel_x`, `_panel_open`
  - `handle_click(x, y)`: togglar panelen om toggle-knappen klickades
  - `_draw_header`: rundade tärningsboxar med skugga via `_draw_rounded_rect`
  - `_draw_bottom`: slankare 52px statusrad med spelarnamn (vänster), fastext (mitten), poäng (höger)
  - `_draw_side_panel`: slide-in panel (340px, 30px/frame), auto-öppnas vid kategorival
  - `_draw_toggle_button`: ▶/◀-knapp på panelens högra kant
  - `_panel_scoreboard`: visar alla spelares totaler med aktiv-highlight
  - `_panel_score`: kategorival (övre + nedre) med instruktion — ersätter gamla popup
  - `_draw_rounded_rect` / `_draw_rounded_rect_border`: hjälpmetoder för rundade hörn
  - `draw_score_popup` borttagen
- `camera_module.py`: `set_mouse_callback`, `_on_mouse`, `_mouse_callback`-state,
  `cv2.setMouseCallback` i `start()`
- `main.py`: `mouse_callback` funktion, `camera.set_mouse_callback(mouse_callback)`,
  popup-anrop ersatt med kommentar (hanteras nu av `draw_ui`)

### Ändrade filer
- `ui_overlay.py`
- `camera_module.py`
- `main.py`
- `CLAUDE.md`, `prompt.md`

---

## 2026-05-10 — Bot: Förbättrad strategi + visa vad boten väljer

### Syfte
Boten väljer inte längre alltid "Chans" direkt. En prioritetsordning implementerades och spelaren kan se vad boten valde i 2.5s efter varje drag.

### Prioritetsordning (_choose_category)
1. Bonus-jakt: om `bonus_progress > 0` och `counts.get(face) >= 2` → välj övre kategori (6→1)
2. Starka kombinationer: Yatzy → Kåk → Stor stege → Liten stege → Fyrtal → Tretal → Två par → Par
3. Övre sektion: välj med högst poäng (även count == 1)
4. Chans: sista möjligheten med faktisk poäng
5. Stryk: fallback om ingenting ger poäng

### "BOT VALDE"-banner (Fas 4)
- `is_bot_showing_choice()` / `get_choice_label()` exponeras från bot_logic
- `draw_bot_choice(frame, label)` i UIOverlay — guldmarkerad banner t.ex. "BOT VALDE: Kåk  (25 p)"
- Visas i 2.5s efter valet innan nästa spelare tar vid
- Triggad i `frame_callback` steg 8b

### Ändrade filer
- `bot_logic.py` — komplett omskrivning med prioriteringsstrategi, Fas 4, `_choice_made`, `_last_choice_label`, `_pending_registered`
- `ui_overlay.py` — `draw_bot_choice(frame, label)` tillagd
- `main.py` — steg 8b i `frame_callback`
- `CLAUDE.md`, `prompt.md`

---

## 2026-05-10 — Bot: Visa tärningar 4.5s innan popup öppnas

### Syfte
Boten visar sina slumptärningar synligt i 4.5s → popup öppnas → 1.2s → kategorival.

### Fas-maskin
- Fas 1: `_bot_roll()` → `_bot_rolling=True` (ingen popup)
- Fas 2: efter 4.5s → `show_score_menu=True`
- Fas 3: efter 1.2s → `_choose_category()`

### UI
- `draw_bot_rolling(frame, dice_values)` i UIOverlay — grön banner med "BOT KASTAR" + tärningsvärden
- Anropas i `frame_callback` när `bot_logic.is_bot_rolling()` är True

### Ändrade filer
- `bot_logic.py` — ny fas-maskin, `is_bot_rolling()`, `_bot_rolling`
- `ui_overlay.py` — `draw_bot_rolling()`
- `main.py` — ett anrop tillagt
- `CLAUDE.md`, `prompt.md`

---

## 2026-05-10 — Bugfix: Bot använder egna slumptärningar

### Problem
Boten anropade `game_state.roll()` som läser `_live_values` (kamera/YOLO) → boten spelade med de fysiska tärningarna.

### Fix
Ny `_bot_roll(game_state)` i `bot_logic.py`:
- Genererar `[random.randint(1,6) for _ in range(5)]` → lagras i `_bot_dice`
- Skriver direkt till `game_state.dice_values` (rör ALDRIG `_live_values`)
- Sätter `roll_count = MAX_ROLLS` → ett kast, direkt till kategorival
- `game_state.roll()` anropas inte alls av boten

Fas-maskinen förenklad: Fas 1 = slumpkast, Fas 2 = kategorival.

### Ändrade filer
- `bot_logic.py` (enbart)
- `CLAUDE.md`, `prompt.md`

---

## 2026-05-10 — Bot (grundversion, greedy) + Flerspelars game over-skärm (steg 6–7)

### Bot — grundversion
Den första bot-implementeringen. Boten spelar automatiskt under sin tur utan att kräva användarinteraktion.

**Strategi (greedy):** Boten provar varje tillgänglig kategori och väljer den som ger mest poäng just nu. Om ingenting ger poäng struker boten en kategori. Strategin är snabb men inte optimal — den tänker inte framåt.

**Fas-maskin:** Boten väntar 1 sekund mellan varje steg (kast, om-kast, kategorival) för att spelet ska se trovärdigt ut för spelaren. `bot_act()` anropas varje frame men agerar bara om timern gått ut.

**Input-blockering:** All tangentinput är blockerad under botens tur så att spelaren inte kan störa.

### Flerspelars game over-skärm
`draw_game_over(frame, players)` fick en ny signatur som tar emot hela spelar-listan (tidigare visades bara en spelares resultat). Nu visas en kolumntabell med alla spelares Övre/Nedre/Totalt. Vinnaren markeras med guld och `[VINNARE]`. Boxhöjden anpassas automatiskt till 1–4 spelare.

### Ändrade filer
- `bot_logic.py` (ny fil)
- `main.py` — bot_act i frame_callback, input-blockering, reset_timer
- `ui_overlay.py` — draw_game_over omskriven
- `CLAUDE.md`, `prompt.md`

---

## 2026-05-10 — Flerspelarsystem (steg 1–5)

### Syfte
Stöd för 1–4 spelare med turordning, individuella poängtavlor, startmeny och bot-placeholder. "Botten" (flerspelars game over-skärm) läggs till i nästa session.

### Arkitektur
- `Player`-klass (player.py): namn, is_bot, egna score_upper + score_lower
- `show_start_menu()` (start_menu.py): tkinter-dialog → (num_players, has_bot)
- `GameState(players)`: aktiv spelare via current_player_index + next_player()
- main.py: all score-access via `game_state.current_player.score_upper/lower`
- ui_overlay.py: header visar spelarnamn (grön=människa, blå=bot)

### Flöde
1. Startmeny → välj 1–4 spelare + ev. bot → Starta spelet
2. Spelet skapar Player-objekt (sista = Bot om markerat)
3. Per runda: aktiv spelare kastar, väljer poäng/stryk → next_player()
4. Game over när ALLA spelares kort är klara

### Ändrade filer
- `player.py` (ny), `start_menu.py` (ny)
- `game_state.py`, `main.py`, `ui_overlay.py`
- `CLAUDE.md`, `prompt.md`

---

## 2026-05-09 — Game Over + Resultatskärm

### Syfte
Spelet avslutas automatiskt när alla 15 kategorier (övre + nedre) har ett värde. Resultatskärm med poänguppdelning visas, SPACE/R startar om.

### Implementering

**Slutdetektering:** `_on_score_registered()` i main.py anropas efter varje lyckad poängval/strykning. Kollar `score_upper.is_complete() and score_lower.is_complete()` → sätter `game_state.game_over = True`.

**Blockering:** `key_callback` hanterar game_over-läget överst med `return` — inga kast, inga poängval möjliga.

**Omstart:** SPACE/R → `score_upper.reset()`, `score_lower.reset()`, `game_state.game_over = False`, `start_new_round()`.

**UI:** `draw_game_over()` i UIOverlay dimmar 74%, visar centrerad ruta (guldbård) med övre/bonus/övre total/nedre/grand total + restart-instruktion. Renderas sist i `frame_callback` (ovanpå allt).

### Ändrade filer
- `yatzy_score.py` — `is_complete()`, `reset()` på båda klasser
- `game_state.py` — `game_over: bool = False`
- `main.py` — `_on_score_registered`, game_over-hantering i callbacks
- `ui_overlay.py` — `draw_game_over`, `_draw_result_row`
- `CLAUDE.md`, `prompt.md` — dokumentation

---

## 2026-05-09 — Stryk-funktion (nedre sektion)

### Syfte
Implementera en korrekt stryk-funktion i Yatzy. Spelaren ska kunna aktivera strykläge med [s], sedan välja en nedre kategori (a–i) att stryka (0 poäng, permanent låst). Kräver att alla 3 kast är gjorda.

### Regler
- Stryk kräver `roll_count == MAX_ROLLS`
- Minst en olåst nedre kategori måste finnas
- Struken kategori: score=0, permanent låst, kan inte ändras
- Övre sektion kan inte strukas

### Implementering
- `GameState.stryk_mode: bool` — ny flagga, återställs i `start_new_round()`
- `YatzyScoreLower._struck: set[str]` + `is_struck()` + `strike()` — ny logik
- `rows()` exponerar `struck`-nyckel per rad
- `key_callback`: s-tangent togglar strykläge; i strykläge → `strike()` istället för `register()`; 1–6 blockerade i strykläge
- `draw_score_popup(stryk_mode)` — röd kantlinje i strykläge, uppdaterad instruktionstext
- `_draw_score_row(stryk_mode)` — nytt tillstånd: struck (mörk röd + [STRUKEN]), olåsta kategorier visas klickbara i strykläge

### Ändrade filer
- `game_state.py` — `stryk_mode`
- `yatzy_score.py` — `_struck`, `is_struck`, `strike`, `rows`
- `main.py` — key_callback, frame_callback
- `ui_overlay.py` — draw_score_popup, _draw_score_row
- `CLAUDE.md`, `prompt.md` — dokumentation

---

## 2026-05-09 — Bugfix: Två par kräver nu två OLIKA värden

### Problem
`[6,6,6,6,6]` returnerade `(24, True)` för kategorin "Två par" — felaktigt.

### Rotorsak
Den ursprungliga koden använde `c // 2` (floor-division) för att räkna par per värde.
`Counter({6: 5})` → `floor(5/2) = 2` → `pairs = [6, 6]` → `6*2 + 6*2 = 24`.
Ingen kontroll på att de två paren måste ha **olika** värden.

### Fix
```python
pair_values = sorted([v for v, c in counts.items() if c >= 2], reverse=True)
if len(pair_values) >= 2:
    return (pair_values[0] * 2 + pair_values[1] * 2, True)
return (0, False)
```
Samlar distinkta värden med count≥2. Kräver minst 2 sådana värden.
`[6,6,6,6,6]` → `pair_values = [6]` → `(0, False)`.

### Ändrade filer
- `yatzy_score.py` — `tva_par`-grenen i `YatzyScoreLower.calculate`

---

## 2026-05-09 — Fix: upper_total-property + bonuslogik verifierad

### Kontext
Användaren frågade om bonuslogiken stämmer och om `upper_total` (Summa + Bonus) saknades som begrepp.

### Verifiering
`bonus`-property är beräknad, aldrig lagrad — kan inte ges dubbelt. `total` summerar bara registrerade kategorier (`!= None`) vilket gör att bonus aktiveras automatiskt i rätt ögonblick.

### Tillagda ändringar
- `upper_total`-property tillagd i `YatzyScoreUpper`: `return self.total + self.bonus`
- `ui_overlay.py` popup uppdaterad med "Ovre total: X" i gul accentfärg under Bonus-raden

### Ändrade filer
- `yatzy_score.py` — `upper_total`-property
- `ui_overlay.py` — visar Övre total i popup

---

## 2026-05-09 — Poängsystem: nedre sektionen + grand total

### Full Claude-prompt
```text
Implementera nedre sektionen: Ett par, Två par, Tretal, Fyrtal, Kåk,
Liten stege, Stor stege, Chans, Yatzy.
- calculate() → (score, valid) — ej valid = grå, ej valbar
- Kåk: exakt count==3 + count==2, Yatzy exkluderas
- Två par: floor(c/2) per värde, ta de två högsta
- Tangenter a–i för nedre kategorier
- Visa under övre sektionen i popup med grand total
```

### Sammanfattning
`YatzyScoreLower` och `LOWER_HOTKEY_MAP` lades till i `yatzy_score.py`. `calculate()` returnerar `(score, bool)` — False-flaggan gör att ogiltiga kombinationer visas grått utan tangent. Kåk-logiken kontrollerar exakt `count==3` och `count==2` vilket automatiskt utesluter Yatzy (5 lika, inga sådana counts). Popup omskrevs med `_draw_score_row`-helper (3 tillstånd), radhöjd proportionell mot box_h, popup 91% av frame-höjden. Grand total visas längst ner.

### Ändrade filer
- `yatzy_score.py` — YatzyScoreLower, LOWER_CATEGORIES, LOWER_HOTKEY_MAP
- `ui_overlay.py` — ny popup-signatur + _draw_score_row + nedre sektion
- `main.py` — score_lower, a–i-tangenter
- `CLAUDE.md` — ny loggsektion
- `prompt.md` — denna loggsektion

---

## 2026-05-09 — Poängsystem: övre sektionen (Ettor–Sexor, Summa, Bonus)

### Full Claude-prompt

```text
Implementera ÖVRE sektionen av Yatzy-tabellen.
- Klass YatzyScoreUpper: calculate, register, is_locked, total, bonus, rows
- rows(dice) returnerar raddata för rendering
- Popup visar potentiell poäng och låsta kategorier
- 1-6 tangenter väljer kategori → start_new_round()
- Bonus 50p vid summa >= 63
- Ingen nedre sektion. Ingen kastlogik. Endast poängsystem.
```

### Sammanfattning

`yatzy_score.py` skapades med `UPPER_CATEGORIES`, `HOTKEY_MAP` och `YatzyScoreUpper`. `calculate()` summerar matchande tärningsvärden, `register()` låser in och returnerar False om redan vald. `rows(dice)` ger fullständig raddata inkl. locked/hotkey för rendering. `bonus_progress` beräknar poäng kvar till bonus. Popupen i `ui_overlay.py` fick ny signatur `draw_score_popup(frame, score_upper, dice_values)` med 6 kategorirader, summering, bonusdisplay och progress. `main.py` hanterar 1–6 tangenter via `HOTKEY_MAP` → `register()` → `start_new_round()`.

### Skapade filer
- `yatzy_score.py`

### Ändrade filer
- `ui_overlay.py` — riktigt poänginnehåll i popup
- `main.py` — score_upper, HOTKEY_MAP, 1-6 tangenter
- `CLAUDE.md` — ny loggsektion
- `prompt.md` — denna loggsektion

---

## 2026-05-09 — Score-popup: modal efter varje kast

### Full Claude-prompt

```text
Skapa centrerad popup-meny som visas efter varje kast.
- show_score_menu = True efter SPACE + kast
- Popup pausar spelet, YOLO fortsätter visuellt
- SPACE stänger popup
- draw_score_popup(frame): dimma bakgrund, centrerad ruta,
  "Välj kategori (kommer snart)", "Tryck SPACE för att fortsätta"
- Ingen poängräkning ännu — endast UI och state-logik
```

### Sammanfattning

`GameState` fick `show_score_menu: bool = False` i `__init__` och `start_new_round`. `key_callback` i `main.py` hanterar nu två grenar: popup öppen → stäng; popup stängd + `can_roll()` → `roll()` + öppna popup. `frame_callback` ritar `draw_score_popup` sist om flaggan är satt. `UIOverlay.draw_score_popup` dimmar hela bilden med `addWeighted` (alpha 0.55), ritar centrerad box (56%×38%), titel, undertitel, separator och instruktionstext — allt via `_put_centered`.

### Ändrade filer
- `game_state.py` — `show_score_menu`-flagga
- `ui_overlay.py` — `draw_score_popup`
- `main.py` — ny key-logik + popup-rendering
- `CLAUDE.md` — ny loggsektion
- `prompt.md` — denna loggsektion

---

## 2026-05-09 — UI-redesign: tärningsboxar i header + bottom-statusrad

### Full Claude-prompt

```text
Jag bygger ett AI-Yatzy i Python med OpenCV.
MÅL: Förbättra UI-layouten

1) TOPPEN – 5 separata boxar (T1–T5), centrerad text, låst tärning = annan färg
2) LÄNGST NER – "KAST 2/3" grön/röd, centrerat
3) LÄNGST NER – "Nytt kast: Tryck SPACE" / "Välj poängkategori", halvtransparent bakgrund
Skapa draw_ui(frame, game_state). Dynamisk bredd. Proportionell spacing.
```

### Sammanfattning

`UIOverlay` skrevs om helt. `draw_ui(frame, game_state)` anropar `_draw_header` och `_draw_bottom`. Header: 5 boxar á 13% bildbredd med 2.5% gap, centrerade via `(w - total_w) // 2`. All text centreras med `cv2.getTextSize`. Bottom-bar: `addWeighted` alpha 0.70, rad 1 = "KAST X/3" (grön/röd), rad 2 = instruktionstext. Statisk hjälpmetod `_put_centered` återanvänds för alla horisontellt centrerade strängar. `main.py` uppdaterat till `overlay.draw_ui(frame, game_state)`.

### Ändrade filer
- `ui_overlay.py` — omskriven med `draw_ui`, `_draw_header`, `_draw_bottom`, `_put_centered`
- `main.py` — nytt anrop `draw_ui`
- `CLAUDE.md` — ny loggsektion
- `prompt.md` — denna loggsektion

---

## 2026-05-09 — Kastlogik: GameState, SPACE-tangent, max 3 kast per runda

### Full Claude-prompt

```text
Jag bygger ett AI-baserat Yatzy-spel i Python med OpenCV och YOLO.
Nu vill jag implementera KASTLOGIKEN i spelet.

MÅL: Implementera kastlogik (max 3 kast per runda)
- Max 3 kast per runda, SPACE = kasta
- GameState-klass: roll_count, dice_values, locked_dice
- Visa Roll 1/3, Roll 2/3, Roll 3/3 - Select score
- start_new_round() för ny runda
- Separera logik från rendering
- Inga globala variabler
```

### Sammanfattning

`GameState` (ny fil `game_state.py`) håller `roll_count`, `dice_values`, `locked_dice` och `_live_values`. `update_live()` anropas varje frame; `roll()` låser in kamerans aktuella värden och ökar `roll_count` — blockeras tyst efter 3. `roll_label`-property ger statustext per fas. `CameraModule` fick `set_key_callback()` och skickar alla tangenter utom 'q' till callbacken. `main.py` kopplar SPACE → `game_state.roll()`. `ui_overlay.py` visar tärningsvärden i vänstra 60% och roll-status i högra 40% av panelen.

### Skapade filer
- `game_state.py`

### Ändrade filer
- `camera_module.py` — key callback
- `main.py` — GameState-integration
- `ui_overlay.py` — roll_label i panelen
- `CLAUDE.md` — ny loggsektion
- `prompt.md` — denna loggsektion

---

## 2026-05-09 — Fix: alla 5 slots synliga (dynamiska positioner)

### Problem
T4 och T5 klipptes av till höger — hardkodade 200 px-steg krävde ~1050 px bredd.

### Fix
`slot_w = w // 5` beräknas per frame. Varje slot placeras på `slot_w * i + slot_w // 6`. Font scale sänkt till 0.9. Alla 5 slots syns alltid oavsett kameraupplösning.

### Ändrade filer
- `ui_overlay.py` — dynamiska slotpositioner
- `CLAUDE.md` — ny loggsektion
- `prompt.md` — denna loggsektion

---

## 2026-05-09 — Fast toppmeny med vänster-till-höger-sortering

### Full Claude-prompt

```text
# UPPDATERING: Stabil YOLO-visning + fast toppmeny
# MÅL:
# 1. Sortera alla detekterade tärningar från vänster till höger (baserat på bbox x-koordinat).
# 2. Skapa en fast toppmeny med 5 slots.
# 3. Endast uppdatera siffrorna – de får INTE hoppa runt mellan frames.
# 4. Om mindre än 5 tärningar hittas ska resterande slots visa "-".
# 5. Ingen avancerad tracking – endast sortering på x-koordinat.
```

### Sammanfattning

Sorteringsbaserad approach ersätter den tidigare blink-stabiliseringen. Detektioner sorteras på `bbox[0]` (x1) direkt i `frame_callback`, värden extraheras till en platt lista och paddas till exakt 5 element med `"-"`. `last_valid_dice`-globalen togs bort. `UIOverlay.draw_dice_panel` skrevs om: panel 80 px hög, 5 fasta slots med format `"T1: 3"` på pixelpositionerna `50 + i*200`, `cv2.LINE_AA` för skarp text. Ingen spellogik berörd.

### Ändrade filer

- `main.py` — sortering, borttagning av global state, ny anropssignatur
- `ui_overlay.py` — omskriven `draw_dice_panel` med fasta slots
- `CLAUDE.md` — ny loggsektion
- `prompt.md` — denna loggsektion

---

## 2026-05-09 — Stabilisering av YOLO-detektioner och overlay-panel

### Full Claude-prompt

```text
Vi ska nu förbättra YOLO-visningen i AI Yatzy.

Mål:
1. Skapa stabila tärningsvärden som inte blinkar mellan frames.
2. Visa en liten informationspanel längst upp i kamerafönstret som visar aktuella tärningsvärden.

VIKTIGT:
- Ingen kastlogik.
- Ingen popup-meny.
- Ingen låszonsförändring.
- Endast stabil visning + overlay-panel.
- Uppdatera alltid CLAUDE.md i slutet.

DEL 1 – STABILISERA DETEKTIONER (ANTI-BLINK)
- last_valid_dice = [] i main.py
- Uppdatera endast när len(detections) == 5

DEL 2 – SKAPA EN ÖVERLAY-PANEL
- Ny fil: ui_overlay.py
- Klass: UIOverlay
- Metod: draw_dice_panel(frame, dice_list)
- Mörk rektangel 60 px hög överst i bilden
- Text: "DICE:  [5] [5] [2] [1] [6]"

DEL 3 – INTEGRATION
- UIOverlay-instans i main.py
- Anropas efter stabilisering

DOKUMENTATION
- Uppdatera CLAUDE.md och prompt.md
```

### Sammanfattning

`last_valid_dice` lades till i `main.py` som en global lista — uppdateras **bara** när YOLO returnerar exakt 5 detektioner. Vid färre detektioner behålls föregående värden, vilket eliminerar blinkande tärningssiffror. `UIOverlay` skapades i `ui_overlay.py` med `draw_dice_panel()` som ritar en 60 px mörk panel i bildtoppen och skriver ut tärningsvärden med gul-orange accent-färg. Panelen ritas sist i callback-kedjan, ovanpå lock-zone och bounding boxes.

### Skapade filer

- `ui_overlay.py` — `UIOverlay`-klass med `draw_dice_panel()`

### Ändrade filer

- `main.py` — `last_valid_dice`, stabiliseringslogik, `UIOverlay`-integration
- `CLAUDE.md` — ny loggsektion
- `prompt.md` — denna loggsektion

---

## 2026-05-09 — Låszon

### Full Claude-prompt

```text
Vi ska nu implementera Låszon-systemet i AI Yatzy.

Mål:
- Rita en röd zon som täcker 25% av högra sidan av kamerafönstret
- Identifiera vilka tärningar (YOLO-detektioner) som befinner sig i zonen
- Markera dem som locked = True
- Rita grön bounding box runt låsta tärningar
- Ingen kastlogik ännu (endast visuell + detektering)

1. Skapa ny fil: lock_zone.py med klass LockZone
2. draw_zone(frame) — transparent röd zon, 25% höger
3. process_detections(detections, frame_width) — center_x > 75% → locked
4. Integrera i main.py med kombinerad callback
5. Inga spelregler ännu.
```

### Sammanfattning

`LockZone`-klassen skapades med tre metoder: `draw_zone` ritar transparent röd zon via `addWeighted`, `process_detections` jämför tärningars bounding box-center mot `frame_width * 0.75` och returnerar `locked`-flagga, `draw_detections` ritar grön box om locked och gul om fri. `YoloModule` fick `detect_only()` som kör inferens utan att rita. `main.py` omstrukturerades till en `frame_callback` som orchestrerar hela flödet. `camera_test.py` raderades.

### Skapade filer

- `lock_zone.py`

### Ändrade filer

- `yolo_module.py` — lade till `detect_only()`
- `main.py` — ny `frame_callback` som kopplar YOLO + LockZone
- `prompt.md` — ny loggsektion
- `CLAUDE.md` — ny loggsektion

### Borttagna filer

- `camera_test.py`

---

## 2026-05-09 — Minimering: ta bort överkrav som kraschade Deltaco-kameran

### Användarrapport
Enkel testkod med bara `cv2.VideoCapture(1)` fungerade perfekt. camera_module fungerade inte. Slutsats: CAP_DSHOW + FOURCC=MJPG + TARGET_FPS=20 + resolution-tvingning är för restriktivt för denna kamera.

### Fix
Tog bort allt utom det som bevisats fungerande:
- Ingen backend-flagga (ingen CAP_DSHOW)
- Ingen FOURCC-tvingning
- Ingen FPS-tvingning
- Ingen resolution-tvingning
- Behöll: warmup, fullscreen, callback, felhantering, GaussianBlur

### Ändrade filer
- `camera_module.py`
- `prompt.md`
- `CLAUDE.md`

---

## 2026-05-09 — Felsökning: svart bild efter 1 sekund (Deltaco-kamera)

### Användarrapport
> Bilden visas korrekt i ungefär 1 sekund, sedan blir det svart igen.
> Kamera: Deltaco — 1080p@23fps, 720p@23fps.

### Rotorsak
FPS-mismatch: OpenCV frågar efter 30 FPS (default), men kamerans max är 23 FPS. Kameran levererar frames ur sin initialbuffer i ~1 sekund, men kan inte hålla 30 FPS — bufferten töms och strömmen dör.

Sekundär orsak: `TARGET_WIDTH = 1080` är en icke-standard bredd. Kameran stödjer 1280×720 (720p) eller 1920×1080 (1080p) — inte 1080×720.

### Fix
- `TARGET_FPS = 20` — explicit under kamerans 23 FPS-max för säker marginal
- `TARGET_WIDTH = 1280` — korrekt standard-720p-bredd
- `_warmup()` — kastar 20 frames via `cap.grab()` innan display-loopen startar, stabiliserar exponering och interna kamerabuffertar
- Konfigurationsordning: FOURCC → FPS → upplösning (drivrutinen förhandlar per codec och FPS)

### Ändrade filer
- `camera_module.py`
- `prompt.md`
- `CLAUDE.md`

---

## 2026-05-09 — Felsökning: kameraglitch (pixelformat)

### Full Claude-prompt

```text
Felsök och förbättra camera_module.py.

Problem:
- Kameran går ibland inte att öppna
- MSMF ger grabFrame error
- DirectShow fungerade inte stabilt
- Bilden är suddig och brusig
- Programmet får inte krascha

Gör följande:
- Implementera automatisk fallback-logik: testa CAP_DSHOW, sedan default
- Sätt stabil upplösning 1280×720 med fallback
- Aktivera autofokus och auto-exponering
- Lägg till GaussianBlur (3, 3) per frame
- Felhantering: om frame misslyckas → försök 5 gånger
- Debug-utskrifter: upplösning, FPS, backend

Uppdatera CLAUDE.md och prompt.md.
```

### Rotorsak

Två separata buggar i _open_camera():
1. `cv2.CAP_MSMF` användes istället för `cv2.CAP_DSHOW` — trots att utskriften sa "DirectShow"
2. Ingen FOURCC satt → kameran valde YUY2/NV12 (raw) → OpenCV tolkade byteströmmen fel → horisontella glitch-band i grönt och rött

### Sammanfattning

Bugg 1 fixad: `CAP_MSMF` → `CAP_DSHOW` och `camera_index`-parametern används korrekt.
Bugg 2 fixad: `_configure()` sätter nu `MJPG` som FOURCC *innan* upplösning sätts (ordningen är kritisk — drivrutinen förhandlar upplösning per codec). Faktisk FOURCC läses tillbaka och skrivs ut vid start.

### Ändrade filer

- `camera_module.py` — FOURCC-fix + CAP_DSHOW-fix
- `prompt.md` — ny loggsektion
- `CLAUDE.md` — ny loggsektion

### Teknisk sammanfattning

MJPG är komprimerat, universellt stött av USB-kameror och avkodas stabilt av OpenCV. Raw-format (YUY2/NV12) kräver att stride och byte-layout matchar exakt — vilket varierar per kamera och driver. Att tvinga MJPG eliminerar pixelformat-glitech helt.

---

## 2026-05-08 — Kamerarobusthet och bildkvalitet

### Syfte
Förbättra stabilitet och bildkvalitet utan att riskera att kameran slutar fungera.

### Vad som gjordes
- `CAP_DSHOW` testades som primär backend (stabilare än MSMF på Windows), med automatisk fallback till OpenCVs default om det misslyckas
- Upplösning 1280×720 sattes via `CAP_PROP_FRAME_WIDTH/HEIGHT` med fallback till kamerans eget default
- `CAP_PROP_AUTOFOCUS = 1` och `CAP_PROP_AUTO_EXPOSURE = 0.25` aktiverades (ignoreras tyst om kameran inte stöder dem)
- `cv2.GaussianBlur(frame, (3, 3), 0)` lades till per frame för brusreducering — förbättrar YOLO-detektering utan märkbar suddighet
- Felhantering: upp till 5 på varandra följande misslyckade frame-läsningar tolereras innan programmet avslutas

### Ändrade filer
- `camera_module.py`

---

## 2026-05-08 — Fullskärm och loggningspolicy

### Syfte
Göra kamerafönstret fullskärm och införa obligatorisk dokumentationspolicy för projektet.

### Vad som gjordes
- OpenCV-fönstret konfigurerades att starta i fullskärm via `cv2.namedWindow` + `cv2.setWindowProperty(WND_PROP_FULLSCREEN, WINDOW_FULLSCREEN)` innan loopen startar
- En permanent loggningspolicy skrevs in i `CLAUDE.md`: varje session som förändrar projektet måste dokumenteras med datum, syfte och ändrade filer

### Ändrade filer
- `camera_module.py`
- `CLAUDE.md`

---

## 2026-05-08 — YOLO-integration

### Full Claude-prompt

```text
Du ska implementera YOLO-MODULEN och integrera den med kameramodulen.

MÅL:
Integrera YOLOv8 så att tärningar detekteras i realtid med bounding boxes i kameraflödet.

YOLO integrerades modulärt.
Callback-arkitektur infördes i CameraModule.
Systemet kan nu detektera tärningsvärden 1–6.

KRAV:
- yolo_module.py: Skapa YoloModule-klass som laddar best.pt, kör inferens och
  returnerar annoterat frame med bounding boxes. Lagra last_detections.
- camera_module.py: Lägg till set_frame_callback(callback) — callback anropas
  på varje frame och det returnerade frame visas.
- main.py: Koppla YoloModule.process_frame som callback till CameraModule.
- Rör inga andra moduler.
- Ingen spellogik.
```

### Sammanfattning

`YoloModule` implementerades med `process_frame(frame)` som kör YOLOv8-inferens, ritar bounding boxes och etiketter (värde + konfidens) och lagrar detektioner i `self.last_detections`. `CameraModule` fick `set_frame_callback()` — varje frame passerar callbacken innan den visas. `main.py` kopplar ihop dem med en rad. CUDA används automatiskt om tillgängligt.

### Skapade filer

*(inga nya filer)*

### Ändrade filer

- `yolo_module.py` — Implementerad med `YoloModule` och `process_frame()`
- `camera_module.py` — Utökad med `set_frame_callback()` och callback-anrop i loop
- `main.py` — Uppdaterad med YOLO-instansiering och callback-koppling
- `prompt.md` — Ny loggsektion tillagd

### Arkitekturförklaring

Callback-mönstret håller `CameraModule` oberoende av YOLO — den vet bara att den ska anropa en funktion på varje frame och visa resultatet. `YoloModule.process_frame` är en ren `frame → frame`-transformation. `last_detections` exponeras som instansvariabel för framtida moduler (t.ex. `dice_manager`) utan att ändra callback-signaturen.

### Versionshistorik

| Version | Datum | Beskrivning |
|---|---|---|
| 0.3 | 2026-05-08 | YOLO-integration — realtidsdetektering med callback-arkitektur |

---

## 2026-05-08 — Kameramodul

### Full Claude-prompt

```text
Du ska implementera KAMERA-MODULEN för projektet.

VIKTIGT:
- Implementera ENDAST kamerafunktionalitet.
- Rör inga andra moduler.
- Lägg inte till YOLO.
- Lägg inte till låszon.
- Lägg inte till spel-logik.
- Lägg inte till popup.
- Ingen extra funktionalitet.

MÅL:
Skapa ett fungerande OpenCV-fönster som visar live-feed från en extern USB-kamera.

KRAV:

1. camera_module.py:
   - Skapa en tydlig klass, t.ex. CameraModule.
   - Klassen ska:
        - Initiera VideoCapture(0)
        - Ha en metod start() som:
            - Startar en loop
            - Läser frames
            - Visar dem i ett fönster
            - Avslutas när användaren trycker 'q'
        - Frigöra kameran korrekt
        - Stänga alla OpenCV-fönster korrekt
   - Lägg tydliga kommentarer i koden.
   - Lägg tydlig docstring högst upp som beskriver:
        - Modulens ansvar
        - Att den endast hanterar kameravisning

2. main.py:
   - Ska importera CameraModule
   - Ska instansiera klassen
   - Ska anropa start()
   - Ingen annan logik

3. Felhantering:
   - Om kameran inte kan öppnas:
        - Skriv ut tydligt felmeddelande
        - Avsluta programmet säkert

4. Fönstertitel:
   - Sätt titel till: "AI Yatzy - Camera Feed"

5. Inga globala variabler.
6. Ingen hårdkodad logik utanför klassen.
7. Ingen koppling till framtida moduler.
```

### Sammanfattning

Kameramodulen implementerades som klassen `CameraModule` i `camera_module.py`. Klassen öppnar en USB-kamera via `cv2.VideoCapture(0)`, visar live-feed i ett namngivet fönster och avslutas säkert på 'q'. Felhantering täcker fallet då kameran inte kan öppnas. `main.py` uppdaterades till att importera och starta modulen utan övrig logik.

### Skapade filer

*(inga nya filer)*

### Ändrade filer

- `camera_module.py` — Implementerad med klassen `CameraModule`
- `main.py` — Uppdaterad med import och anrop av `CameraModule`
- `prompt.md` — Ny loggsektion tillagd

### Arkitekturförklaring

`CameraModule` är isolerad och exponerar ett enkelt publikt gränssnitt: `__init__(camera_index)` och `start()`. Intern resurshantering (`_release`) är privat. Klassen har inga beroenden till övriga moduler och innehåller ingen spellogik. `main.py` agerar tunn orchestrator utan egen logik.

### Versionshistorik

| Version | Datum | Beskrivning |
|---|---|---|
| 0.2 | 2026-05-08 | Kameramodul implementerad — live-feed via OpenCV |

---

## 2026-05-08 — Grundstruktur

### Full prompt

> Du ska skapa grundstrukturen för ett modulärt AI-baserat Yatzy-system i Python.
>
> Projektmiljö: Windows, Python 3.11, VS Code, OpenCV, Ultralytics YOLOv8, PyTorch CUDA.
>
> Skapa följande filer i projektets root: main.py, camera_module.py, yolo_module.py, dice_manager.py, lockzone_module.py, game_engine.py, score_system.py, popup_menu.py, ai_opponent.py, prompt.md.
>
> Krav: Lägg en tydlig översta docstring per fil som beskriver modulens ansvar, vad den ska göra i framtiden och vad den INTE ska göra. Ingen kodlogik. Inga funktioner. Inga klasser. Endast struktur och dokumentation.

### Sammanfattning

Projektets modulära arkitektur initialiserades utan funktionalitet. Varje Python-fil innehåller enbart en docstring med modulens ansvar, framtida syfte och explicita begränsningar. Inga funktioner, klasser eller imports lades till. CLAUDE.md skapades som vägledning för framtida AI-sessioner.

### Skapade filer

- `main.py` — Entry point, kopplar ihop alla moduler
- `camera_module.py` — OpenCV kamerahantering
- `yolo_module.py` — YOLOv8 tärningsdetektering med CUDA
- `dice_manager.py` — Tärningarnas tillstånd och historik
- `lockzone_module.py` — Låszonsdetektering i kamerabild
- `game_engine.py` — Spelflöde och turordning
- `score_system.py` — Poängberäkning och scorekort
- `popup_menu.py` — Overlay-meny med OpenCV
- `ai_opponent.py` — AI-motståndare med strategibeslut
- `prompt.md` — Denna loggfil
- `CLAUDE.md` — Arkitekturdokumentation för Claude Code

### Ändrade filer

- `prompt.md` — Uppdaterad med fullständig loggstruktur

### Arkitekturförklaring

Systemet använder en strikt enkelriktad datapipeline:

```
camera_module → yolo_module → dice_manager + lockzone_module
                                      ↓
                               game_engine
                          ↙         ↓         ↘
                 score_system   ai_opponent   popup_menu
```

Varje modul har ett tydligt definierat gränssnitt och kommunicerar inte utanför sin pipeline-position. `main.py` orchestrerar utan att innehålla logik.

### Versionshistorik

| Version | Datum | Beskrivning |
|---|---|---|
| 0.1 | 2026-05-08 | Grundstruktur — tomma moduler med docstrings |

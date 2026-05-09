# Prompt Logg

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

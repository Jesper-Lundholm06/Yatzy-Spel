# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 2026-05-10 — Bot: Förbättrad strategi + visa vad boten väljer

### Syfte
Boten väljer inte längre "Chans" som förstahandsval. En greedy prioriteringsstrategi implementerades och en "BOT VALDE"-banner visas i 2.5s efter varje botdrag.

### Prioriteringsstrategi (_choose_category i bot_logic.py)
1. Bonus-jakt: om `bonus_progress > 0` och minst 2 av ett värde → övre kategori (6→1)
2. Starka kombinationer: Yatzy → Kåk → Stor stege → Liten stege → Fyrtal → Tretal → Två par → Par
3. Övre sektion: högst poäng av tillgängliga kategorier
4. Chans: sista option med faktisk poäng
5. Stryk/Fallback: om inget ger poäng

### Fas 4 i bot-fas-maskinen
- `_choice_made`, `_last_choice_label`, `_pending_registered` — ny state per val
- `is_bot_showing_choice()` / `get_choice_label()` — publika funktioner
- `_BOT_CHOICE_DISPLAY_DELAY = 2.5` s
- Fas 4 anropar `_pending_registered()` (= `on_registered`) efter delay

### UI (draw_bot_choice)
- `UIOverlay.draw_bot_choice(frame, label)` — guldbandad banner vid 40% av skärmhöjden
- "BOT VALDE:" i grå text, kategorietiketten i guld `(0, 215, 255)`
- Anropas i `frame_callback` steg 8b när `bot_logic.is_bot_showing_choice()` är True

### Ändrade filer
- `bot_logic.py` — komplett omskrivning
- `ui_overlay.py` — `draw_bot_choice()` tillagd
- `main.py` — steg 8b i `frame_callback`

---

# Development Logging Policy

Från och med nu gäller:

- Varje förändring i projektet MÅSTE dokumenteras i CLAUDE.md
- Hela Claude-prompten ska sparas
- Datum ska anges
- Ändrade filer ska listas
- Kort teknisk sammanfattning ska skrivas

## Tech Stack

- Python 3.11, Windows
- OpenCV (`cv2`) — kamerahantering och UI-overlay
- Ultralytics YOLOv8 — tärningsdetektering
- PyTorch med CUDA — GPU-accelererad inferens

## Köra projektet

```powershell
python main.py
```

## Aktuell filstruktur (implementerade moduler)

| Fil | Klass | Ansvar |
|---|---|---|
| `main.py` | — | Orchestrator: kopplar alla moduler via callbacks, ingen spellogik |
| `camera_module.py` | `CameraModule` | Kameraström, frame-loop, key-events via callbacks |
| `yolo_module.py` | `YoloModule` | YOLOv8-inferens, `detect_only()` returnerar detektioner |
| `lock_zone.py` | `LockZone` | Visuell låszon (höger 25%), färgar bounding boxes |
| `game_state.py` | `GameState` | `roll_count`, `dice_values`, `locked_dice`, `show_score_menu` |
| `yatzy_score.py` | `YatzyScoreUpper` + `YatzyScoreLower` | All poänglogik, regelkontroll, raddata för rendering |
| `ui_overlay.py` | `UIOverlay` | Header med tärningsboxar, bottom-statusrad, score-popup |

**Ej implementerade filer** (tomma stubs från grundstrukturen, reserverade för framtiden):
`dice_manager.py`, `lockzone_module.py`, `game_engine.py`, `score_system.py`, `popup_menu.py`, `ai_opponent.py`

## Arkitektur och dataflöde

Data flödar i en riktning per frame. Moduler kommunicerar inte med varandra utanför sina definierade gränssnitt.

```
CameraModule.start()
    └─► frame_callback(frame)          [main.py]
            │
            ├─ yolo.detect_only()          → detektioner (value, bbox, conf)
            ├─ lock_zone.process_detections() → låsflaggor per tärning
            ├─ lock_zone.draw_zone()          → röd zon på frame
            ├─ lock_zone.draw_detections()    → grön/gul bbox per tärning
            ├─ game_state.update_live()       → live-värden sparas
            └─ overlay.draw_ui()              → header + bottom-bar
                    [om show_score_menu]:
                    overlay.draw_score_popup() → dimmar + visar poängtabell

CameraModule.start()
    └─► key_callback(key)              [main.py]
            ├─ SPACE → game_state.roll() + show_score_menu = True
            ├─ 1–6  → score_upper.register() + start_new_round()
            └─ a–i  → score_lower.register() + start_new_round()
```

### Tangentmappning

| Tangent | Effekt |
|---|---|
| `q` | Avsluta programmet |
| `SPACE` | Kasta (om kast kvar) / stäng popup utan val |
| `1`–`6` | Välj övre kategori (Ettor–Sexor) i popup |
| `a`–`i` | Välj nedre kategori (Ett par–Yatzy) i popup |

### Viktiga designregler

- `yolo_module` laddar färdig modell (`best.pt`) — tränar inte.
- `lock_zone` avgör låsning visuellt — påverkar inte poänglogiken.
- `game_state` håller rundans tillstånd — ingen renderingskod.
- `yatzy_score` beräknar och lagrar poäng — väljer inte kategori.
- `ui_overlay` renderar — fattar inga beslut.
- `main.py` orchestrerar — innehåller ingen spellogik.

## prompt.md

Filen `prompt.md` används som loggbok för Claude-sessioner. Vid varje ny session som förändrar projektet ska en ny sektion läggas till **överst** i filen med datum, syfte, skapade/ändrade filer och teknisk sammanfattning.

---

## 2026-05-10 — Bot: Visa tärningar 4.5s innan popup öppnas

### Syfte
Boten visar sina slumptärningar tydligt på skärmen i 4.5 sekunder så spelaren hinner se dem, innan popup-menyn öppnas och kategorival görs.

### Fas-maskin (bot_logic.py)
| Fas | Trigger | Åtgärd | Väntan |
|---|---|---|---|
| 1 | `roll_count==0, not _bot_rolling` | `_bot_roll()`, `_bot_rolling=True` | 4.5s |
| 2 | `_bot_rolling==True, timer>=4.5s` | `_bot_rolling=False`, `show_score_menu=True` | 1.2s |
| 3 | `show_score_menu, not can_roll(), timer>=1.2s` | `_choose_category()` | — |

### Isolering
- `_bot_rolling: bool` — modul-variabel, enbart läst av `is_bot_rolling()`
- `is_bot_rolling()` — publik funktion för main.py att fråga
- `_live_values` och kamerans värden rörs aldrig

### UI (ui_overlay.py)
- `draw_bot_rolling(frame, dice_values)` — ny metod
  - Halvtransparent grön-kantad banner i mitten (y=40% av skärmen)
  - "BOT KASTAR" rubrik
  - `[3]  [5]  [1]  [6]  [2]` — botens tärningar synliga

### main.py (ett anrop tillagt)
- Steg 8: `if bot_logic.is_bot_rolling(): overlay.draw_bot_rolling(frame, game_state.dice_values)`
- Steg 9: `bot_logic.bot_act(...)` (oförändrad logik)

### Ändrade filer
- `bot_logic.py` — fas-maskin med timing, `is_bot_rolling()`, `_bot_rolling`-flagga
- `ui_overlay.py` — `draw_bot_rolling()`
- `main.py` — ett steg tillagt i `frame_callback`

---

## 2026-05-10 — Bugfix: Bot använder egna slumptärningar (isolerat från kamera)

### Problem
Boten använde `game_state.roll()` som kopierar `_live_values` (YOLO/kamera) till `dice_values`. Boten spelade alltså med de fysiska tärningarna istället för sina egna.

### Fix (enbart bot_logic.py)
- `_bot_dice: list[int]` — modul-nivå isolerad lista för botens egna tärningar
- `_bot_roll(game_state)` ny funktion:
  - Genererar `[random.randint(1,6) for _ in range(5)]`
  - Skriver **direkt** till `game_state.dice_values` — **rör aldrig** `_live_values`
  - Sätter `roll_count = MAX_ROLLS` direkt (ett kast, ingen om-kastlogik)
- Fas-maskinen förenklad: Fas 1 = `_bot_roll` + öppna popup, Fas 2 = välj kategori
- `game_state.roll()` anropas **inte** längre av boten

### Designregel
`game_state.dice_values` = bekräftade spelvärdena (sätts av roll() eller _bot_roll).
`game_state._live_values` = kamerans aktuella YOLO-läsning (sätts av update_live).
Dessa är separata — boten skriver till dice_values, kameran uppdaterar _live_values.

### Ändrade filer
- `bot_logic.py` — `_bot_dice`, `_bot_roll`, förenklad fas-maskin

---

## 2026-05-10 — Bot (greedy) + Flerspelars game over-skärm (steg 6–7)

### Bot-strategi (bot_logic.py)

**Ny fil: `bot_logic.py`**
- `BOT_ACTION_DELAY = 1.0s` — fördröjning mellan bot-åtgärder (synlig spelupplevelse)
- `reset_timer()` — anropas när botens tur börjar (efter `next_player()` eller omstart)
- `bot_act(game_state, on_registered)` — anropas varje frame, agerar bara om timer gått ut
- `_execute()` — fas-maskin: Fas 1 = initialt kast, Fas 2 = kasta om, Fas 3 = välj kategori
- `_choose_category()` — greedy: scanna övre + nedre, välj max score; om allt 0 → stryk första lediga nedre; fallback = registrera övre med 0

**main.py-integrering**
- `bot_logic.bot_act()` anropas i steg 8 i `frame_callback`
- `key_callback` returnerar tidigt om `current_player.is_bot` (blockerar tangenttryckningar)
- `reset_timer()` anropas i tre situationer: uppstart (om bot är första), efter `next_player()`, efter omstart

### Game over-skärm (flerspelarversion)

`draw_game_over(frame, players: list)` — ny signatur
- Beräknar `totals[]` och `winner_idx = totals.index(max(totals))`
- Boxhöjd anpassas till antal spelare: `max(inner_h, int(h*0.42))`
- Kolumntabell: Spelare | Övre | Nedre | Totalt
- Vinnare: guld text `(0, 215, 255)` + `[VINNARE]`-suffix; övriga: grå
- SPACE/R → omstart (återställer alla spelares scores + spelarindex)

### Ändrade filer
- `bot_logic.py` (ny)
- `main.py` — bot_logic-import, bot_act i frame_callback, input-blockering, reset_timer-anrop
- `ui_overlay.py` — draw_game_over reskriven (flerspelarversion)

---

## 2026-05-10 — Flerspelarsystem (steg 1–5)

### Syfte
Bygga om systemet till att stödja 1–4 spelare med turordning, individuella poängtavlor och startmeny. Bot-stöd förbereds (ej AI-logik ännu).

### Nya filer

**player.py**
- `Player(name, is_bot=False)` — namn, bot-flagga, egna `score_upper` + `score_lower`

**start_menu.py**
- `show_start_menu() → (int, bool)` — tkinter-dialog, returnerar (antal_spelare, har_bot)
- Mörkt tema, radioknappar 1–4, kryssruta för bot, Start-knapp

### Ändringar per fil

**game_state.py**
- `__init__(players: list)` — tar nu en lista av Player-objekt
- `current_player_index: int = 0`
- `current_player` — property, returnerar `players[current_player_index]`
- `next_player()` — ökar index (modulo antal), anropar `start_new_round()`
- `start_new_round()` återställer INTE `current_player_index` eller `game_over`

**main.py**
- Kör `show_start_menu()` vid uppstart, skapar Player-lista
- `GameState(players)` istället för `GameState()`
- Modul-nivå `score_upper`/`score_lower` borttagna — allt via `game_state.current_player`
- `_on_score_registered()`: kollar om ALLA spelares kort är klara → game_over, annars `next_player()`
- Omstart återställer alla spelares scores + `current_player_index = 0`

**ui_overlay.py**
- `HEADER_H` 100 → 120 px (20 px extra för spelarnamnrad)
- `_draw_header(..., player_name, is_bot)` — visar "TUR: Spelare 1" (grön) eller "BOT: Bot" (blå)
- Separator-linje vid y=20 delar spelarrad från tärningsboxar

### Tangentmappning (oförändrad)
Alla tangenter fungerar som förut — SPACE, 1–6, a–i, s, r — men nu per aktiv spelare.

### Ändrade filer
- `player.py` (ny)
- `start_menu.py` (ny)
- `game_state.py`
- `main.py`
- `ui_overlay.py`

---

## 2026-05-09 — Game Over + Resultatskärm

### Syfte
Spelet avslutas automatiskt när alla 15 kategorier (6 övre + 9 nedre) har ett värde. En resultatskärm visas med poänguppdelning och möjlighet att starta om.

### Logik

**Kontroll efter varje poängval/strykning (`_on_score_registered` i main.py)**
```python
if score_upper.is_complete() and score_lower.is_complete():
    game_state.game_over = True
    game_state.show_score_menu = False
    game_state.stryk_mode = False
else:
    game_state.start_new_round()
```

**Omstart (key_callback)**
- SPACE eller R på resultatskärmen → `score_upper.reset()` + `score_lower.reset()` + `game_state.game_over = False` + `start_new_round()`
- `return` i game_over-blocket blockerar alla andra tangenttryckningar

### Ändringar per fil

**yatzy_score.py (båda klasserna)**
- `is_complete()` — True när alla kategorier har ett värde (≠ None)
- `reset()` — återställer `_scores` till alla None (YatzyScoreLower tömmer även `_struck`)

**game_state.py**
- `game_over: bool = False` tillagd i `__init__` (återställs INTE av `start_new_round()`)

**main.py**
- `_on_score_registered()` — ny hjälpfunktion: loggar totalen, kollar game_over, annars start_new_round
- `key_callback` — game_over-läge hanteras överst med `return` (blockerar alla andra nycklar)
- `frame_callback` — steg 7: `overlay.draw_game_over()` renderas ovanpå allt

**ui_overlay.py**
- `draw_game_over(frame, score_upper, score_lower)` — ny metod: dimmar 74%, centrerad resultatruta med guldbård, visar övre/bonus/övre total/nedre/grand total + restart-instruktion
- `_draw_result_row(...)` — ny hjälpmetod (label vänster, värde höger)

### Ändrade filer
- `yatzy_score.py` — `is_complete`, `reset` på båda klasserna
- `game_state.py` — `game_over`-flagga
- `main.py` — `_on_score_registered`, uppdaterad `key_callback` och `frame_callback`
- `ui_overlay.py` — `draw_game_over`, `_draw_result_row`

---

## 2026-05-09 — Stryk-funktion (nedre sektion)

### Syfte
Spelaren ska kunna stryka en valfri olåst nedre kategori efter att alla 3 kast är gjorda. Struken kategori får 0 poäng och låses permanent.

### Regler implementerade
- Stryk är bara tillgänglig när `roll_count == MAX_ROLLS` (alla kast använda).
- Minst en olåst nedre kategori måste finnas.
- Man kan inte stryka övre sektion, bonus, summa eller total.
- Struken kategori kan inte väljas igen.

### Tangentmappning tillagd
| Tangent | Effekt |
|---|---|
| `s` | Aktivera/avbryt strykläge (popup öppen, alla kast klara) |
| `a`–`i` i strykläge | Struk vald nedre kategori (0 poäng, permanent låst) |

### Ändringar per fil

**game_state.py**
- `stryk_mode: bool = False` tillagd i `__init__` och `start_new_round()`

**yatzy_score.py (YatzyScoreLower)**
- `_struck: set[str]` — spårar struken kategorier
- `is_struck(key)` — bool
- `strike(key)` — sätter `_scores[key] = 0`, lägger till i `_struck`, returnerar False om redan låst
- `rows()` — ny nyckel `struck` per rad

**main.py (key_callback)**
- `can_stryk`-check: `roll_count >= MAX_ROLLS` AND minst en olåst nedre kategori
- `s`-tangent: togglar `stryk_mode` (aktivera/avbryt)
- I strykläge + `a`–`i`: anropar `score_lower.strike()` istället för `register()`
- Normal poängval blockeras i strykläge

**ui_overlay.py**
- `draw_score_popup` signatur: `stryk_mode: bool = False` tillagd
- Popup-kantlinje: röd `(40, 40, 200)` i strykläge, grå annars
- Instruktionstext: visar stryklägesstatus och `[s] Stryk`-hint
- Nedre rader renderas med `stryk_mode` → alla olåsta kategorier visas klickbara (blå/röd)
- `_draw_score_row`: nytt tillstånd `struck` → mörk röd text + `[STRUKEN]`

### Ändrade filer
- `game_state.py`
- `yatzy_score.py`
- `main.py`
- `ui_overlay.py`

---

## 2026-05-09 — Bugfix: Två par kräver två OLIKA värden

### Problem
`[6,6,6,6,6]` returnerade `(24, True)` för "Två par" — felaktigt.

### Rotorsak
`floor(c/2)` per värde skapade `pairs = [6, 6]` ur ett enda värde → inget krav på distinkta värden.

### Fix (YatzyScoreLower.calculate, "tva_par")
```python
pair_values = sorted([v for v, c in counts.items() if c >= 2], reverse=True)
if len(pair_values) >= 2:
    return (pair_values[0] * 2 + pair_values[1] * 2, True)
return (0, False)
```
Tabellen i nedre sektionen korrigeras: Två par kräver nu minst 2 distinkta värden med count≥2.

### Ändrade filer
- `yatzy_score.py` — `tva_par`-grenen i `YatzyScoreLower.calculate`

---

## 2026-05-09 — Poängsystem: nedre sektionen + grand total

### Syfte
Implementera nedre sektionens 9 kategorier med korrekt Yatzy-regellogik, integrera i popup och hantera tangenter a–i för val.

### Regelimplementering (YatzyScoreLower.calculate)

| Kategori | Logik | Specialfall |
|---|---|---|
| Ett par | max(v där count≥2) × 2 | — |
| Två par | Två distinkta värden med count≥2, ta de två högsta | fyra lika = OGILTIGT |
| Tretal | max(v där count≥3) × 3 | — |
| Fyrtal | max(v där count≥4) × 4 | — |
| Kåk | sum(dice) om exakt count==3 och count==2 | Yatzy (5 lika) exkluderas |
| Liten stege | sorted==\[1,2,3,4,5\] → 15 | — |
| Stor stege | sorted==\[2,3,4,5,6\] → 20 | — |
| Chans | sum(dice) alltid valbar | — |
| Yatzy | len(counts)==1 → 50 | — |

`calculate()` returnerar `(score, valid: bool)` — `valid=False` → grå, ej klickbar.
`register()` returnerar False om kategorin är låst **eller** ej valid.

### UI-popup (ui_overlay.py)

- `draw_score_popup(frame, score_upper, score_lower, dice_values)` — ny signatur.
- `_draw_score_row(frame, row, pad_l, pad_r, y, row_h)` — ny hjälpmetod, 3 tillstånd: locked/ej valid/valbar.
- Radhöjd: `max(22, (box_h - 165) // 20)` — proportionell, fungerar vid alla upplösningar.
- Popup-höjd: 91% av frame.
- Grand total (övre_total + nedre_total) visas längst ner i popup.

### Tangenter
- 1–6 → övre sektion
- a–i → nedre sektion (a=ett par ... i=yatzy)
- SPACE → stäng popup om kast kvar

### Ändrade filer
- `yatzy_score.py` — `YatzyScoreLower`, `LOWER_CATEGORIES`, `LOWER_HOTKEY_MAP`
- `ui_overlay.py` — ny popup-signatur, `_draw_score_row`, nedre sektion
- `main.py` — `score_lower`, `LOWER_HOTKEY_MAP`, a–i-tangenter

---

## 2026-05-09 — Poängsystem: övre sektionen (Ettor–Sexor, Summa, Bonus)

### Syfte
Implementera övre sektionens poängsystem med live-beräkning, kategori-val via tangent 1–6 och korrekt bonus-logik. Ingen nedre sektion.

### Ny fil: yatzy_score.py

`UPPER_CATEGORIES` — lista med tuples `(key, label, face, hotkey)` som definierar alla 6 kategorier. Används av klassen och exporteras till `HOTKEY_MAP`.

`HOTKEY_MAP: dict[str, str]` — `"1"` → `"ettor"` etc. Importeras av `main.py` för tangent-routing.

`YatzyScoreUpper`:
- `_scores: dict[str, int | None]` — None = ej vald.
- `calculate(key, dice)` — summerar tärningar som matchar kategorins face-värde; ignorerar `"-"`.
- `register(key, dice)` → bool — låser in poäng, returnerar False om redan vald.
- `is_locked(key)` — bool.
- `total` — property, summa av registrerade kategorier.
- `bonus` — property, 50 om `total >= 63`, annars 0.
- `bonus_progress` — property, poäng kvar till bonus.
- `rows(dice)` — returnerar lista med dicts redo för rendering (key, label, score, locked, hotkey).

### Popup-uppdatering: ui_overlay.py

`draw_score_popup(frame, score_upper, dice_values)` — ny signatur.
- Kategorirader: `[1] Ettor  +2` (tillgänglig) / `  Ettor [VALD]  2` (låst, grå).
- Grön score om > 0, grå om 0.
- Summa + Bonus under separator.
- "X poäng kvar till bonus" visas om bonus ej uppnådd.
- Instruktion längst ner: "1–6 = välj kategori | SPACE = fortsätt kasta".

### main.py

- `score_upper = YatzyScoreUpper()` instansieras.
- `key_callback`: popup öppen + 1–6 → `score_upper.register()` → `start_new_round()`.
- SPACE i popup tillåts bara stänga om `can_roll()` — vid kast 3 måste kategori väljas.

### Skapade filer
- `yatzy_score.py`

### Ändrade filer
- `ui_overlay.py` — `draw_score_popup` med riktigt poänginnehåll
- `main.py` — `score_upper`, `HOTKEY_MAP`, ny key-logik

---

## 2026-05-09 — Score-popup: modal efter varje kast

### Syfte
Lägga till en score-popup-meny som pausar spelet efter varje kast. Ingen poängräkning — endast UI och state-logik.

### Tillståndslogik

`GameState.show_score_menu: bool = False` — ny flagga.

SPACE-flöde i `main.py`:
1. Popup stängd + `can_roll()` → `roll()` → `show_score_menu = True`
2. Popup öppen → `show_score_menu = False` (spelet återupptas)

`start_new_round()` återställer `show_score_menu = False`.

### Popup-design (UIOverlay.draw_score_popup)
- `addWeighted` 0.55 alpha dimmar hela bakgrunden.
- Centrerad ruta: 56% bildbredd × 38% bildhöjd.
- Mörk bakgrund `(28, 28, 28)` + grå kantlinje.
- Rad 1 (y=32% av boxhöjd): "Valj kategori" — stor vit text.
- Rad 2: "(poangval kommer snart)" — liten grå text.
- Separator-linje vid 60% av boxhöjd.
- Rad 3 (nära botten): "Tryck SPACE for att fortsatta".
- All text centrerad via `_put_centered()`.
- Renderas sist i `frame_callback` → ligger alltid ovanpå allt annat.

### Ändrade filer
- `game_state.py` — `show_score_menu`-flagga i `__init__` och `start_new_round`
- `ui_overlay.py` — ny metod `draw_score_popup(frame)`
- `main.py` — popup-rendering i `frame_callback`, ny SPACE-logik i `key_callback`

---

## 2026-05-09 — UI-redesign: tärningsboxar i header + bottom-statusrad

### Syfte
Ersätta den röriga textraden med ett strukturerat UI: separata boxar per tärning i headern och en halvtransparent statusrad längst ner.

### Layout

**Header (toppen, 100 px)**
- Mörk bakgrund, separator-linje mot kamerabilden.
- 5 boxar centrerade horisontellt: bredd 13% av bildbredden var, gap 2.5%.
- Varje box: liten grå etikett "T1" överst, stort vitt värde (scale 1.5) underst.
- Låst tärning → tonad gul bakgrund (redo för framtida låslogik).
- All textcentrering via `cv2.getTextSize` — fungerar vid valfri upplösning.

**Bottom-statusrad (80 px, halvtransparent)**
- `cv2.addWeighted` med alpha 0.70 för halvtransparent mörk bakgrund.
- Rad 1: `"KAST 2 / 3"` — grön om kast kvar, röd vid 3/3. Dold vid kast 0.
- Rad 2: `"Nytt kast: Tryck SPACE"` / `"Välj poängkategori"` / `"Tryck SPACE för att kasta"`.
- Hjälpmetod `_put_centered()` beräknar x via `(frame_w - text_w) // 2`.

### Ändrade filer
- `ui_overlay.py` — helt omskriven; `draw_dice_panel` → `draw_ui(frame, game_state)` + `_draw_header` + `_draw_bottom`
- `main.py` — `draw_dice_panel(...)` → `draw_ui(frame, game_state)`

---

## 2026-05-09 — Kastlogik: GameState, SPACE-tangent, max 3 kast per runda

### Syfte
Lägga till riktig Yatzy-rundlogik: max 3 kast per runda, SPACE-tangent för att kasta, tydlig statustext i UI-panelen. Ingen poänglogik.

### Arkitektur

**game_state.py (ny)**
- `GameState`-klass med: `roll_count`, `dice_values` (5 bekräftade värden), `locked_dice` (5 bools), `_live_values` (senaste YOLO-läsning).
- `update_live(values)` — anropas varje frame med YOLO-detektioner.
- `roll()` — kopierar `_live_values` → `dice_values` för olåsta slots, ökar `roll_count`. Returnerar False om `roll_count >= 3`.
- `can_roll()` — bool.
- `start_new_round()` — återställer allt.
- `roll_label` — property som returnerar statustext beroende på fas.

**camera_module.py**
- Ny: `set_key_callback(callback)` och `_key_callback`-attribut.
- I loopen: `key = cv2.waitKey(1) & 0xFF` — om `key != 255` och callback finns → anropa den.
- 'q' avslutar fortfarande loopen exklusivt.

**main.py**
- `game_state = GameState()` instansieras.
- `frame_callback` anropar `game_state.update_live(live_values)` och ritar panel med `game_state.dice_values` + `game_state.roll_label`.
- `key_callback(key)` anropar `game_state.roll()` vid SPACE.

**ui_overlay.py**
- `draw_dice_panel` utökad med `roll_label: str = ""`.
- Tärningsslots täcker vänstra 60% av panelen; statustext visas i de resterande 40%.
- Grön text vid aktiv runda, orange-röd text vid "Välj poäng".

### Skapade filer
- `game_state.py`

### Ändrade filer
- `camera_module.py` — `set_key_callback`, key-hantering i loop
- `main.py` — `GameState`-integration, `key_callback`
- `ui_overlay.py` — `roll_label`-parameter, delad panel

---

## 2026-05-09 — Fix: alla 5 slots synliga (dynamiska positioner)

### Problem
T4 och T5 klipptes bort vid smalare kameraupplösningar. Hardkodade steg på 200 px krävde minst ~1050 px bredd för att alla 5 slots skulle synas.

### Fix
Slotpositioner beräknas nu dynamiskt: `slot_w = w // 5`, `x = slot_w * i + slot_w // 6`. Alla 5 slots fyller alltid hela panelbredden oavsett upplösning. Font scale sänkt 1.0 → 0.9 för att texten ska rymmas även på smala frames.

### Ändrade filer
- `ui_overlay.py` — dynamiska slotpositioner, borttagna hardkodade konstanter

---

## 2026-05-09 — Fast toppmeny med vänster-till-höger-sortering

### Syfte
Ersätta den blink-baserade stabiliseringen med en sorteringsbaserad toppmeny som alltid visar exakt 5 fasta slots i spatial ordning.

### Lösning

**Sortering (main.py)**
- Detektioner sorteras på `bbox[0]` (x1) → vänster till höger.
- Värden extraheras till en platt lista: `[3, 5, 1, ...]`.
- Listan paddas med `"-"` tills den är exakt 5 lång och trunkeras vid överskott.
- `last_valid_dice`-variabeln togs bort — ingen global state behövs.

**Fast toppmeny (ui_overlay.py)**
- Panel höjd ändrad: 60 px → 80 px.
- Varje slot på fast x-position: `50 + i * 200` → T1 vid x=50, T2 vid x=250, osv.
- Format per slot: `"T1: 3"`, `"T2: -"` — aldrig omflyttning, alltid samma pixelposition.
- `cv2.LINE_AA` för kantutjämnad text.

### Ändrade filer
- `main.py` — sorteringslogik, tar bort `last_valid_dice`, ny `draw_dice_panel`-anropssignatur
- `ui_overlay.py` — omskriven `draw_dice_panel` med fasta slots och nytt API

---

## 2026-05-09 — Stabilisering av YOLO-detektioner och overlay-panel

### Syfte
Eliminera blinkande tärningsvärden och lägga till en visuell informationspanel i kamerafönstret.

### Lösning

**Anti-blink-stabilisering (main.py)**
- `last_valid_dice: list[dict] = []` — global variabel som håller senaste giltiga detektioner.
- Uppdateras **endast** när `len(detections) == 5`. Vid färre detektioner behålls föregående värden.
- Förhindrar att siffror försvinner när YOLO missar en tärning i enstaka frames.

**Overlay-panel (ui_overlay.py)**
- Ny klass `UIOverlay` med metod `draw_dice_panel(frame, dice_list)`.
- Ritar en 60 px hög mörk panel i toppen av bilden via `cv2.rectangle`.
- Visar text: `DICE:  [3] [5] [1] [6] [2]` — gul-orange accent för värden.
- Separeras visuellt från resten av bilden med en tunn linje.

### Skapade/ändrade filer
- `ui_overlay.py` — ny fil med `UIOverlay`-klassen
- `main.py` — stabiliseringslogik + integration av `UIOverlay`

### Teknisk sammanfattning
Enkel frame-baserad stabilisering utan historik-buffert — zero komplexitet, hög effekt.
Overlay renderas sist i callback-kedjan så att panelen alltid syns ovanpå lock-zone och bounding boxes.
Ingen spellogik, ingen popup-meny och ingen låszonsförändring berörs.

---

## 2026-05-09 — Låszon

### Hur låszonen fungerar
- Zonen täcker **höger 25%** av kamerabilden (startar vid `frame_width * 0.75`)
- En tärning anses **låst** om bounding box-centrets x-koordinat överstiger den gränsen
- `draw_zone()` ritar en transparent röd overlay via `cv2.addWeighted`
- `draw_detections()` ritar **grön** bounding box för låsta tärningar, **gul** för fria
- Ingen kastlogik är kopplad — låsning är enbart visuell i detta steg

### Dataflöde per frame
```
camera_module → frame_callback i main.py
                    ├─ yolo.detect_only(frame)        → råa detektioner
                    ├─ lock_zone.process_detections() → [{value, bbox, locked}, ...]
                    ├─ lock_zone.draw_zone(frame)      → ritar röd zon
                    └─ lock_zone.draw_detections()     → ritar färgade boxes
```

### Skapade/ändrade filer
- `lock_zone.py` — ny fil med `LockZone`-klassen
- `yolo_module.py` — ny metod `detect_only()` (inferens utan ritning)
- `main.py` — omstrukturerad med `frame_callback`
- `camera_test.py` — raderad

---

## 2026-05-09 — Minimering: ta bort överkrav (Deltaco-kamera)

### Diagnos
Enkel testkod med bara `cv2.VideoCapture(1)` fungerade. camera_module fungerade inte. Orsak: kombination av CAP_DSHOW + MJPG + FPS-tvingning + resolution är för restriktivt för Deltaco-kameran — drivrutinen accepterar inte konfigurationen.

### Lösning
Allt tvingande konfiguration borttaget. Kvar: default VideoCapture, warmup, fullscreen, callback, felhantering. Kameran väljer själv codec, FPS och upplösning.

### Designregel
Lägg aldrig till fler krav än nödvändigt. Om kameran fungerar med default → använd default.

### Ändrade filer
- `camera_module.py`

---

## 2026-05-09 — Felsökning: svart bild efter 1 sekund (Deltaco-kamera)

### Rotorsak
FPS-mismatch: OpenCV frågar 30 FPS (default), Deltaco-kameran klarar max 23 FPS. Bufferten töms på ~1 sekund och strömmen dör. `TARGET_WIDTH = 1080` var dessutom en icke-standard bredd (kameran stödjer 1280 eller 1920).

### Fix
- `TARGET_FPS = 20` — satt explicit via `CAP_PROP_FPS` under kamerans max
- `TARGET_WIDTH = 1280` — korrekt 720p-bredd
- `_warmup()` — `cap.grab()` × 20 frames innan loopen, stabiliserar buffertar och exponering
- Konfigurationsordning: FOURCC → FPS → upplösning

### Ändrade filer
- `camera_module.py`

---

## 2026-05-09 — Felsökning: kameraglitch (pixelformat)

### Rotorsak
Två buggar i `_open_camera()`:
1. `cv2.CAP_MSMF` användes istället för `cv2.CAP_DSHOW` — trots att utskriften sa "DirectShow"
2. Ingen FOURCC satt → kameran valde YUY2/NV12 (raw) → OpenCV tolkade byteströmmen fel → horisontella glitch-band

### Fix
- `CAP_MSMF` → `cv2.CAP_DSHOW`, `camera_index`-parametern används korrekt
- `_configure()` sätter `MJPG` som FOURCC **innan** upplösning (ordning är kritisk — drivrutinen förhandlar upplösning per codec)
- Faktisk FOURCC läses tillbaka och loggas vid start

### Varför MJPG
MJPG är komprimerat, universellt stött och avkodas stabilt av OpenCV. Raw-format (YUY2/NV12) kräver exakt stride/byte-layout-matchning per kamera och driver — varierar och ger glitch.

### Ändrade filer
- `camera_module.py`
- `CLAUDE.md`
- `prompt.md`

---

## 2026-05-08 — Kamerarobusthet och bildkvalitet

### Vad som testades
- DirectShow (CAP_DSHOW) som primär backend — stabilare än MSMF på Windows, undviker grabFrame-fel
- Default backend som fallback om DirectShow misslyckas
- Upplösning 1280×720 via `CAP_PROP_FRAME_WIDTH/HEIGHT` med automatisk fallback till kamerans default

### Backend-strategi
Systemet försöker alltid CAP_DSHOW först. Om kameran inte öppnas via DirectShow används OpenCVs automatiska val. Vilken backend som faktiskt används skrivs ut vid start.

### Fallback-strategier
- Backend: DirectShow → Default (auto)
- Upplösning: 1280×720 → kamerans eget default (ingen krasch vid misslyckad inställning)
- Frame-läsning: upp till 5 på varandra följande misslyckanden tolereras innan avslut

### Bildförbättringar som aktiverats
- `CAP_PROP_AUTOFOCUS = 1` — autofokus (ignoreras tyst om kameran inte stödjer det)
- `CAP_PROP_AUTO_EXPOSURE = 0.25` — auto-exponering i DirectShow-konventionen
- `cv2.GaussianBlur(frame, (3, 3), 0)` — lätt brusreducering per frame

### Ändrade filer
- `camera_module.py`
- `CLAUDE.md`

### Teknisk sammanfattning
`CameraModule` fick `_open_camera()` med DirectShow/default-fallback och `_configure()` för upplösning och bildkvalitet. Felhantering i `start()` räknar misslyckade frame-läsningar och avslutar först efter 5 i rad. Debug-utskrifter loggar backend, upplösning och FPS vid start.

---

## 2026-05-08 — Fullskärm och loggningspolicy

### Syfte
Göra kamerafönstret fullskärm och införa obligatorisk loggningspolicy.

### Ändrade filer
- `camera_module.py`
- `CLAUDE.md`

### Teknisk sammanfattning
OpenCV-fönstret konfigurerades att starta i fullskärm via `namedWindow` + `setWindowProperty` innan loopen startar. En permanent loggningspolicy infördes överst i CLAUDE.md för att säkerställa full spårbarhet av framtida ändringar.

# Prompt Logg

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

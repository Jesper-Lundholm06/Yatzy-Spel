# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Arkitektur och dataflöde

Systemet är strikt modulärt. Data flödar i en riktning genom pipelinen — moduler kommunicerar inte med varandra utanför sina definierade gränssnitt.

```
camera_module
    └─► yolo_module
            ├─► dice_manager   (tärningarnas värden och låsstatus)
            └─► lockzone_module ──► dice_manager (låsning via zon)

dice_manager ──► game_engine
                    ├─► score_system   (beräknar tillgängliga poäng)
                    ├─► ai_opponent    (fattar beslut för AI-spelaren)
                    └─► popup_menu     (renderar overlay, tar emot input)

main.py — initierar alla moduler och håller igång huvudloopen
```

### Modulernas ansvarsindelning

| Modul | Ansvar | Tar emot från | Exponerar till |
|---|---|---|---|
| `camera_module` | Kameraström | — | `yolo_module` |
| `yolo_module` | YOLO-inferens, bounding boxes + värden 1–6 | `camera_module` | `dice_manager`, `lockzone_module` |
| `lockzone_module` | Avgör om tärning är i låszon | `yolo_module` | `dice_manager` |
| `dice_manager` | Tärningarnas tillstånd (värde, låst/olåst) | `yolo_module`, `lockzone_module` | `game_engine` |
| `game_engine` | Spelflöde, turordning (kast 1–3), omgångar | `dice_manager`, `popup_menu` | `score_system`, `ai_opponent`, `popup_menu` |
| `score_system` | Poängberäkning, scorekort, kategorier | `game_engine` | `game_engine`, `popup_menu` |
| `ai_opponent` | Strategibeslut (låsning + kategori) | `game_engine` | `game_engine` |
| `popup_menu` | OpenCV-overlay, musklick/tangentbord | `game_engine`, `score_system` | `game_engine` |

### Viktiga gränsdragningar

- `yolo_module` tränar **inte** modellen — den laddar en färdig modell.
- `score_system` väljer **inte** kategori — den exponerar möjliga val.
- `ai_opponent` modifierar **inte** scorekort direkt — det sker via `game_engine`.
- `game_engine` renderar **ingen** grafik — det delegeras till `popup_menu`.
- `main.py` innehåller **ingen** spellogik — den kopplar bara ihop modulerna.

## prompt.md

Filen `prompt.md` används som loggbok för Claude-sessioner. Vid varje ny session som förändrar projektet ska en ny sektion läggas till **överst** i filen med datum, syfte, skapade/ändrade filer och teknisk sammanfattning.

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

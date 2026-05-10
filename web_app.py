"""
web_app.py — Flask-server för AI Yatzy (webbversionen).

Startas med:
    python web_app.py
Öppna sedan: http://localhost:5000

Endpoints:
  GET  /             → serverar index.html (spelsidan)
  GET  /video_feed   → MJPEG-stream med YOLO-overlay från kameran
  GET  /api/state    → aktuellt speltillstånd (JSON)
  POST /api/start    → starta nytt spel  { num_players, has_bot }
  POST /api/roll     → kasta (läser kamerans live-värden)
  POST /api/toggle_lock  → låsa/låsa upp tärning  { index }
  POST /api/register → välj poängkategori  { section, key }
  POST /api/strike   → stryka kategori  { key }
  POST /api/toggle_stryk → aktivera/avbryta strykläge
  POST /api/bot_turn → kör botens hela tur (tärningar + val)
  POST /api/restart  → starta om spelet
"""

from flask import Flask, Response, render_template, jsonify, request
from camera_stream import CameraStream
from game_logic import GameLogic

app = Flask(__name__)

# Globala instanser — skapas en gång när servern startar
camera = CameraStream()
game   = GameLogic()


# ── Sidor ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Kameraström ──────────────────────────────────────────────────────────────

@app.route("/video_feed")
def video_feed():
    """MJPEG-stream: kamerabild med YOLO-bounding boxes och låszon."""
    return Response(
        camera.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# ── Spel-API ─────────────────────────────────────────────────────────────────

@app.route("/api/state")
def get_state():
    return jsonify(game.get_state())


@app.route("/api/start", methods=["POST"])
def start():
    data        = request.get_json(force=True)
    num_players = int(data.get("num_players", 1))
    has_bot     = bool(data.get("has_bot", True))
    return jsonify(game.setup(num_players, has_bot))


@app.route("/api/roll", methods=["POST"])
def roll():
    """Kasta — hämtar live-värden från kameraströmmen."""
    live = camera.get_live_values()
    return jsonify(game.roll(live))


@app.route("/api/toggle_lock", methods=["POST"])
def toggle_lock():
    data  = request.get_json(force=True)
    index = int(data.get("index", -1))
    return jsonify(game.toggle_lock(index))


@app.route("/api/register", methods=["POST"])
def register():
    data    = request.get_json(force=True)
    section = data.get("section", "")
    key     = data.get("key", "")
    return jsonify(game.register(section, key))


@app.route("/api/strike", methods=["POST"])
def strike():
    data = request.get_json(force=True)
    key  = data.get("key", "")
    return jsonify(game.strike(key))


@app.route("/api/toggle_stryk", methods=["POST"])
def toggle_stryk():
    return jsonify(game.toggle_stryk())


@app.route("/api/bot_turn", methods=["POST"])
def bot_turn():
    """
    Kör botens hela tur synkront på servern.
    Returnerar speltillståndet EFTER botens drag plus:
      bot_dice         → botens tärningar (för animation)
      bot_choice_label → vad boten valde (för animation)
    """
    return jsonify(game.bot_turn())


@app.route("/api/restart", methods=["POST"])
def restart():
    return jsonify(game.restart())


# ── Start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("AI Yatzy — webbversion")
    print("Öppna: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

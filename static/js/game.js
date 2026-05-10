/* game.js — AI Yatzy webbklient */

"use strict";

// ── Dice emoji map ────────────────────────────────────────────────────────
const DICE_EMOJI = { 1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅" };

// ── State ─────────────────────────────────────────────────────────────────
let state = null;
let strykMode = false;

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  buildDiceRow();

  document.querySelectorAll(".count-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".count-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const count = parseInt(btn.dataset.count);
      document.getElementById("bot-row").style.display = count === 1 ? "" : "none";
    });
  });

  document.getElementById("start-btn").addEventListener("click", startGame);

  document.addEventListener("keydown", e => {
    if (e.code === "Space") {
      e.preventDefault();
      if (state && state.can_roll && !(state.current_player && state.current_player.is_bot)) {
        rollDice();
      }
    }
  });
});

function buildDiceRow() {
  const row = document.getElementById("dice-row");
  row.innerHTML = "";
  for (let i = 0; i < 5; i++) {
    const box = document.createElement("div");
    box.className = "die-box";
    box.dataset.index = i;
    box.dataset.value = "-";
    box.textContent = "–";
    box.addEventListener("click", () => toggleLock(i));
    row.appendChild(box);
  }
}

// ── API helper ────────────────────────────────────────────────────────────
async function apiPost(url, data = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

// ── Game actions ──────────────────────────────────────────────────────────
async function startGame() {
  const numPlayers = parseInt(
    document.querySelector(".count-btn.active").dataset.count
  );
  const hasBot = numPlayers === 1
    ? document.getElementById("has-bot").checked
    : false;

  const data = await apiPost("/api/start", { num_players: numPlayers, has_bot: hasBot });
  document.getElementById("start-modal").classList.add("hidden");
  document.getElementById("game-container").classList.remove("hidden");
  renderState(data);
  if (data.current_player && data.current_player.is_bot) scheduleBotTurn();
}

async function rollDice() {
  if (!state || !state.can_roll) return;
  const data = await apiPost("/api/roll");
  renderState(data);
}

async function toggleLock(index) {
  if (!state || state.roll_count === 0) return;
  const data = await apiPost("/api/toggle_lock", { index });
  renderState(data);
}

async function registerScore(section, key) {
  if (!state) return;
  const data = await apiPost("/api/register", { section, key });
  renderState(data);
  if (data.game_over) showGameOver(data);
  else if (data.current_player && data.current_player.is_bot) scheduleBotTurn();
}

async function strikeScore(key) {
  if (!state) return;
  const data = await apiPost("/api/strike", { key });
  strykMode = false;
  renderState(data);
  if (data.game_over) showGameOver(data);
  else if (data.current_player && data.current_player.is_bot) scheduleBotTurn();
}

async function toggleStryk() {
  if (!state) return;
  const data = await apiPost("/api/toggle_stryk");
  strykMode = data.stryk_mode;
  renderState(data);
}

async function restart() {
  const data = await apiPost("/api/restart");
  document.getElementById("game-over-overlay").classList.add("hidden");
  strykMode = false;
  renderState(data);
  if (data.current_player && data.current_player.is_bot) scheduleBotTurn();
}

// ── Bot turn ──────────────────────────────────────────────────────────────
function scheduleBotTurn() {
  setTimeout(runBotTurn, 600);
}

async function runBotTurn() {
  // Show bot overlay
  const overlay  = document.getElementById("bot-overlay");
  const status   = document.getElementById("bot-status-text");
  const diceDisp = document.getElementById("bot-dice-display");
  const choiceDisp = document.getElementById("bot-choice-display");

  overlay.classList.remove("hidden");
  status.textContent = "BOT KASTAR";
  diceDisp.innerHTML = "";
  choiceDisp.classList.add("hidden");
  choiceDisp.textContent = "";

  const data = await apiPost("/api/bot_turn");

  // Show dice for 3s
  const dice = data.bot_dice || [];
  diceDisp.innerHTML = dice
    .map(v => `<div class="bot-die">${DICE_EMOJI[v] || v}</div>`)
    .join("");

  await sleep(3000);

  // Show choice for 2.5s
  status.textContent = "BOT VALDE";
  choiceDisp.textContent = data.bot_choice_label || "";
  choiceDisp.classList.remove("hidden");

  await sleep(2500);

  overlay.classList.add("hidden");
  renderState(data);

  if (data.game_over) {
    showGameOver(data);
  } else if (data.current_player && data.current_player.is_bot) {
    scheduleBotTurn();
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Render ────────────────────────────────────────────────────────────────
function renderState(data) {
  state = data;
  strykMode = data.stryk_mode || false;

  renderHeader(data);
  renderDice(data);
  renderRollButton(data);
  renderStrykButton(data);
  renderScorePanel(data);
  renderStatusBar(data);
}

function renderHeader(data) {
  const container = document.getElementById("header-players");
  container.innerHTML = "";
  (data.players || []).forEach((pl, i) => {
    const chip = document.createElement("div");
    chip.className = "player-chip" +
      (i === data.current_player_index ? " active" : "") +
      (pl.is_bot ? " bot" : "");
    chip.textContent = pl.name + (pl.is_bot ? " 🤖" : "");
    container.appendChild(chip);
  });
}

function renderDice(data) {
  const values  = data.dice_values  || ["-","-","-","-","-"];
  const locked  = data.locked_dice  || [false,false,false,false,false];
  const canLock = data.roll_count > 0;

  document.querySelectorAll(".die-box").forEach((box, i) => {
    const v = values[i];
    const num = parseInt(v);
    box.dataset.value = v;
    box.textContent = (!isNaN(num) && DICE_EMOJI[num]) ? DICE_EMOJI[num] : (v === "-" ? "–" : v);
    box.classList.toggle("locked", locked[i]);
    box.style.cursor = canLock ? "pointer" : "default";
  });

  const nameEl = document.getElementById("current-player-name");
  const player = data.current_player || {};
  nameEl.textContent = player.name || "–";
  nameEl.style.color = player.is_bot ? "var(--blue)" : "var(--green)";

  const badge = document.getElementById("roll-count-badge");
  badge.textContent = `Kast ${data.roll_count || 0} / ${data.max_rolls || 3}`;
}

function renderRollButton(data) {
  const btn = document.getElementById("roll-btn");
  btn.disabled = !data.can_roll || (data.current_player && data.current_player.is_bot);
}

function renderStrykButton(data) {
  const row = document.getElementById("stryk-row");
  const btn = document.getElementById("stryk-btn");
  const allRollsDone = (data.roll_count || 0) >= (data.max_rolls || 3);
  const isHuman = data.current_player && !data.current_player.is_bot;
  row.style.display = (allRollsDone && isHuman) ? "" : "none";
  btn.classList.toggle("active", strykMode);

  const panel = document.querySelector(".game-panel");
  panel.classList.toggle("stryk-active", strykMode);
}

function renderScorePanel(data) {
  const currentPlayer = (data.players || [])[data.current_player_index];
  if (!currentPlayer) return;

  renderUpperSection(currentPlayer, data);
  renderLowerSection(currentPlayer, data);

  const grandTotal = document.getElementById("grand-total");
  grandTotal.textContent = `TOTALT: ${currentPlayer.grand_total || 0} p`;
}

function renderUpperSection(player, data) {
  const container = document.getElementById("upper-rows");
  const summary   = document.getElementById("upper-summary");
  const upper     = player.upper || {};
  container.innerHTML = "";

  (upper.rows || []).forEach(row => {
    container.appendChild(buildScoreRow(row, "upper", data));
  });

  // Summary
  const progress = upper.bonus_progress || 0;
  const bonus    = upper.bonus || 0;
  const total    = upper.total || 0;
  const upperTotal = upper.upper_total || 0;

  let html = `<div class="summary-row"><span>Summa</span><span>${total} p</span></div>`;
  if (bonus > 0) {
    html += `<div class="summary-row bonus-achieved"><span>Bonus ✓</span><span>+50 p</span></div>`;
  } else {
    html += `<div class="summary-row progress"><span>Till bonus</span><span>${progress} p kvar</span></div>`;
  }
  html += `<div class="summary-row"><span>Övre totalt</span><span>${upperTotal} p</span></div>`;
  summary.innerHTML = html;
}

function renderLowerSection(player, data) {
  const container = document.getElementById("lower-rows");
  const summary   = document.getElementById("lower-summary");
  const lower     = player.lower || {};
  container.innerHTML = "";

  (lower.rows || []).forEach(row => {
    container.appendChild(buildScoreRow(row, "lower", data));
  });

  summary.innerHTML = `<div class="summary-row"><span>Nedre totalt</span><span>${lower.total || 0} p</span></div>`;
}

function buildScoreRow(row, section, data) {
  const el = document.createElement("div");
  const allRollsDone = (data.roll_count || 0) >= (data.max_rolls || 3);
  const hasRolled    = (data.roll_count || 0) > 0;
  const isBot        = data.current_player && data.current_player.is_bot;

  let classes = "score-row";
  if (section === "lower") classes += " lower-row";

  let scoreContent = "";
  let extraTag = "";

  if (row.locked) {
    classes += " locked";
    const val = row.score || 0;
    scoreContent = `<span class="score-val ${val === 0 ? 'zero' : ''}">${val} p</span>`;
    if (row.struck) extraTag = `<span class="struck-tag">STRUKEN</span>`;

  } else if (row.struck) {
    classes += " struck";
    scoreContent = `<span class="score-val zero">0 p</span>`;
    extraTag = `<span class="struck-tag">STRUKEN</span>`;

  } else if (strykMode && section === "lower") {
    classes += " stryk-selectable";
    scoreContent = `<span class="score-val zero">stryka</span>`;

  } else if (!hasRolled || (section === "lower" && row.valid === false)) {
    classes += " invalid";
    scoreContent = `<span class="score-val zero">–</span>`;

  } else {
    const val = row.score || 0;
    scoreContent = `<span class="score-val preview">${val > 0 ? '+' + val + ' p' : '0 p'}</span>`;
  }

  el.className = classes;

  const hotkey = row.hotkey ? `<span class="hotkey-tag">${row.hotkey}</span>` : "";
  el.innerHTML = `
    <span class="score-label">${row.label || ""}</span>
    ${hotkey}
    ${extraTag}
    ${scoreContent}
  `;

  // Click handler
  if (!row.locked && !row.struck && !isBot && hasRolled) {
    if (strykMode && section === "lower") {
      el.addEventListener("click", () => strikeScore(row.key));
    } else if (!strykMode && (section === "upper" || row.valid !== false)) {
      el.addEventListener("click", () => registerScore(section, row.key));
    }
  }

  return el;
}

function renderStatusBar(data) {
  const bar = document.getElementById("status-bar");
  if (!data.can_roll && data.roll_count === 0) {
    bar.textContent = `Klicka "Kasta" för att börja!`;
    return;
  }
  if (data.current_player && data.current_player.is_bot) {
    bar.textContent = "Botens tur – väntar...";
    return;
  }
  if (strykMode) {
    bar.textContent = "STRYKLÄGE — klicka en nedre kategori att stryka";
    return;
  }
  if (!data.can_roll && data.roll_count > 0) {
    bar.textContent = "Alla kast gjorda — välj kategori (eller stryka)";
    return;
  }
  if (data.roll_count > 0) {
    bar.textContent = "Låsade tärningar hålls — klicka tärning för att låsa/låsa upp";
    return;
  }
  bar.textContent = `Klicka "Kasta" för att börja!`;
}

// ── Game Over ─────────────────────────────────────────────────────────────
function showGameOver(data) {
  const overlay  = document.getElementById("game-over-overlay");
  const results  = document.getElementById("game-over-results");
  overlay.classList.remove("hidden");

  const players = data.players || [];
  const totals  = players.map(p => p.grand_total || 0);
  const maxTotal = Math.max(...totals);

  results.innerHTML = players.map((pl, i) => {
    const isWinner = totals[i] === maxTotal;
    return `
      <div class="result-row ${isWinner ? 'winner' : ''}">
        <span class="result-name">${pl.name}${pl.is_bot ? ' 🤖' : ''}</span>
        <span class="result-score">${totals[i]} p</span>
        ${isWinner ? '<span class="winner-badge">VINNARE</span>' : ''}
      </div>
    `;
  }).join("");
}

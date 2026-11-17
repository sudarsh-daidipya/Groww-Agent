let settingsInitialized = false;

const DEFAULT_MODELS = {
  gemini: "gemini-2.0-flash",
  openai: "gpt-4o-mini",
  groq: "llama-3.3-70b-versatile",
  grok: "grok-2-latest",
  deepseek: "deepseek-chat",
  claude: "claude-3-5-sonnet-latest",
  openrouter: "meta-llama/llama-3.3-70b-instruct",
  ollama: "qwen2.5:7b"
};

function updateModelLabels(provider, modelName) {
  const provUpper = (provider || "AI").toUpperCase();
  const exactModel = modelName || DEFAULT_MODELS[provider] || "AI";
  document.getElementById("active-ai-label").textContent = `${provUpper} • ${exactModel}`;
  document.getElementById("ai-box-title").textContent = exactModel;
}

function onProviderChange() {
  const prov = document.getElementById("s-provider").value;
  const defaultMod = DEFAULT_MODELS[prov] || "";
  document.getElementById("s-model").value = defaultMod;
  updateModelLabels(prov, defaultMod);
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function logoutUser() {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
}

async function loadChart() {
  const asset = document.getElementById("asset-select").value;
  try {
    const data = await fetchJSON(`/api/market/candles?asset=${asset}&days=5`);
    const c = data.candles;
    if (!c || !c.length) return;

    const times = c.map(x => x.timestamp);
    const traceCandle = {
      x: times, open: c.map(x => x.open), high: c.map(x => x.high),
      low: c.map(x => x.low), close: c.map(x => x.close),
      type: "candlestick", name: asset, xaxis: "x", yaxis: "y"
    };
    const traceST = {
      x: times, y: c.map(x => x.supertrend), mode: "lines", name: "SuperTrend",
      line: { color: "#f59e0b", width: 2 }, xaxis: "x", yaxis: "y"
    };
    const traceEMA9 = {
      x: times, y: c.map(x => x.ema_9), mode: "lines", name: "EMA 9",
      line: { color: "#38bdf8", width: 1.3 }, xaxis: "x", yaxis: "y"
    };
    const traceEMA21 = {
      x: times, y: c.map(x => x.ema_21), mode: "lines", name: "EMA 21",
      line: { color: "#a855f7", width: 1.3 }, xaxis: "x", yaxis: "y"
    };
    const traceRSI = {
      x: times, y: c.map(x => x.rsi), mode: "lines", name: "RSI (14)",
      line: { color: "#22c55e", width: 1.5 }, xaxis: "x", yaxis: "y2"
    };

    const layout = {
      paper_bgcolor: "#111827", plot_bgcolor: "#0b0f19", font: { color: "#cbd5e1" },
      margin: { l: 50, r: 20, t: 20, b: 40 },
      xaxis: { rangeslider: { visible: false }, gridcolor: "#1f2937" },
      yaxis: { domain: [0.3, 1], gridcolor: "#1f2937", title: "Price" },
      yaxis2: { domain: [0, 0.24], gridcolor: "#1f2937", title: "RSI", range: [0, 100] },
      legend: { orientation: "h", y: 1.05 }
    };

    Plotly.newPlot("chart-container", [traceCandle, traceST, traceEMA9, traceEMA21, traceRSI], layout, { responsive: true });
  } catch (e) {
    console.error("Chart error:", e);
  }
}

function updateEvaluationUI(ev) {
  if (!ev || !ev.asset) return;
  const rEl = document.getElementById("rule-sig");
  const aEl = document.getElementById("ai-sig");
  const agEl = document.getElementById("agree-sig");

  rEl.textContent = ev.rule_signal || "---";
  rEl.className = ev.rule_signal || "";

  aEl.textContent = ev.ai_signal || "---";
  aEl.className = ev.ai_signal || "";

  agEl.textContent = ev.agreed ? "✅ YES" : "❌ NO";
  agEl.style.color = ev.agreed ? "#22c55e" : "#94a3b8";

  const activeModel = document.getElementById("s-model").value.trim() || "AI";
  document.getElementById("ai-rationale").textContent = `[${ev.asset} • ${activeModel}] ${ev.rationale || "No rationale"}`;
  document.getElementById("m-spot").textContent = ev.spot ?? "--";
  document.getElementById("m-st").textContent = `${ev.supertrend ?? "--"} (${ev.trend ?? ""})`;
  document.getElementById("m-rsi").textContent = ev.rsi ?? "--";
  document.getElementById("m-conf").textContent = ev.confidence ? `${(ev.confidence * 100).toFixed(0)}%` : "--";
}

async function refreshBotStatus() {
  try {
    const st = await fetchJSON("/api/bot/status");
    document.getElementById("bot-dot").className = st.running ? "dot on" : "dot";

    const badge = document.getElementById("mode-badge");
    badge.textContent = st.dry_run ? "DRY-RUN" : "LIVE TRADING";
    badge.className = st.dry_run ? "badge dry" : "badge live";

    if (st.settings) {
      updateModelLabels(st.settings.ai_provider, st.settings.ai_model);
      document.getElementById("key-status-badge").textContent = `(Active: ${st.settings.key_status})`;
      const gBadge = document.getElementById("groww-status-badge");
      if (gBadge) gBadge.textContent = `(Active: ${st.settings.groww_status})`;
    }

    if (st.last_evaluation) updateEvaluationUI(st.last_evaluation);

    const posBox = document.getElementById("position-box");
    if (st.active_position) {
      const p = st.active_position;
      posBox.innerHTML = `
        <div style="text-align:left; font-size:13px; line-height:1.6;">
          <b>${p.symbol}</b> (${p.mode})<br/>
          Qty: <b>${p.quantity}</b> | Entry Spot: <b>${p.entry_spot}</b><br/>
          SL: <b>${p.sl}</b> | Targets: <b>${(p.targets || []).join(", ")}</b><br/>
          Time: <small>${p.entry_time}</small>
        </div>`;
    } else {
      posBox.innerHTML = "No open position";
    }

    if (st.logs && st.logs.length) {
      document.getElementById("log-box").textContent = st.logs.join("\n");
    }

    if (!settingsInitialized && st.settings) {
      document.getElementById("s-dryrun").value = String(st.dry_run);
      document.getElementById("s-asset").value = st.settings.default_asset;
      document.getElementById("s-nifty-lot").value = st.settings.nifty_lot_size;
      document.getElementById("s-crude-lot").value = st.settings.crude_lot_size;
      document.getElementById("s-max-trades").value = st.settings.max_trades_per_day;
      document.getElementById("s-st-period").value = st.settings.st_period;
      document.getElementById("s-st-mult").value = st.settings.st_multiplier;
      document.getElementById("s-rsi").value = st.settings.rsi_period;
      document.getElementById("s-provider").value = st.settings.ai_provider;
      document.getElementById("s-model").value = st.settings.ai_model;
      settingsInitialized = true;
    }
  } catch (e) {
    console.error("Status error:", e);
  }
}

async function evaluateNow() {
  const asset = document.getElementById("asset-select").value;
  const activeModel = document.getElementById("s-model").value.trim() || "AI";
  document.getElementById("ai-rationale").textContent = `Scanning market & querying ${activeModel}...`;
  const ev = await fetchJSON(`/api/signals/evaluate?asset=${asset}`, { method: "POST" });
  updateEvaluationUI(ev);
  refreshBotStatus();
  loadJournals();
}

async function startBot() {
  await fetchJSON("/api/bot/start", { method: "POST" });
  refreshBotStatus();
}

async function stopBot() {
  await fetchJSON("/api/bot/stop", { method: "POST" });
  refreshBotStatus();
}

async function killSwitch() {
  if (!confirm("Activate EMERGENCY KILL SWITCH? This will square off active position and stop the bot.")) return;
  await fetchJSON("/api/bot/kill", { method: "POST" });
  refreshBotStatus();
  loadJournals();
}

async function closePosition() {
  await fetchJSON("/api/orders/close-position", { method: "POST" });
  refreshBotStatus();
  loadJournals();
}

async function saveSettings() {
  const saveBtn = document.getElementById("save-btn");
  try {
    saveBtn.textContent = "⏳ Saving...";
    const prov = document.getElementById("s-provider").value;
    const mod = document.getElementById("s-model").value.trim();

    const payload = {
      dry_run: document.getElementById("s-dryrun").value === "true",
      default_asset: document.getElementById("s-asset").value,
      nifty_lot_size: parseInt(document.getElementById("s-nifty-lot").value) || 75,
      crude_lot_size: parseInt(document.getElementById("s-crude-lot").value) || 100,
      max_trades_per_day: parseInt(document.getElementById("s-max-trades").value) || 3,
      st_period: parseInt(document.getElementById("s-st-period").value) || 10,
      st_multiplier: parseFloat(document.getElementById("s-st-mult").value) || 3.0,
      rsi_period: parseInt(document.getElementById("s-rsi").value) || 14,
      ai_provider: prov,
      ai_model: mod,
      ai_api_key: document.getElementById("s-apikey").value.trim(),
      groww_api_key: document.getElementById("s-groww-key").value.trim(),
      groww_api_secret: document.getElementById("s-groww-secret").value.trim(),
      groww_api_token: ""
    };

    await fetchJSON("/api/bot/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    updateModelLabels(prov, mod);
    document.getElementById("s-apikey").value = "";
    document.getElementById("s-groww-key").value = "";
    document.getElementById("s-groww-secret").value = "";
    saveBtn.textContent = "✅ Saved Successfully!";
    setTimeout(() => { saveBtn.textContent = "💾 Save Keys & Bot Settings"; }, 2000);

    await refreshBotStatus();
    await loadChart();
  } catch (err) {
    saveBtn.textContent = "❌ Error Saving";
    alert("Failed to save settings: " + err.message);
    setTimeout(() => { saveBtn.textContent = "💾 Save Keys & Bot Settings"; }, 2000);
  }
}

async function loadJournals() {
  const orders = await fetchJSON("/api/orders/history");
  document.querySelector("#orders-table tbody").innerHTML = orders.map(o => `
    <tr>
      <td>${o.timestamp}</td><td>${o.order_id}</td><td><b>${o.symbol}</b></td>
      <td>${o.action}</td><td>${o.quantity}</td><td>${o.mode}</td>
      <td>${o.price}</td><td>${o.status}</td>
    </tr>`).join("");

  const sigs = await fetchJSON("/api/signals/history");
  document.querySelector("#signals-table tbody").innerHTML = sigs.map(s => `
    <tr>
      <td>${s.timestamp}</td><td>${s.asset}</td><td>${s.spot}</td>
      <td class="${s.rule_signal}">${s.rule_signal}</td>
      <td class="${s.ai_signal}">${s.ai_signal}</td>
      <td>${(s.confidence * 100).toFixed(0)}%</td><td>${s.rationale}</td>
    </tr>`).join("");
}

async function runBacktest() {
  const asset = document.getElementById("asset-select").value;
  const days = document.getElementById("bt-days").value;
  document.getElementById("bt-summary").textContent = "Running backtest...";
  const res = await fetchJSON(`/api/market/backtest?asset=${asset}&days=${days}`);
  document.getElementById("bt-summary").innerHTML =
    `Trades: <b>${res.total_trades}</b> | Win Rate: <b>${res.win_rate}%</b> | Net Spot Points: <b>${res.total_spot_points}</b>`;
  document.querySelector("#bt-table tbody").innerHTML = res.trades.map(t => `
    <tr>
      <td class="${t.type}">${t.type}</td><td>${t.entry_time}</td><td>${t.exit_time}</td>
      <td>${t.entry_spot}</td><td>${t.exit_spot}</td>
      <td style="color:${t.points >= 0 ? '#22c55e' : '#ef4444'}"><b>${t.points}</b></td>
    </tr>`).join("");
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
  event.target.classList.add("active");
  document.getElementById(`tab-${name}`).classList.add("active");
  if (name === "orders" || name === "signals") loadJournals();
}

function loadChartAndSignals() {
  loadChart();
}

window.addEventListener("DOMContentLoaded", () => {
  loadChart();
  refreshBotStatus();
  loadJournals();
  setInterval(refreshBotStatus, 5000);
});
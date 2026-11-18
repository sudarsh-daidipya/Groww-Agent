// 1. Auth Guard & Automatic Bearer Token Interceptor
if (!localStorage.getItem("algo_token")) {
  window.location.replace("/login");
}

const _origFetch = window.fetch;
window.fetch = async function (url, opts = {}) {
  const token = localStorage.getItem("algo_token");
  if (token && typeof url === "string" && url.startsWith("/api/") && !url.startsWith("/api/auth/")) {
    opts.headers = { ...(opts.headers || {}), Authorization: "Bearer " + token };
  }
  const res = await _origFetch(url, opts);
  if (res.status === 401 && typeof url === "string" && !url.startsWith("/api/auth/")) {
    localStorage.removeItem("algo_token");
    window.location.replace("/login");
  }
  return res;
};

async function logoutUser() {
  localStorage.removeItem("algo_token");
  try {
    await _origFetch("/api/auth/logout", { method: "POST" });
  } catch (e) {}
  window.location.replace("/login");
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(errText || `HTTP ${res.status}`);
  }
  return res.json();
}

// 2. Dashboard State & Chart Rendering
let currentAsset = "NIFTY";

function getSelectedAsset() {
  const el = document.getElementById("asset-select") || document.getElementById("asset");
  return el ? el.value : currentAsset;
}

async function loadCandlesAndChart() {
  const asset = getSelectedAsset();
  currentAsset = asset;
  try {
    const data = await fetchJSON(`/api/market/candles?asset=${asset}&interval=15`);
    const candles = data.candles || data;
    if (!Array.isArray(candles) || candles.length === 0) return;

    const times = candles.map(c => c.timestamp || c.time || c.datetime);
    const open = candles.map(c => c.open);
    const high = candles.map(c => c.high);
    const low = candles.map(c => c.low);
    const close = candles.map(c => c.close);

    const traces = [
      {
        x: times,
        open,
        high,
        low,
        close,
        type: "candlestick",
        name: asset,
        increasing: { line: { color: "#10b981" } },
        decreasing: { line: { color: "#ef4444" } },
      }
    ];

    if (candles[0].supertrend !== undefined) {
      traces.push({
        x: times,
        y: candles.map(c => c.supertrend),
        type: "scatter",
        mode: "lines",
        name: "SuperTrend",
        line: { color: "#3b82f6", width: 1.5 }
      });
    }

    if (candles[0].ema9 !== undefined) {
      traces.push({
        x: times,
        y: candles.map(c => c.ema9),
        type: "scatter",
        mode: "lines",
        name: "EMA 9",
        line: { color: "#f59e0b", width: 1.2 }
      });
    }

    if (candles[0].ema21 !== undefined) {
      traces.push({
        x: times,
        y: candles.map(c => c.ema21),
        type: "scatter",
        mode: "lines",
        name: "EMA 21",
        line: { color: "#a855f7", width: 1.2 }
      });
    }

    const chartDiv = document.getElementById("chart") || document.getElementById("price-chart");
    if (chartDiv && window.Plotly) {
      Plotly.newPlot(chartDiv, traces, {
        paper_bgcolor: "#0b0f19",
        plot_bgcolor: "#111827",
        font: { color: "#e2e8f0" },
        xaxis: { rangeslider: { visible: false }, gridcolor: "#1f2937" },
        yaxis: { gridcolor: "#1f2937" },
        margin: { t: 25, b: 35, l: 50, r: 20 }
      }, { responsive: true });
    }
  } catch (e) {
    console.error("Chart load error:", e);
  }
}

async function refreshStatus() {
  try {
    const status = await fetchJSON("/api/bot/status");
    const badge = document.getElementById("bot-status") || document.getElementById("status-badge");
    if (badge) {
      badge.textContent = status.running ? "RUNNING" : "STOPPED";
    }
    const logsBox = document.getElementById("logs-box") || document.getElementById("live-logs");
    if (logsBox && Array.isArray(status.logs)) {
      logsBox.innerHTML = status.logs.map(l => `<div>${l}</div>`).join("");
    }
  } catch (e) {
    console.error("Status error:", e);
  }
}

async function refreshOrders() {
  try {
    const orders = await fetchJSON("/api/orders");
    const tbody = document.getElementById("orders-body") || document.getElementById("trades-body");
    if (tbody && Array.isArray(orders)) {
      tbody.innerHTML = orders.map(o => `
        <tr>
          <td>${o.timestamp || ""}</td>
          <td>${o.asset || ""}</td>
          <td>${o.signal || o.side || ""}</td>
          <td>${o.strike || o.symbol || ""}</td>
          <td>${o.entry_price || o.price || "-"}</td>
          <td>${o.status || ""}</td>
        </tr>
      `).join("");
    }
  } catch (e) {
    console.error("Orders error:", e);
  }
}

async function scanNow() {
  const asset = getSelectedAsset();
  try {
    const res = await fetchJSON(`/api/signals/evaluate?asset=${asset}`, { method: "POST" });
    alert(`Scan Complete (${asset}): ${res.final_signal || res.signal || JSON.stringify(res)}`);
    await refreshStatus();
    await refreshOrders();
  } catch (e) {
    alert("Scan error: " + e.message);
  }
}

async function startBot() {
  await fetchJSON("/api/bot/start", { method: "POST" });
  await refreshStatus();
}

async function stopBot() {
  await fetchJSON("/api/bot/stop", { method: "POST" });
  await refreshStatus();
}

async function killSwitch() {
  if (!confirm("Activate Emergency Kill Switch & Square Off all positions?")) return;
  await fetchJSON("/api/orders/square-off", { method: "POST" });
  await stopBot();
  await refreshOrders();
}

async function saveSettings(e) {
  if (e) e.preventDefault();
  const payload = {
    groww_api_key: document.getElementById("groww-api-key")?.value || "",
    groww_api_secret: document.getElementById("groww-api-secret")?.value || "",
    ai_provider: document.getElementById("ai-provider")?.value || "gemini",
    ai_model: document.getElementById("ai-model")?.value || "gemini-2.0-flash",
    ai_api_key: document.getElementById("ai-api-key")?.value || "",
    dry_run: (document.getElementById("trade-mode")?.value || "true") === "true"
  };
  await fetchJSON("/api/bot/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  alert("Settings saved!");
  await refreshStatus();
}

document.addEventListener("DOMContentLoaded", () => {
  loadCandlesAndChart();
  refreshStatus();
  refreshOrders();
  setInterval(refreshStatus, 10000);
});

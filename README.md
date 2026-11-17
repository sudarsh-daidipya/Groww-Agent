# Groww + Multi-AI Algorithmic Trading Terminal

A locally hosted, full-stack algorithmic trading dashboard and execution bot built with **FastAPI**, **Python**, **Plotly**, and **SQLite**. Designed for intraday derivatives analysis and automated trade execution on **NIFTY 50 (NSE)** and **Crude Oil (MCX)** via the official **Groww API**, backed by dual-layer consensus combining local technical indicators with Multi-LLM signal verification.

---

## Key Features

### 1. Dual-Layer Signal Consensus Engine
* **Local Technical Indicator Engine:** Computes **SuperTrend (10, 3.0)**, **EMA 9 / EMA 21**, **RSI (14)**, and **ATR (14)** on 15-minute closed candles using `pandas` and `numpy`.
* **AI Signal Verification:** Sends structured candle snapshots to your selected LLM to validate setups (`BUY_CE`, `BUY_PE`, or `NO_TRADE`) along with confidence scores, suggested strikes, stop-loss levels, and target zones.
* **Consensus Execution:** Orders trigger only when both the deterministic Rule Engine and the AI Decision agree.

### 2. Multi-AI Provider Integration
Switch seamlessly between 8 LLM backends directly from the web dashboard without modifying code:
* **Google Gemini** (`gemini-2.0-flash`, `gemini-1.5-flash`)
* **OpenAI** (`gpt-4o-mini`, `gpt-4o`)
* **Meta Llama via Groq** (`llama-3.3-70b-versatile`)
* **xAI Grok** (`grok-2-latest`)
* **DeepSeek** (`deepseek-chat`, `deepseek-reasoner`)
* **Anthropic Claude** (`claude-3-5-sonnet-latest`)
* **OpenRouter** (Any supported model)
* **Local Ollama** (`qwen2.5:7b` or any locally hosted model)

### 3. Live Interactive Dashboard & Risk Controls
* **Interactive Plotly Charts:** Real-time 15m candlestick charts overlaid with SuperTrend, EMA 9/21, and a dedicated RSI subplot.
* **Paper & Live Trading Modes:** Toggle between **DRY-RUN (Paper Trading)** and **LIVE (Real Money)** execution at runtime.
* **Built-In Risk Management:** Enforces a maximum of **1 open position** at a time, configurable daily trade caps, automated square-off, and an **Emergency Kill Switch**.
* **Historical Rule Backtester:** Test indicator strategies across custom day ranges with instant win-rate and net spot-point metrics.
* **Persistent SQLite Journaling:** Logs every evaluated signal and executed order in `data/trades.db`.

### 4. Secure Credential Management
* Supports `.env` environment configuration as well as runtime UI credential updates (`Groww API Key/Secret` and `AI API Keys`) with masked status indicators and automatic `.env` persistence.

---

## Project Structure

```text
Groww Agent/
├── backend/
│   ├── api/
│   │   ├── auth.py            # Session authentication endpoints
│   │   ├── bot.py             # Bot lifecycle, status & runtime settings API
│   │   ├── market.py          # Historical candles & rule backtester API
│   │   ├── orders.py          # Order journal & position square-off API
│   │   └── signals.py         # Manual & automated signal evaluation API
│   ├── bot/
│   │   └── engine.py          # Background scheduler & trade execution loop
│   ├── services/
│   │   ├── gemini.py          # Universal Multi-AI REST decision engine
│   │   ├── groww_client.py    # Official GrowwAPI wrapper with simulated fallback
│   │   ├── indicators.py      # SuperTrend, EMA, RSI & ATR calculations
│   │   ├── instruments.py     # Option strike & symbol resolver
│   │   └── risk.py            # SQLite persistence & daily risk guardrails
│   ├── config.py              # Centralized settings & environment loader
│   └── main.py                # FastAPI application & static file server
├── frontend/
│   ├── src/
│   │   ├── app.js             # Dashboard logic, Plotly rendering & API client
│   │   └── style.css          # Dark-mode trading terminal UI styles
│   ├── index.html             # Main trading terminal interface
│   └── login.html             # Session-protected login page
├── data/
│   └── trades.db              # Local SQLite database (auto-created)
├── .env                       # Local secrets & API keys (ignored by Git)
├── .gitignore                 # Excludes .env, venv, cache & local DB
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation

Setup & Installation
1. Prerequisites
Python 3.10+

Active Groww Trading API credentials (GROWW_API_KEY & GROWW_API_SECRET)

At least one AI Provider API key (or a local Ollama instance)

2. Clone & Create Virtual Environment
git clone [https://github.com/](https://github.com/)<your-username>/<your-repo-name>.git
cd "Groww Agent"

python -m venv venv
# Windows (CMD):
venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
pip install itsdangerous

Create a .env file in the root directory (or configure keys directly via the Web UI after starting the server):
# Groww API Credentials
GROWW_ACCESS_TOKEN=
GROWW_API_KEY=your_groww_api_key_here
GROWW_API_SECRET=your_groww_api_secret_here

# Active AI Provider & Model
AI_PROVIDER=gemini
AI_MODEL=gemini-2.0-flash
AI_API_KEY= (you can continue with the others API Keys as well.
GEMINI_API_KEY=your_gemini_api_key_here

# Optional Multi-AI Keys
OPENAI_API_KEY=
GROQ_API_KEY=
GROK_API_KEY=
DEEPSEEK_API_KEY=
CLAUDE_API_KEY=
OPENROUTER_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434/v1

# Trading & Indicator Defaults
DRY_RUN=true
DEFAULT_ASSET=NIFTY
NIFTY_LOT_SIZE=75
CRUDE_LOT_SIZE=100
MAX_TRADES_PER_DAY=3
SUPERTREND_PERIOD=10
SUPERTREND_MULTIPLIER=3.0
RSI_PERIOD=14

# Dashboard Login Credentials
APP_USERNAME=admin
APP_PASSWORD=change_this_password
APP_SECRET_KEY=replace_with_a_random_secret_string

Start the FastAPI server using Uvicorn:
python -m uvicorn backend.main:app --reload --port 8000

[http://127.0.0.1:8000](http://127.0.0.1:8000)

Groww + Multi-AI Algo Trader Terminal

An automated, multi-asset algorithmic trading dashboard built with FastAPI, Groww Trading APIs, Technical Analysis Indicators, and Multi-LLM AI Validation (Google Gemini, OpenAI, Anthropic Claude, and Groq) for NSE (NIFTY, BANKNIFTY) and MCX (CRUDEOIL, NATURALGAS) options trading.

Key Features Implemented

1. Secure Dual-Mode Authentication System

Google OAuth 2.0 Sign-In: One-click authentication via Google Identity Services (GIS) with server-side ID token verification.

Email & Password Sign In / Sign Up: Local SQLite user store (users table) secured with PBKDF2-HMAC-SHA256 salted password hashing.

Hybrid Session & Bearer Token Security: Signed timed tokens (itsdangerous) stored in localStorage with automatic Authorization: Bearer <token> request interception in app.js and SessionMiddleware fallback on FastAPI.

No-Cache Route Guards: Strict Cache-Control: no-store headers on /login and / to prevent stale redirects.

2. Multi-Asset Market Data & Technical Charting

Supported Instruments: NSE Options (NIFTY 50, BANKNIFTY) and MCX Commodity Options (CRUDE OIL, NATURAL GAS).

Interactive Plotly Candlestick Charts: Live price action overlayed with SuperTrend, EMA 9, and EMA 21 indicators.

3. Multi-AI Signal Confirmation & Bot Engine

Multi-LLM Support: Configurable AI providers (Google Gemini, OpenAI, Anthropic Claude, Groq) to validate technical setups before execution.

Execution Modes: Safe Paper Trading (Dry Run) mode for strategy testing alongside Live Trading mode.

Risk & Emergency Controls: Real-time bot status monitoring, live engine logs, trade history tracking, and a one-click Emergency Kill Switch to square off all active positions immediately.

Project Architecture

Groww Agent/
├── backend/
│   ├── api/
│   │   ├── auth.py          # Google OAuth, Email Sign In/Up, PBKDF2 hashing & token signing
│   │   ├── market.py        # Live candles & technical indicator endpoints
│   │   ├── signals.py       # AI + technical signal evaluation endpoint
│   │   ├── bot.py           # Bot start/stop, status logs & runtime configuration
│   │   └── orders.py        # Order history & emergency square-off endpoints
│   ├── bot/
│   │   └── engine.py        # Core automated trading loop & execution engine
│   ├── services/
│   │   ├── gemini.py        # Multi-AI / LLM prompt & signal validation service
│   │   ├── groww_client.py  # Groww API wrapper for market data & order placement
│   │   ├── indicators.py    # SuperTrend, EMA 9/21 & technical calculations
│   │   ├── instruments.py   # NSE & MCX option strike/contract resolver
│   │   └── risk.py          # SQLite database initialization & risk checks
│   ├── config.py            # Environment settings & IST timezone configuration
│   └── main.py              # FastAPI app, CORS, SessionMiddleware & Bearer auth guard
├── frontend/
│   ├── index.html           # Main Algo Trader Terminal dashboard UI
│   ├── login.html           # Sign In / Sign Up & Google OAuth login UI
│   └── src/
│       ├── app.js           # Auth interceptor, Plotly charts, bot controls & live polling
│       └── style.css        # Dark terminal theme styling
├── .gitignore               # Excludes .env, venv/, and local SQLite databases
└── requirements.txt         # Python dependencies


Local Setup & Run Instructions

1. Activate Virtual Environment & Install Dependencies

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt


2. Configure Environment Variables

Create a .env file in the root directory (ignored by Git):

APP_SECRET_KEY=your_random_secret_key
GOOGLE_CLIENT_ID=your_google_oauth_client_id
ALLOWED_EMAILS=your_email@gmail.com
GROWW_API_KEY=your_groww_api_key
GROWW_API_SECRET=your_groww_api_secret
GEMINI_API_KEY=your_gemini_api_key


3. Start the FastAPI Server

python -m uvicorn backend.main:app --reload --port 8000


4. Access the Terminal

Open http://127.0.0.1:8000/login in your browser.

Sign in with Google or create an account via Sign Up to access the dashboard.

Development Milestones Completed

[x] FastAPI backend structure with modular routers (auth, market, signals, bot, orders).

[x] SQLite persistence for trade logs and user accounts (data/trades.db).

[x] Google OAuth 2.0 + Email/Password authentication with Bearer token interceptor.

[x] Interactive dark-mode trading dashboard with Plotly charts, live logs, and Kill Switch.

[ ] Live market strategy backtesting & automated trailing stop-loss tuning.
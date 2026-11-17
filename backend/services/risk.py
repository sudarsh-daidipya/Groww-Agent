import sqlite3
from datetime import datetime
import requests
from backend.config import settings, DB_PATH, IST

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                asset TEXT,
                spot REAL,
                rule_signal TEXT,
                ai_signal TEXT,
                confidence REAL,
                rationale TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                order_id TEXT,
                symbol TEXT,
                action TEXT,
                quantity INTEGER,
                mode TEXT,
                price REAL,
                status TEXT
            )
        """)
        conn.commit()

def log_signal(asset: str, spot: float, rule_sig: str, ai_sig: str, conf: float, rationale: str):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO signals (timestamp, asset, spot, rule_signal, ai_signal, confidence, rationale) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"), asset, spot, rule_sig, ai_sig, conf, rationale),
        )
        conn.commit()

def log_order(order_id: str, symbol: str, action: str, qty: int, mode: str, price: float, status: str):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO orders (timestamp, order_id, symbol, action, quantity, mode, price, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"), order_id, symbol, action, qty, mode, price, status),
        )
        conn.commit()

def get_today_trade_count() -> int:
    init_db()
    today_prefix = datetime.now(IST).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE timestamp LIKE ? AND action = 'BUY'",
            (f"{today_prefix}%",),
        )
        return cur.fetchone()[0]

def can_take_new_trade(active_position: dict | None) -> tuple[bool, str]:
    if active_position is not None:
        return False, "Already in an active position (1 position at a time)."
    if get_today_trade_count() >= settings.MAX_TRADES_PER_DAY:
        return False, f"Max daily trades ({settings.MAX_TRADES_PER_DAY}) reached."
    return True, "OK"

def send_telegram_alert(message: str):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": message}, timeout=5)
    except Exception:
        pass
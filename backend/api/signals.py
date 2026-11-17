import sqlite3
from fastapi import APIRouter
from backend.config import DB_PATH
from backend.bot.engine import bot_engine
from backend.services.risk import init_db

router = APIRouter(prefix="/api/signals", tags=["Signals"])

@router.post("/evaluate")
def evaluate_now(asset: str = "NIFTY"):
    return bot_engine.step_once(asset=asset, force=True)

@router.get("/history")
def get_signal_history(limit: int = 50):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
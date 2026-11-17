import sqlite3
from fastapi import APIRouter
from backend.config import DB_PATH
from backend.bot.engine import bot_engine
from backend.services.risk import init_db

router = APIRouter(prefix="/api/orders", tags=["Orders"])

@router.get("/history")
def get_order_history(limit: int = 50):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

@router.post("/close-position")
def close_active_position():
    if not bot_engine.active_position:
        return {"status": "no_active_position"}
    bot_engine.kill_switch()
    return {"status": "position_closed"}
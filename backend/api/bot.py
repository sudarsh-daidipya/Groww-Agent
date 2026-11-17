from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import set_key
from backend.config import settings, BASE_DIR
from backend.bot.engine import bot_engine
from backend.services.groww_client import reset_groww_client

router = APIRouter(prefix="/api/bot", tags=["Bot"])
ENV_FILE = BASE_DIR / ".env"

class SettingsUpdate(BaseModel):
    dry_run: bool = True
    default_asset: str = "NIFTY"
    nifty_lot_size: int = 75
    crude_lot_size: int = 100
    max_trades_per_day: int = 3
    st_period: int = 10
    st_multiplier: float = 3.0
    rsi_period: int = 14
    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.0-flash"
    ai_api_key: str = ""
    groww_api_key: str = ""
    groww_api_secret: str = ""
    groww_api_token: str = ""

def _mask(val: str) -> str:
    if not val or "your_new" in val:
        return "NOT SET"
    return f"...{val[-4:]}" if len(val) > 4 else "SET"

@router.get("/status")
def get_status():
    active_ai_key = settings.get_active_ai_key()
    groww_ref = settings.GROWW_ACCESS_TOKEN or settings.GROWW_API_KEY
    return {
        "running": bot_engine.running,
        "dry_run": settings.DRY_RUN,
        "active_position": bot_engine.active_position,
        "last_evaluation": bot_engine.last_evaluation,
        "logs": bot_engine.logs[:50],
        "settings": {
            "default_asset": settings.DEFAULT_ASSET,
            "nifty_lot_size": settings.NIFTY_LOT_SIZE,
            "crude_lot_size": settings.CRUDE_LOT_SIZE,
            "max_trades_per_day": settings.MAX_TRADES_PER_DAY,
            "st_period": settings.ST_PERIOD,
            "st_multiplier": settings.ST_MULTIPLIER,
            "rsi_period": settings.RSI_PERIOD,
            "ai_provider": settings.AI_PROVIDER,
            "ai_model": settings.AI_MODEL,
            "key_status": _mask(active_ai_key),
            "groww_status": _mask(groww_ref),
        }
    }

@router.post("/start")
def start_bot():
    bot_engine.start()
    return {"status": "started", "running": bot_engine.running}

@router.post("/stop")
def stop_bot():
    bot_engine.stop()
    return {"status": "stopped", "running": bot_engine.running}

@router.post("/kill")
def kill_bot():
    bot_engine.kill_switch()
    return {"status": "killed", "running": bot_engine.running}

@router.post("/settings")
def update_settings(payload: SettingsUpdate):
    settings.DRY_RUN = payload.dry_run
    settings.DEFAULT_ASSET = payload.default_asset.upper()
    settings.NIFTY_LOT_SIZE = payload.nifty_lot_size
    settings.CRUDE_LOT_SIZE = payload.crude_lot_size
    settings.MAX_TRADES_PER_DAY = payload.max_trades_per_day
    settings.ST_PERIOD = payload.st_period
    settings.ST_MULTIPLIER = payload.st_multiplier
    settings.RSI_PERIOD = payload.rsi_period
    settings.AI_PROVIDER = payload.ai_provider.lower()
    settings.AI_MODEL = payload.ai_model.strip()

    # Save AI Key to memory + .env
    if payload.ai_api_key.strip():
        clean_ai_key = payload.ai_api_key.strip()
        settings.AI_API_KEY = clean_ai_key
        if settings.AI_PROVIDER == "gemini":
            settings.GEMINI_API_KEY = clean_ai_key
        try:
            set_key(str(ENV_FILE), "AI_API_KEY", clean_ai_key)
            set_key(str(ENV_FILE), f"{settings.AI_PROVIDER.upper()}_API_KEY", clean_ai_key)
        except Exception:
            pass

    # Save Groww Key & Secret to memory + .env
    groww_changed = False
    if payload.groww_api_key.strip():
        settings.GROWW_API_KEY = payload.groww_api_key.strip()
        groww_changed = True
        try:
            set_key(str(ENV_FILE), "GROWW_API_KEY", settings.GROWW_API_KEY)
        except Exception:
            pass

    if payload.groww_api_secret.strip():
        settings.GROWW_API_SECRET = payload.groww_api_secret.strip()
        groww_changed = True
        try:
            set_key(str(ENV_FILE), "GROWW_API_SECRET", settings.GROWW_API_SECRET)
        except Exception:
            pass

    if payload.groww_api_token.strip():
        settings.GROWW_ACCESS_TOKEN = payload.groww_api_token.strip()
        settings.GROWW_API_TOKEN = settings.GROWW_ACCESS_TOKEN
        groww_changed = True
        try:
            set_key(str(ENV_FILE), "GROWW_ACCESS_TOKEN", settings.GROWW_ACCESS_TOKEN)
        except Exception:
            pass

    if groww_changed:
        reset_groww_client()
        bot_engine.add_log("Groww API Key/Secret updated & saved to .env!")

    bot_engine.add_log(
        f"Settings saved: AI={settings.AI_PROVIDER.upper()} ({settings.AI_MODEL}), Key={_mask(settings.get_active_ai_key())}"
    )
    return {"status": "updated"}
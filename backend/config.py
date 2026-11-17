import os
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

IST = ZoneInfo("Asia/Kolkata")
DB_PATH = BASE_DIR / "data" / "trades.db"
LOG_DIR = BASE_DIR / "data" / "logs"

class Settings:
    # Google OAuth & Session Settings
    GOOGLE_CLIENT_ID: str = os.getenv(
        "GOOGLE_CLIENT_ID",
        "458048900570-n8u3gvfgo4pdcdomam4pt0sau6akpmoe.apps.googleusercontent.com",
    )
    ALLOWED_EMAILS: list[str] = [
        e.strip().lower() for e in os.getenv("ALLOWED_EMAILS", "").split(",") if e.strip()
    ]
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "groww_algo_super_secret_session_key_2026")

    # Groww Official Credentials
    GROWW_ACCESS_TOKEN: str = os.getenv("GROWW_ACCESS_TOKEN") or os.getenv("GROWW_API_TOKEN", "")
    GROWW_API_TOKEN: str = GROWW_ACCESS_TOKEN
    GROWW_API_KEY: str = os.getenv("GROWW_API_KEY", "")
    GROWW_API_SECRET: str = os.getenv("GROWW_API_SECRET", "")

    # Active AI Provider, Model & UI Override Key
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")
    AI_MODEL: str = os.getenv("AI_MODEL", "gemini-2.0-flash")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")

    # Provider-specific fallback keys from .env
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROK_API_KEY: str = os.getenv("GROK_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    # Trading & Indicator Parameters
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    DEFAULT_ASSET: str = os.getenv("DEFAULT_ASSET", "NIFTY")
    NIFTY_LOT_SIZE: int = int(os.getenv("NIFTY_LOT_SIZE", 75))
    CRUDE_LOT_SIZE: int = int(os.getenv("CRUDE_LOT_SIZE", 100))
    MAX_TRADES_PER_DAY: int = int(os.getenv("MAX_TRADES_PER_DAY", 3))

    ST_PERIOD: int = int(os.getenv("SUPERTREND_PERIOD", 10))
    ST_MULTIPLIER: float = float(os.getenv("SUPERTREND_MULTIPLIER", 3.0))
    RSI_PERIOD: int = int(os.getenv("RSI_PERIOD", 14))

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    def get_active_ai_key(self) -> str:
        if self.AI_API_KEY and self.AI_API_KEY.strip():
            return self.AI_API_KEY.strip()
        mapping = {
            "gemini": self.GEMINI_API_KEY,
            "openai": self.OPENAI_API_KEY,
            "groq": self.GROQ_API_KEY,
            "grok": self.GROK_API_KEY,
            "deepseek": self.DEEPSEEK_API_KEY,
            "claude": self.CLAUDE_API_KEY,
            "openrouter": self.OPENROUTER_API_KEY,
            "ollama": "ollama-local",
        }
        return mapping.get(self.AI_PROVIDER.lower(), "")

settings = Settings()
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from growwapi import GrowwAPI
from backend.config import settings, IST

load_dotenv()

_CLIENT = None
LAST_DATA_SOURCE = "LIVE"

def reset_groww_client():
    """Clears cached client when new API Key & Secret are saved from the UI."""
    global _CLIENT
    _CLIENT = None

def get_groww_client() -> GrowwAPI:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    # Official Groww Snippet Flow (checks UI settings first, then .env)
    access_token = (
        settings.GROWW_ACCESS_TOKEN.strip()
        or settings.GROWW_API_TOKEN.strip()
        or os.getenv("GROWW_ACCESS_TOKEN", "").strip()
    )

    if not access_token:
        api_key = settings.GROWW_API_KEY.strip() or os.getenv("GROWW_API_KEY", "").strip()
        secret = settings.GROWW_API_SECRET.strip() or os.getenv("GROWW_API_SECRET", "").strip()

        if not api_key or not secret or "your_new" in api_key:
            raise ValueError("Groww API credentials missing")

        access_token = GrowwAPI.get_access_token(
            api_key=api_key,
            secret=secret
        )

    groww = GrowwAPI(access_token)  # type: ignore
    _CLIENT = groww
    return _CLIENT

def _generate_fallback_candles(asset: str = "NIFTY", n_bars: int = 120) -> pd.DataFrame:
    now = datetime.now(IST).replace(second=0, microsecond=0)
    now = now - timedelta(minutes=now.minute % 15)
    timestamps = [now - timedelta(minutes=15 * i) for i in range(n_bars)][::-1]

    seed = 42 if asset.upper() == "NIFTY" else 99
    rng = np.random.default_rng(seed)
    base_price = 24850.0 if asset.upper() == "NIFTY" else 6180.0
    step_vol = 28.0 if asset.upper() == "NIFTY" else 18.0

    rows = []
    price = base_price
    for ts in timestamps:
        delta = rng.normal(0, step_vol)
        open_p = price
        close_p = round(open_p + delta, 2)
        high_p = round(max(open_p, close_p) + abs(rng.normal(0, step_vol * 0.6)), 2)
        low_p = round(min(open_p, close_p) - abs(rng.normal(0, step_vol * 0.6)), 2)
        vol = int(rng.integers(15000, 95000))
        rows.append([ts, open_p, high_p, low_p, close_p, vol])
        price = close_p

    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])

def _parse_candle_response(candles) -> pd.DataFrame:
    if not candles:
        raise ValueError("No candle data returned from Groww API.")
    df = pd.DataFrame(candles).iloc[:, :6]
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]

    if isinstance(df["timestamp"].iloc[0], (int, float, np.integer)):
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert(IST)
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    df.sort_values(by="timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def fetch_candles(asset: str = "NIFTY", days_back: int = 5, closed_only: bool = True) -> pd.DataFrame:
    global LAST_DATA_SOURCE
    try:
        client = get_groww_client()
        end_time = datetime.now(IST)
        start_time = end_time - timedelta(days=days_back)

        if asset.upper() == "NIFTY":
            res = client.get_historical_candles(
                exchange=client.EXCHANGE_NSE,
                segment=client.SEGMENT_CASH,
                groww_symbol="NSE-NIFTY",
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                candle_interval=client.CANDLE_INTERVAL_MIN_15,
            )
        else:
            res = client.get_historical_candles(
                exchange="MCX",
                segment="COMMODITY",
                groww_symbol="MCX-CRUDEOIL-FUT",
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                candle_interval=client.CANDLE_INTERVAL_MIN_15,
            )

        candles = res.get("candles", []) if isinstance(res, dict) else res
        df = _parse_candle_response(candles)
        LAST_DATA_SOURCE = "GROWW LIVE"
        return df
    except Exception as e:
        print(f"[Groww Data Notice]: {e} -> Using Simulated 15m Feed.")
        LAST_DATA_SOURCE = f"SIMULATED ({e})"
        return _generate_fallback_candles(asset=asset, n_bars=120)
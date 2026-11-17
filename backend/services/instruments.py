from datetime import datetime, timedelta
import pandas as pd
from backend.config import settings, IST
from backend.services.groww_client import get_groww_client

_INSTRUMENT_CACHE = None

def get_instrument_master() -> pd.DataFrame:
    global _INSTRUMENT_CACHE
    if _INSTRUMENT_CACHE is None:
        client = get_groww_client()
        try:
            data = client.get_all_instruments()
            _INSTRUMENT_CACHE = pd.DataFrame(data)
        except Exception:
            _INSTRUMENT_CACHE = pd.read_csv(client.INSTRUMENT_CSV_URL)
    return _INSTRUMENT_CACHE

def resolve_atm_option_symbol(spot_price: float, option_type: str, underlying: str = "NIFTY") -> tuple[str, int]:
    step = 50 if underlying.upper() == "NIFTY" else 100
    atm_strike = int(round(spot_price / float(step)) * step)
    opt_type = option_type.upper()

    try:
        df_inst = get_instrument_master()
        today_str = datetime.now(IST).strftime("%Y-%m-%d")
        target_exch = "NSE" if underlying.upper() == "NIFTY" else "MCX"
        
        mask = (
            (df_inst["exchange"].astype(str).str.upper() == target_exch) &
            (df_inst["segment"].astype(str).str.upper().isin(["FNO", "COMMODITY"])) &
            (df_inst["trading_symbol"].astype(str).str.startswith(underlying.upper())) &
            (df_inst["trading_symbol"].astype(str).str.endswith(f"{atm_strike}{opt_type}")) &
            (df_inst["expiry_date"].astype(str) >= today_str)
        )
        candidates = df_inst[mask].sort_values(by="expiry_date")
        if not candidates.empty:
            return str(candidates.iloc[0]["groww_symbol"]), atm_strike
    except Exception as e:
        print(f"[Contract Discovery Fallback]: {e}")

    # Rule-based fallback agar master table se na mile
    today = datetime.now(IST)
    days_to_thursday = (3 - today.weekday()) % 7
    expiry_dt = today + timedelta(days=days_to_thursday)
    prefix = "NSE-NIFTY" if underlying.upper() == "NIFTY" else "MCX-CRUDEOIL"
    symbol_str = f"{prefix}{expiry_dt.strftime('%y%b').upper()}{atm_strike}{opt_type}"
    return symbol_str, atm_strike

def execute_order(groww_symbol: str, underlying: str, action: str = "BUY", quantity: int = 75) -> dict:
    """Dry-run me paper order simulate karega, Live mode me Groww par bhejega."""
    now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    exchange = "NSE" if underlying.upper() == "NIFTY" else "MCX"
    segment = "FNO" if underlying.upper() == "NIFTY" else "COMMODITY"

    if settings.DRY_RUN:
        return {
            "status": "DRY_RUN_FILLED",
            "order_id": f"PAPER-{int(datetime.now(IST).timestamp())}",
            "symbol": groww_symbol,
            "exchange": exchange,
            "segment": segment,
            "action": action,
            "quantity": quantity,
            "timestamp": now_str,
        }

    client = get_groww_client()
    receipt = client.place_order(
        exchange=exchange,
        segment=segment,
        trading_symbol=groww_symbol,
        transaction_type=action.upper(),
        order_type="MARKET",
        product="INTRADAY",
        quantity=quantity,
    )
    return {
        "status": "LIVE_SUBMITTED",
        "order_id": str(receipt),
        "symbol": groww_symbol,
        "exchange": exchange,
        "segment": segment,
        "action": action,
        "quantity": quantity,
        "timestamp": now_str,
    }
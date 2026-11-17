from fastapi import APIRouter, HTTPException
import backend.services.groww_client as gc
from backend.services.indicators import add_technical_indicators, evaluate_rule_signal

router = APIRouter(prefix="/api/market", tags=["Market"])

@router.get("/candles")
def get_candles(asset: str = "NIFTY", days: int = 5):
    try:
        df = gc.fetch_candles(asset=asset, days_back=days, closed_only=False)
        df = add_technical_indicators(df).dropna(subset=["supertrend"]).tail(120)
        df["timestamp"] = df["timestamp"].astype(str)
        return {
            "asset": asset,
            "source": gc.LAST_DATA_SOURCE,
            "candles": df.to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backtest")
def run_backtest(asset: str = "NIFTY", days: int = 10):
    try:
        df = gc.fetch_candles(asset=asset, days_back=days, closed_only=True)
        df = add_technical_indicators(df).dropna().reset_index(drop=True)

        trades = []
        in_pos = None

        for i in range(len(df) - 1):
            row = df.iloc[i]
            sig = evaluate_rule_signal(row)

            if in_pos is None and sig in ["BUY_CE", "BUY_PE"]:
                in_pos = {"type": sig, "entry_price": float(row["close"]), "entry_time": str(row["timestamp"]), "idx": i}
            elif in_pos is not None:
                bars_held = i - in_pos["idx"]
                exit_cond = (
                    (in_pos["type"] == "BUY_CE" and row["close"] < row["ema_9"]) or
                    (in_pos["type"] == "BUY_PE" and row["close"] > row["ema_9"]) or
                    bars_held >= 6
                )
                if exit_cond:
                    exit_p = float(row["close"])
                    pts = (exit_p - in_pos["entry_price"]) if in_pos["type"] == "BUY_CE" else (in_pos["entry_price"] - exit_p)
                    trades.append({
                        "type": in_pos["type"],
                        "entry_time": in_pos["entry_time"],
                        "exit_time": str(row["timestamp"]),
                        "entry_spot": round(in_pos["entry_price"], 2),
                        "exit_spot": round(exit_p, 2),
                        "points": round(pts, 2),
                    })
                    in_pos = None

        wins = [t for t in trades if t["points"] > 0]
        total_pts = round(sum(t["points"] for t in trades), 2)
        win_rate = round((len(wins) / len(trades)) * 100, 1) if trades else 0.0

        return {
            "asset": asset,
            "days": days,
            "total_trades": len(trades),
            "win_rate": win_rate,
            "total_spot_points": total_pts,
            "trades": trades[-20:],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
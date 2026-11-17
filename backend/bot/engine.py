import threading
import time
from datetime import datetime
from backend.config import settings, IST
from backend.services.groww_client import fetch_candles
from backend.services.indicators import add_technical_indicators, evaluate_rule_signal
from backend.services.gemini import get_gemini_option_decision
from backend.services.instruments import resolve_atm_option_symbol, execute_order
from backend.services.risk import log_signal, log_order, can_take_new_trade, send_telegram_alert

class BotEngine:
    def __init__(self):
        self.running = False
        self.thread = None
        self.active_position = None  # Ek baar me sirf 1 active position
        self.last_candle_ts = None
        self.last_evaluation = {}
        self.logs = []

    def add_log(self, msg: str):
        ts = datetime.now(IST).strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        print(entry)
        self.logs.insert(0, entry)
        self.logs = self.logs[:150]

    def start(self):
        if self.running:
            return
        self.running = True
        self.add_log(f"Bot STARTED (Mode: {'DRY-RUN' if settings.DRY_RUN else 'LIVE'})")
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.add_log("Bot STOPPED.")

    def kill_switch(self):
        self.add_log("EMERGENCY KILL SWITCH ACTIVATED!")
        if self.active_position:
            pos = self.active_position
            res = execute_order(pos["symbol"], pos["underlying"], action="SELL", quantity=pos["quantity"])
            log_order(
                res["order_id"], pos["symbol"], "SELL", pos["quantity"],
                "DRY_RUN" if settings.DRY_RUN else "LIVE", pos.get("entry_spot", 0.0), res["status"]
            )
            self.add_log(f"Closed active position: {pos['symbol']} ({res['status']})")
            send_telegram_alert(f"🚨 Kill Switch: Closed {pos['symbol']}")
            self.active_position = None
        self.stop()

    def step_once(self, asset: str = "NIFTY", force: bool = False):
        df = fetch_candles(asset=asset, days_back=5, closed_only=True)
        df = add_technical_indicators(df)
        latest = df.iloc[-1]
        candle_ts = str(latest["timestamp"])

        rule_sig = evaluate_rule_signal(latest)
        ai_res = get_gemini_option_decision(df, asset_name=asset)
        ai_sig = ai_res.get("decision", "NO_TRADE")
        conf = float(ai_res.get("confidence_score", 0.0))
        rationale = ai_res.get("rationale", "")

        # Fallback to CRUDEOIL agar NIFTY me NO_TRADE hai
        if asset == "NIFTY" and rule_sig == "NO_TRADE" and ai_sig == "NO_TRADE":
            try:
                self.add_log("NIFTY is NO_TRADE. Checking CRUDEOIL fallback...")
                df_crude = add_technical_indicators(fetch_candles("CRUDEOIL", days_back=4, closed_only=True))
                latest_c = df_crude.iloc[-1]
                r_c = evaluate_rule_signal(latest_c)
                ai_c = get_gemini_option_decision(df_crude, asset_name="CRUDEOIL")
                if r_c != "NO_TRADE" or ai_c.get("decision") != "NO_TRADE":
                    asset = "CRUDEOIL"
                    latest = latest_c
                    candle_ts = str(latest["timestamp"])
                    rule_sig = r_c
                    ai_res = ai_c
                    ai_sig = ai_c.get("decision", "NO_TRADE")
                    conf = float(ai_c.get("confidence_score", 0.0))
                    rationale = ai_c.get("rationale", "")
            except Exception as e:
                self.add_log(f"Crude fallback skipped: {e}")

        agreed = (rule_sig == ai_sig) and (ai_sig in ["BUY_CE", "BUY_PE"])

        self.last_evaluation = {
            "timestamp": candle_ts,
            "asset": asset,
            "spot": round(float(latest["close"]), 2),
            "supertrend": round(float(latest["supertrend"]), 2),
            "trend": latest["trend_direction"],
            "rsi": round(float(latest["rsi"]), 2),
            "ema_9": round(float(latest["ema_9"]), 2),
            "ema_21": round(float(latest["ema_21"]), 2),
            "rule_signal": rule_sig,
            "ai_signal": ai_sig,
            "agreed": agreed,
            "confidence": conf,
            "rationale": rationale,
            "sl": ai_res.get("recommended_stop_loss", 0.0),
            "targets": ai_res.get("target_levels", []),
        }

        if candle_ts != self.last_candle_ts or force:
            self.last_candle_ts = candle_ts
            log_signal(asset, float(latest["close"]), rule_sig, ai_sig, conf, rationale)
            self.add_log(f"{asset} [{candle_ts}] Spot:{latest['close']:.1f} | Rule:{rule_sig} | AI:{ai_sig}")

            if agreed:
                allowed, reason = can_take_new_trade(self.active_position)
                if allowed:
                    opt_type = "CE" if ai_sig == "BUY_CE" else "PE"
                    sym, strike = resolve_atm_option_symbol(float(latest["close"]), opt_type, asset)
                    qty = settings.NIFTY_LOT_SIZE if asset == "NIFTY" else settings.CRUDE_LOT_SIZE
                    order_res = execute_order(sym, asset, "BUY", qty)

                    mode_str = "DRY_RUN" if settings.DRY_RUN else "LIVE"
                    log_order(order_res["order_id"], sym, "BUY", qty, mode_str, float(latest["close"]), order_res["status"])

                    self.active_position = {
                        "symbol": sym,
                        "underlying": asset,
                        "strike": strike,
                        "type": opt_type,
                        "quantity": qty,
                        "entry_spot": round(float(latest["close"]), 2),
                        "sl": ai_res.get("recommended_stop_loss", 0.0),
                        "targets": ai_res.get("target_levels", []),
                        "entry_time": order_res["timestamp"],
                        "mode": mode_str,
                    }
                    msg = f"✅ {mode_str} ORDER: {sym} (Qty {qty}) @ Spot {latest['close']:.2f}"
                    self.add_log(msg)
                    send_telegram_alert(msg)
                else:
                    self.add_log(f"Trade skipped: {reason}")

        return self.last_evaluation

    def _run_loop(self):
        while self.running:
            try:
                self.step_once(settings.DEFAULT_ASSET)
            except Exception as e:
                self.add_log(f"Engine Error: {e}")
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)

bot_engine = BotEngine()
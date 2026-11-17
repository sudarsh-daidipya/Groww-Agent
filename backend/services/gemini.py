import json
import re
import requests
import pandas as pd
from backend.config import settings

OPENAI_COMPAT_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "grok": "https://api.x.ai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}

def _extract_json(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    return json.loads(match.group(0) if match else cleaned)

def get_gemini_option_decision(df: pd.DataFrame, asset_name: str = "NIFTY 50") -> dict:
    provider = settings.AI_PROVIDER.lower()
    user_model = settings.AI_MODEL.strip()
    api_key = settings.get_active_ai_key()

    if provider != "ollama" and (not api_key or "your_new" in api_key):
        return {
            "asset": asset_name,
            "model_used": user_model,
            "decision": "NO_TRADE",
            "confidence_score": 0.0,
            "suggested_strike": "N/A",
            "recommended_stop_loss": 0.0,
            "target_levels": [0.0, 0.0],
            "rationale": f"API Key missing for '{provider.upper()}'. Paste it in UI Settings."
        }

    recent = df.tail(5)[
        ["timestamp", "open", "high", "low", "close", "volume",
         "supertrend", "trend_direction", "rsi", "ema_9", "ema_21", "atr_14"]
    ].copy()
    recent["timestamp"] = recent["timestamp"].astype(str)
    snapshot = recent.to_dict(orient="records")
    strike_hint = "24900 CE" if "NIFTY" in asset_name.upper() else "6200 CE"

    prompt = f"""You are an intraday derivatives analyst for {asset_name}.
Candles (last 5 closed 15m):
{json.dumps(snapshot, indent=2)}

Execution Rules:
1. BUY_CE if: Close > SuperTrend AND Close > EMA 9 AND EMA 9 >= EMA 21 AND RSI between 52 and 70.
2. BUY_PE if: Close < SuperTrend AND Close < EMA 9 AND EMA 9 <= EMA 21 AND RSI between 30 and 48.
3. NO_TRADE otherwise.

Return ONLY valid JSON:
{{
  "asset": "{asset_name}",
  "decision": "BUY_CE" | "BUY_PE" | "NO_TRADE",
  "confidence_score": 0.0,
  "suggested_strike": "{strike_hint}",
  "recommended_stop_loss": 0.0,
  "target_levels": [0.0, 0.0],
  "rationale": "concise 1-line technical reason"
}}"""

    try:
        # 1. Google Gemini REST API (Uses your chosen model first; never overwrites settings.AI_MODEL)
        if provider == "gemini":
            candidates = []
            for m in [user_model, "gemini-3.5-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"]:
                if m and m not in candidates:
                    candidates.append(m)

            headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1, "maxOutputTokens": 300},
            }

            last_err = ""
            for m_name in candidates:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent"
                r = requests.post(url, headers=headers, json=payload, timeout=20)
                if r.status_code == 404:
                    last_err = f"Model '{m_name}' not found (404)"
                    continue
                if not r.ok:
                    try:
                        err_msg = r.json().get("error", {}).get("message", r.text[:120])
                    except Exception:
                        err_msg = f"HTTP {r.status_code}"
                    raise RuntimeError(f"Gemini API error ({r.status_code}): {err_msg}")

                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                res_obj = _extract_json(text)
                res_obj["model_used"] = user_model
                return res_obj

            raise RuntimeError(f"Model returned 404 ({last_err}).")

        # 2. Anthropic Claude API
        elif provider == "claude":
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": user_model,
                "max_tokens": 300,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}],
            }
            r = requests.post(url, headers=headers, json=payload, timeout=25)
            r.raise_for_status()
            text = r.json()["content"][0]["text"]
            res_obj = _extract_json(text)
            res_obj["model_used"] = user_model
            return res_obj

        # 3. OpenAI, Groq (Meta Llama), xAI Grok, DeepSeek, OpenRouter, or Local Ollama
        else:
            url = (
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/chat/completions"
                if provider == "ollama"
                else OPENAI_COMPAT_URLS.get(provider, OPENAI_COMPAT_URLS["openai"])
            )
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": user_model,
                "messages": [
                    {"role": "system", "content": "Always respond with a raw JSON object only."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 300,
            }
            r = requests.post(url, headers=headers, json=payload, timeout=25)
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
            res_obj = _extract_json(text)
            res_obj["model_used"] = user_model
            return res_obj

    except Exception as e:
        return {
            "asset": asset_name,
            "model_used": user_model,
            "decision": "NO_TRADE",
            "confidence_score": 0.0,
            "suggested_strike": "N/A",
            "recommended_stop_loss": 0.0,
            "target_levels": [0.0, 0.0],
            "rationale": f"{user_model} Notice: {str(e)}"
        }
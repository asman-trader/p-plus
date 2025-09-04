# routes/analysis_routes.py
from flask import Blueprint, jsonify, request
import time, math
import requests

analysis_bp = Blueprint("analysis", __name__)

# ---------------------------
# تنظیمات و کش سبک
# ---------------------------
BINANCE_API = "https://api.binance.com/api/v3/klines"
CACHE_TTL = 15  # ثانیه برای هر تایم‌فریم
_cache = {}     # { (symbol, interval, limit): {"t": ts, "rows": [[...], ...]} }

# نگاشت تایم‌فریم‌ها
VALID_INTERVALS = {"1m","5m","15m","1h","4h"}
DEFAULT_INTERVALS = ["5m","15m","1h"]
DEFAULT_LIMIT = 200  # برای EMA/RSI کافی است

def _pair(symbol: str) -> str:
    # ما در فرانت BTC/USDT داریم → برای بایننس "BTCUSDT"
    return f"{symbol.upper()}USDT"

def _get_klines(symbol: str, interval: str, limit: int):
    key = (symbol, interval, limit)
    ent = _cache.get(key)
    now = time.time()
    if ent and now - ent["t"] <= CACHE_TTL:
        return ent["rows"]

    params = {"symbol": _pair(symbol), "interval": interval, "limit": limit}
    r = requests.get(BINANCE_API, params=params, timeout=6)
    r.raise_for_status()
    rows = r.json()  # هر ردیف: [openTime, open, high, low, close, volume, ...]
    _cache[key] = {"t": now, "rows": rows}
    return rows

# ---------------------------
# اندیکاتورها (بدون وابستگی)
# ---------------------------
def ema(series, period):
    if not series or period <= 0 or len(series) < period:
        return []
    k = 2 / (period + 1)
    out = []
    # EMA اولیه = میانگین ساده  period  کندل اول
    sma = sum(series[:period]) / period
    out.extend([None]*(period-1))
    out.append(sma)
    for i in range(period, len(series)):
        out.append(series[i]*k + out[-1]*(1-k))
    return out

def rsi(series, period=14):
    if not series or len(series) < period + 1:
        return []
    gains, losses = [], []
    for i in range(1, len(series)):
        ch = series[i] - series[i-1]
        gains.append(max(ch, 0.0))
        losses.append(abs(min(ch, 0.0)))
    # میانگین نمایی برای RS/RSi (روش Wilder)
    def _ewma(x, p):
        k = 1 / p
        out = [sum(x[:p]) / p]
        for i in range(p, len(x)):
            out.append(out[-1]*(1-k) + x[i]*k)
        return out
    avg_gain = _ewma(gains, period)
    avg_loss = _ewma(losses, period)
    # هم‌ترازسازی طول‌ها
    rs = []
    for g, l in zip(avg_gain, avg_loss):
        if l == 0:
            rs.append(math.inf)
        else:
            rs.append(g / l)
    rsi_vals = [100 - (100 / (1 + v)) for v in rs]
    # پر کردن None برای ابتدای سری تا هم‌طول close‌ها شود
    pad_len = len(series) - len(rsi_vals) - 1
    return [None]*max(pad_len, 0) + rsi_vals

# ---------------------------
# سیگنال‌ساز ساده روی چندبازه
# ---------------------------
def timeframe_signal(close, ema20, ema50, rsi14):
    """
    Rule-based:
      - Buy: close > EMA20 > EMA50 و RSI بین 50 و 70
      - Sell: close < EMA20 < EMA50 یا RSI < 45 یا RSI > 80
      - Neutral: غیر از این‌ها
    """
    if not close or not ema20 or not ema50 or not rsi14:
        return "neutral"
    c, e20, e50, r = close[-1], ema20[-1], ema50[-1], rsi14[-1]
    if e20 is None or e50 is None or r is None:
        return "neutral"
    if (c > e20 > e50) and (50 <= r <= 70):
        return "buy"
    if (c < e20 < e50) or (r < 45) or (r > 80):
        return "sell"
    return "neutral"

def confidence(scores):
    """
    امتیاز اعتماد 0..100
    buy=+1, neutral=0, sell=-1 → مقیاس 0..100
    """
    if not scores:
        return 0
    s = 0
    for x in scores:
        if x == "buy": s += 1
        elif x == "sell": s -= 1
    # نگاشت به 0..100 (حداکثر |scores| = n → +n ↦ 100, -n ↦ 0, 0 ↦ 50)
    n = len(scores)
    return round(((s + n) / (2*n)) * 100)

# ---------------------------
# API
# ---------------------------
@analysis_bp.get("/analysis/<symbol>")
def analyze(symbol):
    intervals_q = request.args.get("intervals")
    limit_q = request.args.get("limit", type=int) or DEFAULT_LIMIT

    intervals = [x.strip() for x in (intervals_q.split(",") if intervals_q else DEFAULT_INTERVALS)]
    intervals = [i for i in intervals if i in VALID_INTERVALS]
    if not intervals:
        intervals = DEFAULT_INTERVALS

    result = {"symbol": symbol.upper(), "timeframes": {}, "confidence": 0}
    votes = []

    for iv in intervals:
        try:
            rows = _get_klines(symbol, iv, limit_q)
            closes = [float(r[4]) for r in rows]
            e20 = ema(closes, 20)
            e50 = ema(closes, 50)
            r14 = rsi(closes, 14)
            sig = timeframe_signal(closes, e20, e50, r14)
            votes.append(sig)

            # آخرین مقادیر برای نمایش
            last = {
                "close": round(closes[-1], 6) if closes else None,
                "ema20": round(e20[-1], 6) if e20 and e20[-1] is not None else None,
                "ema50": round(e50[-1], 6) if e50 and e50[-1] is not None else None,
                "rsi14": round(r14[-1], 2) if r14 and r14[-1] is not None else None,
                "signal": sig
            }
            result["timeframes"][iv] = last
        except Exception as e:
            result["timeframes"][iv] = {"error": str(e)}

    result["confidence"] = confidence(votes)
    return jsonify(result)

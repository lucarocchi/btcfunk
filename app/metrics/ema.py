import sqlite3
from datetime import datetime, timezone

DB_PATH = "mvrv_cache.sqlite"


def _calc_ema(closes, period):
    if len(closes) < period:
        return [None] * len(closes)
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    ema = sum(closes[:period]) / period
    result.append(round(ema, 2))
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
        result.append(round(ema, 2))
    return result


def get_ema(tf: int = 1440, limit: int = 500):
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT ts, close FROM ohlc WHERE tf = ? ORDER BY ts DESC LIMIT ?",
        (tf, limit + 200)
    ).fetchall()
    con.close()

    if not rows:
        return {"error": "no data", "tf": tf}

    rows       = sorted(rows, key=lambda x: x[0])
    timestamps = [r[0] for r in rows]
    closes     = [r[1] for r in rows]

    ema20  = _calc_ema(closes, 20)
    ema50  = _calc_ema(closes, 50)
    ema200 = _calc_ema(closes, 200)

    fmt    = "%Y-%m-%d" if tf >= 1440 else "%m-%d %H:%M"
    labels = [datetime.fromtimestamp(ts, tz=timezone.utc).strftime(fmt) for ts in timestamps]

    current_price = closes[-1] if closes else None
    e20 = ema20[-1]; e50 = ema50[-1]; e200 = ema200[-1]

    if current_price and e200:
        if current_price > e200 and e50 and e50 > e200: signal = 'bullish'
        elif current_price < e200 and e50 and e50 < e200: signal = 'bearish'
        else: signal = 'mixed'
    else:
        signal = 'neutral'

    return {
        "labels":     labels[-limit:],
        "ema20":      ema20[-limit:],
        "ema50":      ema50[-limit:],
        "ema200":     ema200[-limit:],
        "ema20_val":  e20,
        "ema50_val":  e50,
        "ema200_val": e200,
        "signal":     signal,
        "tf":         tf,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

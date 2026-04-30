import sqlite3
from datetime import datetime, timezone

DB_PATH = "mvrv_cache.sqlite"


def _calc_rsi(closes, period=14):
    if len(closes) < period + 2:
        return []
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains  = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi = []
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(round(100 - (100 / (1 + rs)), 2))
    return rsi


def get_rsi(tf: int = 1440, period: int = 14, limit: int = 500):
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT ts, close FROM ohlc WHERE tf = ? ORDER BY ts DESC LIMIT ?",
        (tf, limit + period + 2)
    ).fetchall()
    con.close()

    if not rows:
        return {"error": "no data", "tf": tf}

    rows       = sorted(rows, key=lambda x: x[0])
    timestamps = [r[0] for r in rows]
    closes     = [r[1] for r in rows]

    rsi_values = _calc_rsi(closes, period)
    fmt    = "%Y-%m-%d" if tf >= 1440 else "%m-%d %H:%M"
    labels = [datetime.fromtimestamp(ts, tz=timezone.utc).strftime(fmt)
              for ts in timestamps[period+1:]]

    current = rsi_values[-1] if rsi_values else None
    if current is None:   signal = 'neutral'
    elif current > 70:    signal = 'overbought'
    elif current < 30:    signal = 'oversold'
    elif current >= 50:   signal = 'bullish'
    else:                 signal = 'bearish'

    return {
        "labels":     labels[-limit:],
        "rsi":        rsi_values[-limit:],
        "current":    current,
        "signal":     signal,
        "tf":         tf,
        "period":     period,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

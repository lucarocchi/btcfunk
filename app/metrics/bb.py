import sqlite3
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"


def _calc_bb(closes, period=20, std_dev=2):
    upper, mid, lower = [], [], []
    for i in range(len(closes)):
        if i < period - 1:
            upper.append(None); mid.append(None); lower.append(None)
        else:
            window = closes[i - period + 1:i + 1]
            mean = sum(window) / period
            std  = (sum((x - mean)**2 for x in window) / period) ** 0.5
            mid.append(round(mean, 2))
            upper.append(round(mean + std_dev * std, 2))
            lower.append(round(mean - std_dev * std, 2))
    return upper, mid, lower


def get_bb(tf: int = 1440, period: int = 20):
    limit = 9999 if tf >= 1440 else 720
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT ts, close FROM ohlc WHERE tf = ? ORDER BY ts DESC LIMIT ?",
        (tf, limit + period)
    ).fetchall()
    con.close()

    if not rows:
        return {"error": "no data", "tf": tf}

    rows       = sorted(rows, key=lambda x: x[0])
    timestamps = [r[0] for r in rows]
    closes     = [r[1] for r in rows]

    upper, mid, lower = _calc_bb(closes, period)
    bandwidth = [round((u - l) / m * 100, 2) if u and l and m else None
                 for u, l, m in zip(upper, lower, mid)]

    fmt    = "%Y-%m-%d" if tf >= 1440 else "%m-%d %H:%M"
    labels = [datetime.fromtimestamp(ts, tz=timezone.utc).strftime(fmt) for ts in timestamps]

    cp = closes[-1] if closes else None
    u  = upper[-1];  lo = lower[-1]; bw = bandwidth[-1]

    if cp and u and lo:
        pct = (cp - lo) / (u - lo) * 100
        if pct > 95:   signal = 'overbought'
        elif pct < 5:  signal = 'oversold'
        else:          signal = 'neutral'
    else:
        signal = 'neutral'

    return {
        "labels":        labels[-limit:],
        "bb_upper":      upper[-limit:],
        "bb_mid":        mid[-limit:],
        "bb_lower":      lower[-limit:],
        "bandwidth":     bandwidth[-limit:],
        "upper_val":     u,
        "lower_val":     lo,
        "bandwidth_val": bw,
        "signal":        signal,
        "tf":            tf,
        "period":        period,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }

import sqlite3
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"


def get_price(tf: int = 1440):
    limit = 9999 if tf >= 1440 else 720
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT ts, open, high, low, close, vol FROM ohlc WHERE tf = ? ORDER BY ts DESC LIMIT ?",
        (tf, limit)
    ).fetchall()
    con.close()

    if not rows:
        return {"error": "no data", "tf": tf}

    rows = sorted(rows, key=lambda x: x[0])
    timestamps = [r[0] for r in rows]
    closes = [r[4] for r in rows]
    vols   = [r[5] for r in rows]

    fmt    = "%Y-%m-%d" if tf >= 1440 else "%m-%d %H:%M"
    labels = [datetime.fromtimestamp(ts, tz=timezone.utc).strftime(fmt) for ts in timestamps]

    return {
        "labels":         labels,
        "open":           [r[1] for r in rows],
        "high":           [r[2] for r in rows],
        "low":            [r[3] for r in rows],
        "close":          closes,
        "volume":         vols,
        "current_price":  closes[-1] if closes else None,
        "current_volume": vols[-2] if len(vols) >= 2 else vols[-1] if vols else None,
        "tf":             tf,
        "updated_at":     datetime.now(timezone.utc).isoformat(),
    }

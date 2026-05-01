import sqlite3
import requests
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"

COINBASE_URL = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
BINANCE_URL  = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
HEADERS      = {"User-Agent": "btcfunk/1.0"}


def _live_premium():
    try:
        cb = float(requests.get(COINBASE_URL, headers=HEADERS, timeout=8).json()["data"]["amount"])
        bn = float(requests.get(BINANCE_URL,  headers=HEADERS, timeout=8).json()["price"])
        return round((cb - bn) / bn * 100, 4), cb, bn
    except Exception:
        return None, None, None


def get_coinbase_premium():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT day, premium_pct FROM coinbase_premium_daily
        WHERE day >= date('now', '-365 days')
        ORDER BY day
    """).fetchall()
    con.close()

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]

    live_pct, cb_price, bn_price = _live_premium()
    current = live_pct if live_pct is not None else (values[-1] if values else None)

    return {
        "labels":      labels,
        "values":      values,
        "current":     current,
        "coinbase":    cb_price,
        "binance":     bn_price,
        "updated_at":  datetime.now(timezone.utc).isoformat(),
    }

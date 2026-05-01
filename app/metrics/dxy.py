import sqlite3
import json
import requests
from datetime import datetime, timezone, timedelta

DB_PATH = "btcfunk.sqlite"
CACHE_TTL_HOURS = 24


def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS cache (
        key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
    )""")
    con.commit()
    con.close()


def _get_cached(key):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT value, updated_at FROM cache WHERE key=?", (key,)).fetchone()
    con.close()
    if not row:
        return None
    updated = datetime.fromisoformat(row[1])
    if datetime.now(timezone.utc) - updated > timedelta(hours=CACHE_TTL_HOURS):
        return None
    return json.loads(row[0])


def _set_cached(key, value):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT OR REPLACE INTO cache (key, value, updated_at) VALUES (?, ?, ?)",
        (key, json.dumps(value), datetime.now(timezone.utc).isoformat())
    )
    con.commit()
    con.close()


def _fetch_yahoo(ticker):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "range": "5y"}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; btcfunk/1.0)"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    labels, values = [], []
    for ts, cl in zip(timestamps, closes):
        if cl is None:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        labels.append(dt.strftime("%Y-%m-%d"))
        values.append(round(cl, 2))
    return labels, values


def get_dxy():
    _init_db()
    cached = _get_cached('dxy')
    if cached:
        return cached

    dxy_labels, dxy_values = _fetch_yahoo("DX-Y.NYB")
    btc_labels, btc_values = _fetch_yahoo("BTC-USD")

    out = {
        "labels": dxy_labels,
        "values": dxy_values,
        "current": dxy_values[-1] if dxy_values else None,
        "btc_labels": btc_labels,
        "btc_close": btc_values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _set_cached('dxy', out)
    return out

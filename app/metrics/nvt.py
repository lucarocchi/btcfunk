import sqlite3, json, requests
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery

DB_PATH = "mvrv_cache.sqlite"
CACHE_TTL_HOURS = 24
HISTORY_DAYS = 430  # extra days for 28d MA warmup

_bq_client = None

def _get_bq():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client()
    return _bq_client

def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS nvt_daily (day TEXT PRIMARY KEY, btc_volume REAL)")
    con.commit()
    return con

def _cache_get(con, key):
    row = con.execute("SELECT value, updated_at FROM cache WHERE key=?", (key,)).fetchone()
    if not row: return None
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(row[1])).total_seconds() / 3600
    return json.loads(row[0]) if age < CACHE_TTL_HOURS else None

def _cache_set(con, key, value):
    con.execute("INSERT OR REPLACE INTO cache (key,value,updated_at) VALUES (?,?,?)",
                (key, json.dumps(value), datetime.now(timezone.utc).isoformat()))
    con.commit()

def _fetch_volume(since_day):
    query = f"""
        SELECT DATE(block_timestamp) AS day, SUM(value) / 1e8 AS btc_volume
        FROM `bigquery-public-data.crypto_bitcoin.outputs`
        WHERE DATE(block_timestamp) >= '{since_day}' AND value > 0
        GROUP BY day ORDER BY day
    """
    result = _get_bq().query(query).result()
    return [(str(row.day), float(row.btc_volume)) for row in result]

def _update_volume(con):
    row = con.execute("SELECT MAX(day) FROM nvt_daily").fetchone()
    last = row[0] if row and row[0] else None
    floor = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    since = last if last and last > floor else floor
    rows = _fetch_volume(since)
    if rows:
        con.executemany("INSERT OR REPLACE INTO nvt_daily (day, btc_volume) VALUES (?,?)", rows)
        con.commit()

def _moving_avg(values_dict, n=28):
    days = sorted(values_dict)
    result = {}
    for i, d in enumerate(days):
        window = days[max(0, i - n + 1):i + 1]
        result[d] = sum(values_dict[w] for w in window) / len(window)
    return result

def get_nvt():
    con = _init_db()
    cached = _cache_get(con, "nvt")
    if cached:
        return cached

    _update_volume(con)

    rows = con.execute(
        "SELECT day, btc_volume FROM nvt_daily WHERE day >= date('now','-430 days') ORDER BY day"
    ).fetchall()

    vol = {day: btc for day, btc in rows}
    ma = _moving_avg(vol, n=28)

    rc_row = con.execute("SELECT value FROM cache WHERE key='realized_cap'").fetchone()
    circulating_supply = json.loads(rc_row[0]).get("circulating_supply") if rc_row else None

    r = requests.get("https://api.kraken.com/0/public/Ticker", params={"pair": "XBTUSD"}, timeout=10)
    current_price = float(r.json()["result"][list(r.json()["result"])[0]]["c"][0])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    labels, values = [], []
    for day in sorted(ma):
        if day < cutoff or not circulating_supply or ma[day] == 0:
            continue
        labels.append(day)
        values.append(round(circulating_supply / ma[day], 2))

    current_nvt = None
    if labels and circulating_supply and ma.get(labels[-1]):
        current_nvt = round(circulating_supply / ma[labels[-1]], 2)

    result = {
        "nvt": current_nvt,
        "current_price": current_price,
        "labels": labels,
        "values": values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "nvt", result)
    return result

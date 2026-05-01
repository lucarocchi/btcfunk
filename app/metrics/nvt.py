import sqlite3, json, requests
from datetime import datetime, timezone, timedelta

DB_PATH = "btcfunk.sqlite"
CACHE_TTL_HOURS = 24


def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
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
    if cached: return cached

    rows = con.execute(
        "SELECT day, btc_volume FROM nvt_daily WHERE day >= date('now','-430 days') ORDER BY day"
    ).fetchall()

    vol = {day: btc for day, btc in rows}
    ma  = _moving_avg(vol, n=28)

    supply_row = con.execute("SELECT SUM(btc_value) FROM utxo_snapshot").fetchone()
    circulating_supply = supply_row[0] if supply_row and supply_row[0] else None

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
        "nvt":           current_nvt,
        "current_price": current_price,
        "labels":        labels,
        "values":        values,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "nvt", result)
    return result

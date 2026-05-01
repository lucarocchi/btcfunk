import sqlite3, json, statistics
from datetime import datetime, timezone, timedelta

DB_PATH = "btcfunk.sqlite"
CACHE_TTL_HOURS = 24


def _cache_get(con, key):
    row = con.execute("SELECT value, updated_at FROM cache WHERE key=?", (key,)).fetchone()
    if not row: return None
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(row[1])).total_seconds() / 3600
    return json.loads(row[0]) if age < CACHE_TTL_HOURS else None


def _cache_set(con, key, value):
    con.execute("INSERT OR REPLACE INTO cache (key,value,updated_at) VALUES (?,?,?)",
                (key, json.dumps(value), datetime.now(timezone.utc).isoformat()))
    con.commit()


def get_mvrv_zscore():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
    cached = _cache_get(con, "mvrv_zscore")
    if cached:
        return cached

    from app.metrics.mvrv import get_mvrv
    d = get_mvrv()

    supply       = d["market_cap"] / d["current_price"]
    realized_cap = d["realized_cap"]
    current_mc   = d["market_cap"]

    prices = {r[0]: r[1] for r in con.execute(
        "SELECT day, price FROM btc_prices ORDER BY day").fetchall()}

    all_mkt_caps = [supply * p for p in prices.values()]
    std = statistics.stdev(all_mkt_caps) if len(all_mkt_caps) > 1 else 1

    z = round((current_mc - realized_cap) / std, 4)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    hist   = [(day, p) for day, p in sorted(prices.items()) if day >= cutoff]
    labels = [x[0] for x in hist]
    values = [round((supply * x[1] - realized_cap) / std, 4) for x in hist]

    result = {
        "z_score":      z,
        "market_cap":   current_mc,
        "realized_cap": realized_cap,
        "labels":       labels,
        "values":       values,
        "updated_at":   datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "mvrv_zscore", result)
    return result

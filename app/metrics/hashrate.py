import sqlite3, json
from datetime import datetime, timezone

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


def _ma(values_dict, n):
    days = sorted(values_dict)
    out  = {}
    for i, d in enumerate(days):
        w = days[max(0, i - n + 1):i + 1]
        out[d] = sum(values_dict[x] for x in w) / len(w)
    return out


def get_hashrate():
    con = _init_db()
    cached = _cache_get(con, "hashrate")
    if cached: return cached

    rows = con.execute("""
        SELECT day, hashrate_eh, block_count FROM hashrate_daily
        WHERE day >= date('now', '-365 days') ORDER BY day
    """).fetchall()

    labels       = [r[0] for r in rows]
    values       = [r[1] for r in rows]
    block_counts = [r[2] for r in rows]

    all_hr = {r[0]: r[1] for r in
              con.execute("SELECT day, hashrate_eh FROM hashrate_daily ORDER BY day").fetchall()}
    ma14 = _ma(all_hr, 14)

    result = {
        "hashrate_eh": values[-1]       if values      else None,
        "ma14_eh":     round(ma14.get(labels[-1], 0), 4) if labels else None,
        "block_count": block_counts[-1] if block_counts else None,
        "labels":      labels,
        "values":      values,
        "updated_at":  datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "hashrate", result)
    return result

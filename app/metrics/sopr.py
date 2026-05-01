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


def get_sopr():
    con = _init_db()
    cached = _cache_get(con, "sopr")
    if cached: return cached

    rows = con.execute("""
        SELECT day, sopr FROM sopr_daily
        WHERE day >= date('now', '-365 days')
        ORDER BY day
    """).fetchall()

    labels  = [r[0] for r in rows]
    values  = [r[1] for r in rows]
    current = values[-1] if values else None

    result = {
        "current":    current,
        "labels":     labels,
        "values":     values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "sopr", result)
    return result

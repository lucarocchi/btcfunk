import sqlite3, json
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"
CACHE_TTL_HOURS = 24


def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS exchange_flows_daily (
            day TEXT, exchange TEXT, inflow REAL DEFAULT 0, outflow REAL DEFAULT 0,
            PRIMARY KEY (day, exchange)
        )
    """)
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


def get_exchange_flow():
    con = _init_db()
    cached = _cache_get(con, "exchange_flow")
    if cached: return cached

    rows = con.execute("""
        SELECT day, SUM(inflow) AS inflow, SUM(outflow) AS outflow
        FROM exchange_flows_daily
        WHERE day >= date('now', '-365 days')
        GROUP BY day ORDER BY day
    """).fetchall()

    if not rows:
        return {"error": "no exchange flow data — run scripts/import_exchange_addresses.py first"}

    labels   = [r[0] for r in rows]
    inflows  = [round(r[1], 2) for r in rows]
    outflows = [round(r[2], 2) for r in rows]
    net      = [round(r[1] - r[2], 2) for r in rows]

    top = con.execute("""
        SELECT exchange, SUM(inflow) AS total_in, SUM(outflow) AS total_out
        FROM exchange_flows_daily
        WHERE day >= date('now', '-30 days')
        GROUP BY exchange ORDER BY (total_in + total_out) DESC LIMIT 10
    """).fetchall()

    reserve_values = []
    running = 0.0
    for v in net:
        running += v
        reserve_values.append(round(running, 2))

    result = {
        "current_inflow":  inflows[-1]         if inflows  else None,
        "current_outflow": outflows[-1]         if outflows else None,
        "current_net":     net[-1]              if net      else None,
        "current_reserve": reserve_values[-1]   if reserve_values else None,
        "labels":          labels,
        "inflows":         inflows,
        "outflows":        outflows,
        "net":             net,
        "reserve":         reserve_values,
        "top_exchanges":   [{"exchange": r[0], "inflow": round(r[1], 2), "outflow": round(r[2], 2)} for r in top],
        "updated_at":      datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "exchange_flow", result)
    return result

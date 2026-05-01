import sqlite3
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"


def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS exchange_flows_daily (
            day TEXT, exchange TEXT, inflow REAL DEFAULT 0, outflow REAL DEFAULT 0,
            PRIMARY KEY (day, exchange)
        )
    """)
    con.commit()
    return con


def get_exchange_flow():
    con = _init_db()

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

    return {
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

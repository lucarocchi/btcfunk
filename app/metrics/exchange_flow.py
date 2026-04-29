import sqlite3, json
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery

DB_PATH = "mvrv_cache.sqlite"
CACHE_TTL_HOURS = 24
HISTORY_DAYS = 365

_bq_client = None

def _get_bq():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client()
    return _bq_client

def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS exchange_flows_daily (
            day      TEXT,
            exchange TEXT,
            inflow   REAL DEFAULT 0,
            outflow  REAL DEFAULT 0,
            PRIMARY KEY (day, exchange)
        )
    """)
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

def _get_addresses(con):
    rows = con.execute("SELECT address, exchange FROM known_addresses").fetchall()
    return {addr: exc for addr, exc in rows}

def _fetch_flows(addr_map, since_day):
    addr_list = ", ".join(f"'{a}'" for a in addr_map)

    query = f"""
    WITH inflows AS (
        SELECT
            DATE(o.block_timestamp) AS day,
            addr                    AS address,
            SUM(o.value) / 1e8      AS btc
        FROM `bigquery-public-data.crypto_bitcoin.outputs` o,
        UNNEST(o.addresses) AS addr
        WHERE addr IN ({addr_list})
          AND DATE(o.block_timestamp) > '{since_day}'
        GROUP BY day, address
    ),
    outflows AS (
        SELECT
            DATE(i.block_timestamp) AS day,
            addr                    AS address,
            SUM(o.value) / 1e8      AS btc
        FROM `bigquery-public-data.crypto_bitcoin.inputs` i
        JOIN `bigquery-public-data.crypto_bitcoin.outputs` o
            ON i.spent_transaction_hash = o.transaction_hash
            AND i.spent_output_index    = o.index,
        UNNEST(o.addresses) AS addr
        WHERE addr IN ({addr_list})
          AND DATE(i.block_timestamp) > '{since_day}'
        GROUP BY day, address
    )
    SELECT
        COALESCE(i.day,     out.day)     AS day,
        COALESCE(i.address, out.address) AS address,
        COALESCE(i.btc,  0)              AS inflow,
        COALESCE(out.btc, 0)             AS outflow
    FROM inflows i
    FULL OUTER JOIN outflows out ON i.day = out.day AND i.address = out.address
    ORDER BY day
    """
    result = _get_bq().query(query).result()
    return [(str(row.day), row.address, float(row.inflow), float(row.outflow)) for row in result]

def _update_flows(con, addr_map):
    row = con.execute("SELECT MAX(day) FROM exchange_flows_daily").fetchone()
    last = row[0] if row and row[0] else None
    floor = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    since = last if last and last > floor else floor

    rows = _fetch_flows(addr_map, since)
    if not rows:
        return

    # Aggregate by (day, exchange) — multiple addresses per exchange
    agg = {}
    for day, address, inflow, outflow in rows:
        exchange = addr_map.get(address, "Unknown")
        k = (day, exchange)
        if k not in agg:
            agg[k] = [0.0, 0.0]
        agg[k][0] += inflow
        agg[k][1] += outflow

    to_insert = [(day, exc, round(inf, 4), round(out, 4)) for (day, exc), (inf, out) in agg.items()]
    con.executemany(
        "INSERT OR REPLACE INTO exchange_flows_daily (day, exchange, inflow, outflow) VALUES (?,?,?,?)",
        to_insert,
    )
    con.commit()

def get_exchange_flow():
    con = _init_db()
    cached = _cache_get(con, "exchange_flow")
    if cached:
        return cached

    addr_map = _get_addresses(con)
    if not addr_map:
        return {"error": "no addresses — run scripts/import_exchange_addresses.py first"}

    _update_flows(con, addr_map)

    # All exchanges aggregated — last 365 days
    rows = con.execute("""
        SELECT day, SUM(inflow) AS inflow, SUM(outflow) AS outflow
        FROM exchange_flows_daily
        WHERE day >= date('now', '-365 days')
        GROUP BY day ORDER BY day
    """).fetchall()

    labels   = [r[0] for r in rows]
    inflows  = [round(r[1], 2) for r in rows]
    outflows = [round(r[2], 2) for r in rows]
    net      = [round(r[1] - r[2], 2) for r in rows]

    # Top exchanges last 30 days
    top = con.execute("""
        SELECT exchange, SUM(inflow) AS total_in, SUM(outflow) AS total_out
        FROM exchange_flows_daily
        WHERE day >= date('now', '-30 days')
        GROUP BY exchange
        ORDER BY (total_in + total_out) DESC
        LIMIT 10
    """).fetchall()

    # Exchange Reserve: cumulative net flow trend over available period
    reserve_values = []
    running = 0.0
    for v in net:
        running += v
        reserve_values.append(round(running, 2))

    result = {
        "current_inflow":   inflows[-1]  if inflows  else None,
        "current_outflow":  outflows[-1] if outflows else None,
        "current_net":      net[-1]      if net      else None,
        "current_reserve":  reserve_values[-1] if reserve_values else None,
        "labels":           labels,
        "inflows":          inflows,
        "outflows":         outflows,
        "net":              net,
        "reserve":          reserve_values,
        "top_exchanges":    [{"exchange": r[0], "inflow": round(r[1], 2), "outflow": round(r[2], 2)} for r in top],
        "address_count":    len(addr_map),
        "updated_at":       datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "exchange_flow", result)
    return result

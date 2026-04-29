import sqlite3, json
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery

DB_PATH = "mvrv_cache.sqlite"
CACHE_TTL_HOURS = 24
HISTORY_DAYS = 400

_bq_client = None


def _get_bq():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client()
    return _bq_client


def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS active_addr_daily (
            day   TEXT PRIMARY KEY,
            count INTEGER
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


def _fetch_active(since_day):
    query = f"""
        SELECT
            DATE(o.block_timestamp) AS day,
            COUNT(DISTINCT addr)    AS count
        FROM `bigquery-public-data.crypto_bitcoin.outputs` o,
        UNNEST(o.addresses) AS addr
        WHERE DATE(o.block_timestamp) > '{since_day}'
        GROUP BY day ORDER BY day
    """
    result = _get_bq().query(query).result()
    return [(str(row.day), int(row.count)) for row in result]


def _update(con):
    row = con.execute("SELECT MAX(day) FROM active_addr_daily").fetchone()
    last = row[0] if row and row[0] else None
    floor = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    since = last if last and last > floor else floor
    rows = _fetch_active(since)
    if rows:
        con.executemany("INSERT OR REPLACE INTO active_addr_daily (day, count) VALUES (?,?)", rows)
        con.commit()


def _moving_avg(values_dict, n):
    days = sorted(values_dict)
    result = {}
    for i, d in enumerate(days):
        window = days[max(0, i - n + 1):i + 1]
        result[d] = sum(values_dict[w] for w in window) / len(window)
    return result


def get_active_addresses():
    con = _init_db()
    cached = _cache_get(con, "active_addresses")
    if cached:
        return cached

    _update(con)

    rows = con.execute("""
        SELECT day, count FROM active_addr_daily
        WHERE day >= date('now', '-365 days')
        ORDER BY day
    """).fetchall()

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    current = values[-1] if values else None

    all_rows = con.execute("SELECT day, count FROM active_addr_daily ORDER BY day").fetchall()
    ma30 = _moving_avg({r[0]: r[1] for r in all_rows}, 30)
    ma30_current = round(ma30.get(labels[-1], 0)) if labels else None

    result = {
        "current":     current,
        "ma30":        ma30_current,
        "labels":      labels,
        "values":      values,
        "updated_at":  datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "active_addresses", result)
    return result

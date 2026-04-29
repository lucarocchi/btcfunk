import sqlite3, json
from collections import defaultdict
from datetime import datetime, timezone, timedelta, date
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
    con.execute("CREATE TABLE IF NOT EXISTS cdd_daily (day TEXT PRIMARY KEY, cdd REAL)")
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

def _fetch_flows(since_day):
    """Same base query as SOPR: (spend_day, creation_day, btc_amount)."""
    query = f"""
        SELECT
            DATE(i.block_timestamp) AS spend_day,
            DATE(o.block_timestamp) AS creation_day,
            SUM(o.value) / 1e8      AS btc_amount
        FROM `bigquery-public-data.crypto_bitcoin.inputs` i
        JOIN `bigquery-public-data.crypto_bitcoin.outputs` o
            ON i.spent_transaction_hash = o.transaction_hash
            AND i.spent_output_index = o.index
        WHERE o.value > 0
          AND DATE(i.block_timestamp) > '{since_day}'
        GROUP BY spend_day, creation_day
        ORDER BY spend_day
    """
    result = _get_bq().query(query).result()
    return [(str(row.spend_day), str(row.creation_day), float(row.btc_amount)) for row in result]

def _update_cdd(con):
    row = con.execute("SELECT MAX(day) FROM cdd_daily").fetchone()
    last = row[0] if row and row[0] else None
    floor = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    since = last if last and last > floor else floor

    rows = _fetch_flows(since)
    if not rows:
        return

    daily = defaultdict(float)
    for spend_day, creation_day, btc_amount in rows:
        try:
            age_days = (date.fromisoformat(spend_day) - date.fromisoformat(creation_day)).days
        except ValueError:
            continue
        if age_days < 0:
            continue
        daily[spend_day] += btc_amount * age_days

    to_insert = [(day, round(val, 2)) for day, val in sorted(daily.items())]
    if to_insert:
        con.executemany("INSERT OR REPLACE INTO cdd_daily (day, cdd) VALUES (?,?)", to_insert)
        con.commit()

def _moving_avg(values_dict, n=90):
    days = sorted(values_dict)
    result = {}
    for i, d in enumerate(days):
        window = days[max(0, i - n + 1):i + 1]
        result[d] = sum(values_dict[w] for w in window) / len(window)
    return result

def get_cdd():
    con = _init_db()
    cached = _cache_get(con, "cdd")
    if cached:
        return cached

    _update_cdd(con)

    rows = con.execute("""
        SELECT day, cdd FROM cdd_daily
        WHERE day >= date('now', '-365 days')
        ORDER BY day
    """).fetchall()

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    current = values[-1] if values else None

    # 90-day MA for signal
    all_rows = con.execute("SELECT day, cdd FROM cdd_daily ORDER BY day").fetchall()
    ma = _moving_avg({r[0]: r[1] for r in all_rows}, n=90)
    ma_current = ma.get(labels[-1]) if labels else None

    result = {
        "current": current,
        "ma90": round(ma_current, 2) if ma_current else None,
        "labels": labels,
        "values": values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "cdd", result)
    return result

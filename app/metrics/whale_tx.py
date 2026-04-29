import sqlite3, json
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery

DB_PATH = "mvrv_cache.sqlite"
CACHE_TTL_HOURS = 24
HISTORY_DAYS = 400
WHALE_THRESHOLD_SAT = 10_000_000_000  # 100 BTC

_bq_client = None


def _get_bq():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client()
    return _bq_client


def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS whale_tx_daily (
            day        TEXT PRIMARY KEY,
            count      INTEGER,
            btc_volume REAL
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


def _fetch_whales(since_day):
    query = f"""
        SELECT
            DATE(block_timestamp)    AS day,
            COUNT(*)                 AS count,
            SUM(output_value) / 1e8  AS btc_volume
        FROM `bigquery-public-data.crypto_bitcoin.transactions`
        WHERE NOT is_coinbase
          AND output_value >= {WHALE_THRESHOLD_SAT}
          AND DATE(block_timestamp) > '{since_day}'
        GROUP BY day ORDER BY day
    """
    result = _get_bq().query(query).result()
    return [(str(row.day), int(row.count), float(row.btc_volume)) for row in result]


def _update(con):
    row = con.execute("SELECT MAX(day) FROM whale_tx_daily").fetchone()
    last = row[0] if row and row[0] else None
    floor = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    since = last if last and last > floor else floor
    rows = _fetch_whales(since)
    if rows:
        con.executemany(
            "INSERT OR REPLACE INTO whale_tx_daily (day, count, btc_volume) VALUES (?,?,?)", rows
        )
        con.commit()


def _moving_avg(values_dict, n):
    days = sorted(values_dict)
    result = {}
    for i, d in enumerate(days):
        window = days[max(0, i - n + 1):i + 1]
        result[d] = sum(values_dict[w] for w in window) / len(window)
    return result


def get_whale_tx():
    con = _init_db()
    cached = _cache_get(con, "whale_tx")
    if cached:
        return cached

    _update(con)

    rows = con.execute("""
        SELECT day, count, btc_volume FROM whale_tx_daily
        WHERE day >= date('now', '-365 days')
        ORDER BY day
    """).fetchall()

    labels     = [r[0] for r in rows]
    values     = [r[1] for r in rows]
    btc_series = [round(r[2], 2) for r in rows]
    current_count  = values[-1]     if values else None
    current_volume = btc_series[-1] if btc_series else None

    all_rows = con.execute("SELECT day, count FROM whale_tx_daily ORDER BY day").fetchall()
    ma30 = _moving_avg({r[0]: r[1] for r in all_rows}, 30)
    ma30_current = round(ma30.get(labels[-1], 0)) if labels else None

    result = {
        "current":        current_count,
        "current_volume": current_volume,
        "ma30":           ma30_current,
        "labels":         labels,
        "values":         values,
        "btc_series":     btc_series,
        "threshold_btc":  WHALE_THRESHOLD_SAT / 1e8,
        "updated_at":     datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "whale_tx", result)
    return result

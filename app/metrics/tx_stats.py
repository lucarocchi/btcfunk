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
        CREATE TABLE IF NOT EXISTS tx_stats_daily (
            day       TEXT PRIMARY KEY,
            tx_count  INTEGER,
            volume    REAL,
            fees      REAL
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


def _fetch(since_day):
    query = f"""
        SELECT
            DATE(block_timestamp)      AS day,
            COUNT(*)                   AS tx_count,
            SUM(output_value) / 1e8    AS volume_btc,
            SUM(fee) / 1e8             AS fees_btc
        FROM `bigquery-public-data.crypto_bitcoin.transactions`
        WHERE NOT is_coinbase
          AND DATE(block_timestamp) > '{since_day}'
        GROUP BY day ORDER BY day
    """
    result = _get_bq().query(query).result()
    return [(str(r.day), int(r.tx_count), float(r.volume_btc), float(r.fees_btc)) for r in result]


def _update(con):
    row = con.execute("SELECT MAX(day) FROM tx_stats_daily").fetchone()
    last  = row[0] if row and row[0] else None
    floor = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    since = last if last and last > floor else floor
    rows  = _fetch(since)
    if rows:
        con.executemany(
            "INSERT OR REPLACE INTO tx_stats_daily (day, tx_count, volume, fees) VALUES (?,?,?,?)",
            rows
        )
        con.commit()


def _ma(values_dict, n):
    days = sorted(values_dict)
    out  = {}
    for i, d in enumerate(days):
        w = days[max(0, i - n + 1):i + 1]
        out[d] = sum(values_dict[x] for x in w) / len(w)
    return out


def get_tx_stats():
    con = _init_db()
    cached = _cache_get(con, "tx_stats")
    if cached:
        return cached

    _update(con)

    rows = con.execute("""
        SELECT day, tx_count, volume, fees FROM tx_stats_daily
        WHERE day >= date('now', '-365 days') ORDER BY day
    """).fetchall()

    labels    = [r[0] for r in rows]
    tx_counts = [r[1] for r in rows]
    volumes   = [round(r[2], 2) for r in rows]
    fees      = [round(r[3], 6) for r in rows]
    avg_fees  = [round(r[3] / r[1], 8) if r[1] else 0 for r in rows]

    all_tx = {r[0]: r[1] for r in con.execute("SELECT day, tx_count FROM tx_stats_daily ORDER BY day").fetchall()}
    ma30   = _ma(all_tx, 30)

    result = {
        "tx_count":        tx_counts[-1]  if tx_counts else None,
        "tx_count_ma30":   round(ma30.get(labels[-1], 0)) if labels else None,
        "volume_btc":      volumes[-1]    if volumes   else None,
        "avg_fee_btc":     avg_fees[-1]   if avg_fees  else None,
        "labels":          labels,
        "tx_counts":       tx_counts,
        "volumes":         volumes,
        "avg_fees":        avg_fees,
        "updated_at":      datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "tx_stats", result)
    return result

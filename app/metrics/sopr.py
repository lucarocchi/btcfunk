import sqlite3
import json
import requests
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery

DB_PATH = "mvrv_cache.sqlite"
CACHE_TTL_HOURS = 24

_bq_client = None


def _get_bq():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client()
    return _bq_client


def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS sopr_daily (
            day TEXT PRIMARY KEY,
            sopr REAL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)
    con.commit()
    return con


def _cache_get(con, key):
    row = con.execute("SELECT value, updated_at FROM cache WHERE key = ?", (key,)).fetchone()
    if not row:
        return None
    updated = datetime.fromisoformat(row[1])
    age_hours = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
    if age_hours > CACHE_TTL_HOURS:
        return None
    return json.loads(row[0])


def _cache_set(con, key, value):
    con.execute(
        "INSERT OR REPLACE INTO cache (key, value, updated_at) VALUES (?, ?, ?)",
        (key, json.dumps(value), datetime.now(timezone.utc).isoformat())
    )
    con.commit()


def _fetch_sopr(since_day=None):
    """Fetch daily SOPR from BigQuery.
    SOPR = sum(value_at_spend) / sum(value_at_creation) per day.
    """
    where = ""
    if since_day:
        where = f"AND DATE(i.block_timestamp) > '{since_day}'"

    query = f"""
        SELECT
            DATE(i.block_timestamp) AS day,
            SUM(o.value) / 1e8      AS value_created,
            SUM(i_val.value) / 1e8  AS value_spent
        FROM `bigquery-public-data.crypto_bitcoin.inputs` i
        JOIN `bigquery-public-data.crypto_bitcoin.outputs` o
            ON i.spent_transaction_hash = o.transaction_hash
            AND i.spent_output_index = o.index
        JOIN `bigquery-public-data.crypto_bitcoin.outputs` i_val
            ON i.transaction_hash = i_val.transaction_hash
            AND i_val.index = 0
        WHERE o.value > 0
        {where}
        GROUP BY day
        ORDER BY day
    """
    result = _get_bq().query(query).result()
    return [(str(row.day), float(row.value_spent), float(row.value_created)) for row in result]


def _get_prices(con):
    rows = con.execute("SELECT day, price FROM btc_prices").fetchall()
    return {row[0]: row[1] for row in rows}


def _update_sopr(con):
    row = con.execute("SELECT MAX(day) FROM sopr_daily").fetchone()
    since_day = row[0] if row and row[0] else None

    rows = _fetch_sopr(since_day)
    if not rows:
        return

    prices = _get_prices(con)
    to_insert = []
    for day, value_spent, value_created in rows:
        price = prices.get(day)
        if not price or value_created == 0:
            continue
        sopr = (value_spent * price) / (value_created * price)
        to_insert.append((day, round(sopr, 6)))

    if to_insert:
        con.executemany("INSERT OR REPLACE INTO sopr_daily (day, sopr) VALUES (?, ?)", to_insert)
        con.commit()


def get_sopr():
    con = _init_db()

    cached = _cache_get(con, "sopr")
    if cached:
        return cached

    _update_sopr(con)

    # Last 365 days for the chart
    rows = con.execute("""
        SELECT day, sopr FROM sopr_daily
        WHERE day >= date('now', '-365 days')
        ORDER BY day
    """).fetchall()

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    current = values[-1] if values else None

    result = {
        "current": current,
        "labels": labels,
        "values": values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    _cache_set(con, "sopr", result)
    return result

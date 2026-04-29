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
    """
    SOPR = sum(btc_i * price_at_spend_day) / sum(btc_i * price_at_creation_day)

    Query returns (spend_day, creation_day, btc_amount) for each unique pair.
    Prices are applied in Python using local btc_prices table.
    """
    where = ""
    if since_day:
        where = f"AND DATE(i.block_timestamp) > '{since_day}'"

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
        {where}
        GROUP BY spend_day, creation_day
        ORDER BY spend_day
    """
    result = _get_bq().query(query).result()
    return [(str(row.spend_day), str(row.creation_day), float(row.btc_amount)) for row in result]


def _get_prices(con):
    rows = con.execute("SELECT day, price FROM btc_prices").fetchall()
    return {row[0]: row[1] for row in rows}


SOPR_HISTORY_DAYS = 400  # fetch slightly more than the 365 shown in chart

def _update_sopr(con):
    row = con.execute("SELECT MAX(day) FROM sopr_daily").fetchone()
    last = row[0] if row and row[0] else None
    floor = (datetime.now(timezone.utc) - timedelta(days=SOPR_HISTORY_DAYS)).strftime("%Y-%m-%d")
    since_day = last if last and last > floor else floor

    rows = _fetch_sopr(since_day)
    if not rows:
        return

    prices = _get_prices(con)

    from collections import defaultdict
    realized  = defaultdict(float)
    cost_basis = defaultdict(float)

    for spend_day, creation_day, btc_amount in rows:
        p_spend    = prices.get(spend_day)
        p_creation = prices.get(creation_day)
        if not p_spend or not p_creation:
            continue
        realized[spend_day]   += btc_amount * p_spend
        cost_basis[spend_day] += btc_amount * p_creation

    to_insert = [
        (day, round(realized[day] / cost_basis[day], 6))
        for day in sorted(realized)
        if cost_basis[day] > 0
    ]

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

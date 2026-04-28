import sqlite3
import json
import requests
from datetime import datetime, timezone
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


def _fetch_prices():
    """Fetch daily BTC/USDT close prices from Binance (free, no auth, last 1000 days)"""
    r = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": "1d", "limit": 1000},
        timeout=30,
    )
    r.raise_for_status()
    return {
        datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d"): float(candle[4])
        for candle in r.json()
    }


def _fetch_utxos():
    query = """
        SELECT
            DATE(o.block_timestamp) AS day,
            SUM(o.value) / 1e8     AS btc_value
        FROM `bigquery-public-data.crypto_bitcoin.outputs` o
        LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
            ON o.transaction_hash = i.spent_transaction_hash
            AND o.index = i.spent_output_index
        WHERE i.transaction_hash IS NULL
        GROUP BY day
        ORDER BY day
    """
    result = _get_bq().query(query).result()
    return {str(row.day): float(row.btc_value) for row in result}


def get_mvrv():
    con = _init_db()

    cached = _cache_get(con, "mvrv")
    if cached:
        return cached

    # Current price + market cap
    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": "bitcoin", "vs_currencies": "usd", "include_market_cap": "true"},
        timeout=10,
    )
    r.raise_for_status()
    btc = r.json()["bitcoin"]
    current_price = btc["usd"]
    market_cap = btc["usd_market_cap"]

    prices = _fetch_prices()
    utxos = _fetch_utxos()

    realized_cap = sum(
        btc_val * prices.get(day, current_price)
        for day, btc_val in utxos.items()
    )

    result = {
        "mvrv": round(market_cap / realized_cap, 4) if realized_cap else 0,
        "market_cap": market_cap,
        "realized_cap": realized_cap,
        "current_price": current_price,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    _cache_set(con, "mvrv", result)
    return result

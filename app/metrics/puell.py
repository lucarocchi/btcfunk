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
        CREATE TABLE IF NOT EXISTS puell_daily (
            day     TEXT PRIMARY KEY,
            revenue REAL
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


def _fetch_miner_revenue(since_day):
    query = f"""
        SELECT DATE(block_timestamp) AS day, SUM(output_value) / 1e8 AS revenue
        FROM `bigquery-public-data.crypto_bitcoin.transactions`
        WHERE is_coinbase = TRUE
          AND DATE(block_timestamp) > '{since_day}'
        GROUP BY day ORDER BY day
    """
    result = _get_bq().query(query).result()
    return [(str(row.day), float(row.revenue)) for row in result]


def _update_puell(con):
    row = con.execute("SELECT MAX(day) FROM puell_daily").fetchone()
    last = row[0] if row and row[0] else None
    floor = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    since = last if last and last > floor else floor
    rows = _fetch_miner_revenue(since)
    if rows:
        con.executemany("INSERT OR REPLACE INTO puell_daily (day, revenue) VALUES (?,?)", rows)
        con.commit()


def _moving_avg(values_dict, n):
    days = sorted(values_dict)
    result = {}
    for i, d in enumerate(days):
        window = days[max(0, i - n + 1):i + 1]
        result[d] = sum(values_dict[w] for w in window) / len(window)
    return result


def get_puell():
    con = _init_db()
    cached = _cache_get(con, "puell")
    if cached:
        return cached

    _update_puell(con)

    all_rows = con.execute("SELECT day, revenue FROM puell_daily ORDER BY day").fetchall()
    revenue_dict = {r[0]: r[1] for r in all_rows}

    ma365 = _moving_avg(revenue_dict, 365)

    # Last 365 days for chart
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    chart_days = sorted(d for d in revenue_dict if d >= cutoff)
    labels  = chart_days
    values  = [round(revenue_dict[d] / ma365[d], 4) if ma365.get(d) else None for d in chart_days]

    current_day    = chart_days[-1]  if chart_days else None
    current_puell  = values[-1]      if values     else None
    current_revenue= round(revenue_dict.get(current_day, 0), 2) if current_day else None
    current_ma365  = round(ma365.get(current_day, 0), 2)        if current_day else None

    result = {
        "puell":           current_puell,
        "daily_revenue":   current_revenue,
        "ma365_revenue":   current_ma365,
        "labels":          labels,
        "values":          values,
        "updated_at":      datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "puell", result)
    return result

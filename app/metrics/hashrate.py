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
        CREATE TABLE IF NOT EXISTS hashrate_daily (
            day         TEXT PRIMARY KEY,
            difficulty  REAL,
            hashrate_eh REAL,
            block_count INTEGER
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
            DATE(timestamp)    AS day,
            AVG(difficulty)    AS avg_difficulty,
            COUNT(*)           AS block_count
        FROM `bigquery-public-data.crypto_bitcoin.blocks`
        WHERE DATE(timestamp) > '{since_day}'
        GROUP BY day ORDER BY day
    """
    result = _get_bq().query(query).result()
    rows   = []
    for r in result:
        diff = float(r.avg_difficulty)
        # hash_rate (H/s) = difficulty × 2^32 / 600; convert to EH/s (/1e18)
        eh = round(diff * (2 ** 32) / 600 / 1e18, 4)
        rows.append((str(r.day), diff, eh, int(r.block_count)))
    return rows


def _update(con):
    row   = con.execute("SELECT MAX(day) FROM hashrate_daily").fetchone()
    last  = row[0] if row and row[0] else None
    floor = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    since = last if last and last > floor else floor
    rows  = _fetch(since)
    if rows:
        con.executemany(
            "INSERT OR REPLACE INTO hashrate_daily (day, difficulty, hashrate_eh, block_count) VALUES (?,?,?,?)",
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


def get_hashrate():
    con = _init_db()
    cached = _cache_get(con, "hashrate")
    if cached:
        return cached

    _update(con)

    rows = con.execute("""
        SELECT day, hashrate_eh, block_count FROM hashrate_daily
        WHERE day >= date('now', '-365 days') ORDER BY day
    """).fetchall()

    labels      = [r[0] for r in rows]
    values      = [r[1] for r in rows]
    block_counts= [r[2] for r in rows]

    all_hr = {r[0]: r[1] for r in con.execute("SELECT day, hashrate_eh FROM hashrate_daily ORDER BY day").fetchall()}
    ma14   = _ma(all_hr, 14)

    result = {
        "hashrate_eh":   values[-1]       if values      else None,
        "ma14_eh":       round(ma14.get(labels[-1], 0), 4) if labels else None,
        "block_count":   block_counts[-1] if block_counts else None,
        "labels":        labels,
        "values":        values,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "hashrate", result)
    return result

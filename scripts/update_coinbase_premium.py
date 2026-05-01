"""
Popola/aggiorna coinbase_premium_daily in btcfunk.sqlite.
  --backfill   scarica tutta la storia disponibile (2019-01-01 → ieri)
  (default)    aggiorna solo ieri
"""
import os, sys, sqlite3, time, argparse
import requests
from datetime import date, timedelta, datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "../btcfunk.sqlite")
HEADERS    = {"User-Agent": "btcfunk/1.0"}

CB_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
BN_URL = "https://api.binance.com/api/v3/klines"


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def _init(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS coinbase_premium_daily (
            day          TEXT PRIMARY KEY,
            coinbase_close REAL,
            binance_close  REAL,
            premium_pct    REAL
        )
    """)
    con.commit()


def _since(con):
    row = con.execute("SELECT MAX(day) FROM coinbase_premium_daily").fetchone()
    return row[0] if row[0] else None


def _fetch_coinbase(start: date, end: date) -> dict:
    """Returns {day_str: close_price}. Coinbase returns max 300 candles per call."""
    result = {}
    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(days=299), end)
        params = {
            "granularity": 86400,
            "start": chunk_start.isoformat() + "T00:00:00Z",
            "end":   chunk_end.isoformat()   + "T23:59:59Z",
        }
        try:
            r = requests.get(CB_URL, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            candles = r.json()
            for c in candles:
                # format: [timestamp, low, high, open, close, volume]
                d = date.fromtimestamp(c[0]).isoformat()
                result[d] = float(c[4])
        except Exception as e:
            log(f"  Coinbase fetch error {chunk_start}→{chunk_end}: {e}")
        chunk_start = chunk_end + timedelta(days=1)
        time.sleep(0.3)
    return result


def _fetch_binance(start: date, end: date) -> dict:
    """Returns {day_str: close_price}. Binance returns max 1000 candles per call."""
    result = {}
    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(days=999), end)
        params = {
            "symbol":    "BTCUSDT",
            "interval":  "1d",
            "startTime": int(datetime(chunk_start.year, chunk_start.month, chunk_start.day, tzinfo=timezone.utc).timestamp() * 1000),
            "endTime":   int(datetime(chunk_end.year,   chunk_end.month,   chunk_end.day,   23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000),
            "limit":     1000,
        }
        try:
            r = requests.get(BN_URL, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            candles = r.json()
            for c in candles:
                # format: [openTime, open, high, low, close, ...]
                d = datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                result[d] = float(c[4])
        except Exception as e:
            log(f"  Binance fetch error {chunk_start}→{chunk_end}: {e}")
        chunk_start = chunk_end + timedelta(days=1)
        time.sleep(0.3)
    return result


def run(start: date, end: date, con):
    log(f"Fetching Coinbase candles {start} → {end}")
    cb_data = _fetch_coinbase(start, end)
    log(f"  Coinbase: {len(cb_data)} days")

    log(f"Fetching Binance candles {start} → {end}")
    bn_data = _fetch_binance(start, end)
    log(f"  Binance: {len(bn_data)} days")

    rows = []
    for d in sorted(set(cb_data) & set(bn_data)):
        cb = cb_data[d]
        bn = bn_data[d]
        if bn == 0:
            continue
        pct = round((cb - bn) / bn * 100, 4)
        rows.append((d, cb, bn, pct))

    con.executemany(
        "INSERT OR REPLACE INTO coinbase_premium_daily (day, coinbase_close, binance_close, premium_pct) VALUES (?,?,?,?)",
        rows
    )
    con.commit()
    log(f"  Inserted/updated {len(rows)} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill", action="store_true", help="Fetch full history from 2019-01-01")
    args = parser.parse_args()

    con = sqlite3.connect(DB_PATH)
    _init(con)

    yesterday = date.today() - timedelta(days=1)

    if args.backfill:
        start = date(2019, 1, 1)
    else:
        last = _since(con)
        if last:
            start = date.fromisoformat(last) + timedelta(days=1)
        else:
            start = yesterday

    if start > yesterday:
        log("Already up to date.")
        con.close()
        sys.exit(0)

    run(start, yesterday, con)
    con.close()

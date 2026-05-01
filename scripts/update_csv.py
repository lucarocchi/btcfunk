"""
Aggiorna SQLite (tabella ohlc) con le candele più recenti da Kraken API.
Progettato per girare ogni 7 minuti via cron.
"""
import os, sqlite3
import requests
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "../btcfunk.sqlite")

PAIRS = [
    {"interval": 1440, "key": "XXBTZUSD"},
    {"interval": 240,  "key": "XXBTZUSD"},
    {"interval": 60,   "key": "XXBTZUSD"},
    {"interval": 15,   "key": "XXBTZUSD"},
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def _init_ohlc(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS ohlc (
            tf     INTEGER NOT NULL,
            ts     INTEGER NOT NULL,
            open   REAL,
            high   REAL,
            low    REAL,
            close  REAL,
            vol    REAL,
            trades INTEGER,
            PRIMARY KEY (tf, ts)
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_ohlc_tf_ts ON ohlc (tf, ts)")
    con.commit()

def _since(con, tf):
    row = con.execute("SELECT MAX(ts) FROM ohlc WHERE tf = ?", (tf,)).fetchone()
    return row[0] if row[0] else 0

def fetch_and_sync(pair, con):
    tf    = pair["interval"]
    since = _since(con, tf)
    if since == 0:
        log(f"  tf={tf}: nessun dato in SQLite — skip")
        return

    url = f"https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval={tf}&since={since}"
    try:
        data = requests.get(url, timeout=15).json()
    except Exception as e:
        log(f"  tf={tf}: errore HTTP — {e}")
        return

    if "result" not in data or data.get("error"):
        log(f"  tf={tf}: API error — {data.get('error', 'no result')}")
        return

    bars = data["result"].get(pair["key"], [])
    new_bars = [b for b in bars if int(b[0]) > since]

    if not new_bars:
        return

    rows = [(tf, int(b[0]), float(b[1]), float(b[2]),
             float(b[3]), float(b[4]), float(b[6]), int(b[7])) for b in new_bars]
    con.executemany(
        "INSERT OR REPLACE INTO ohlc (tf, ts, open, high, low, close, vol, trades) VALUES (?,?,?,?,?,?,?,?)",
        rows
    )
    con.commit()

    last_dt = datetime.fromtimestamp(int(new_bars[-1][0]), tz=timezone.utc).strftime("%d/%m/%Y %H:%M")
    log(f"  tf={tf}: +{len(new_bars)} candele → {last_dt}")

def _resample(con, src_tf, dst_tf, limit=200):
    rows = con.execute(
        "SELECT ts, open, high, low, close, vol, trades FROM ohlc WHERE tf = ? ORDER BY ts DESC LIMIT ?",
        (src_tf, limit)
    ).fetchall()
    if not rows:
        return 0
    rows = sorted(rows, key=lambda x: x[0])
    period = dst_tf * 60
    buckets = {}
    for ts, o, h, l, c, vol, trades in rows:
        bk = (ts // period) * period
        if bk not in buckets:
            buckets[bk] = [bk, o, h, l, c, vol, trades]
        else:
            b = buckets[bk]
            if h > b[2]: b[2] = h
            if l < b[3]: b[3] = l
            b[4] = c; b[5] += vol; b[6] += trades
    out = [(dst_tf, b[0], b[1], b[2], b[3], b[4], b[5], b[6])
           for b in sorted(buckets.values(), key=lambda x: x[0])]
    con.executemany(
        "INSERT OR REPLACE INTO ohlc (tf, ts, open, high, low, close, vol, trades) VALUES (?,?,?,?,?,?,?,?)",
        out
    )
    con.commit()
    return len(out)

if __name__ == "__main__":
    con = sqlite3.connect(DB_PATH)
    _init_ohlc(con)

    for pair in PAIRS:
        fetch_and_sync(pair, con)
    n30  = _resample(con, src_tf=15,  dst_tf=30,  limit=200)
    n720 = _resample(con, src_tf=240, dst_tf=720, limit=200)
    log(f"  tf=30: {n30} candele · tf=720: {n720} candele (resample)")

    con.close()

"""
Aggiorna i CSV storici e SQLite (tabella ohlc) con le candele più recenti da Kraken API.
Progettato per girare ogni 7 minuti via cron.
- Sorgente di verità: SQLite (ohlc)
- CSV: backup su disco
- TF piccoli (5m, 1m): non memorizzati, vanno chiamati live dall'API Kraken
"""
import csv, os, sqlite3
import requests
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "../app/data")
DB_PATH    = os.path.join(SCRIPT_DIR, "../btcfunk.sqlite")

PAIRS = [
    {"interval": 1440, "key": "XXBTZUSD", "file": "raw/XBTUSD_1440.csv"},
    {"interval": 240,  "key": "XXBTZUSD", "file": "raw/XBTUSD_240.csv"},
    {"interval": 60,   "key": "XXBTZUSD", "file": "raw/XBTUSD_60.csv"},
    {"interval": 15,   "key": "XXBTZUSD", "file": "raw/XBTUSD_15.csv"},
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

def _since_from_sqlite(con, tf):
    row = con.execute("SELECT MAX(ts) FROM ohlc WHERE tf = ?", (tf,)).fetchone()
    return row[0] if row[0] else 0

def _since_from_csv(path):
    last = 0
    if not os.path.exists(path): return 0
    with open(path, newline="") as f:
        for row in csv.reader(f):
            try:
                ts = int(row[0])
                if ts > last: last = ts
            except: pass
    return last

def fetch_and_sync(pair, con):
    tf   = pair["interval"]
    path = os.path.join(DATA_DIR, pair["file"])

    since = _since_from_sqlite(con, tf)
    if since == 0:
        since = _since_from_csv(path)
    if since == 0:
        log(f"  tf={tf}: nessun dato locale — skip")
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

    bars = data["result"].get(pair["key"], [])  # include ultima candela parziale, verrà aggiornata al prossimo run
    new_bars = [b for b in bars if int(b[0]) > since]

    if not new_bars:
        return

    # append CSV (backup)
    if os.path.exists(path):
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            for b in new_bars:
                w.writerow([int(b[0]), float(b[1]), float(b[2]),
                             float(b[3]), float(b[4]), float(b[6]), int(b[7])])

    # sync SQLite (solo nuove righe)
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
    """Resampla le ultime `limit` candele da src_tf a dst_tf."""
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

def resample_30m(con):
    n = _resample(con, src_tf=15, dst_tf=30, limit=200)
    log(f"  tf=30:  {n} candele aggiornate (resample ultimi 200x15m)")

def resample_720m(con):
    n = _resample(con, src_tf=240, dst_tf=720, limit=200)
    log(f"  tf=720: {n} candele aggiornate (resample ultimi 200x240m)")

def bootstrap_from_csv(con):
    """Import iniziale: legge i CSV esistenti e popola SQLite. Salta se già presente."""
    tf_map = [
        (1440, "raw/XBTUSD_1440.csv"),
        (720,  "raw/XBTUSD_720.csv"),
        (240,  "raw/XBTUSD_240.csv"),
        (60,   "raw/XBTUSD_60.csv"),
        (15,   "raw/XBTUSD_15.csv"),
    ]
    for tf, fname in tf_map:
        existing = con.execute("SELECT COUNT(*) FROM ohlc WHERE tf = ?", (tf,)).fetchone()[0]
        if existing > 0:
            continue
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            continue
        rows = []
        with open(path, newline="") as f:
            for row in csv.reader(f):
                try:
                    rows.append((tf, int(row[0]), float(row[1]), float(row[2]),
                                  float(row[3]), float(row[4]), float(row[5]), int(row[6])))
                except: pass
        con.executemany(
            "INSERT OR REPLACE INTO ohlc (tf, ts, open, high, low, close, vol, trades) VALUES (?,?,?,?,?,?,?,?)",
            rows
        )
        con.commit()
        log(f"  bootstrap tf={tf}: {len(rows)} righe da CSV")

if __name__ == "__main__":
    con = sqlite3.connect(DB_PATH)
    _init_ohlc(con)
    bootstrap_from_csv(con)

    for pair in PAIRS:
        fetch_and_sync(pair, con)
    resample_30m(con)
    resample_720m(con)

    con.close()

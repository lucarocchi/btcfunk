"""
Aggiornamento giornaliero da Kraken API (gratuito, nessuna credenziale).

Sostituisce la parte prezzi di daily_update.py (BigQuery, disabilitato per costi):
  1. sincronizza le candele daily (tf=1440) della coppia XBTUSD
  2. rigenera btc_prices dalle candele daily (usata da MVRV, RHODL, LTH/STH, Z-Score)
  3. segnala eventuali giorni mancanti nella serie

Uso:
    python3 scripts/update_kraken_daily.py            # incrementale (ultimi giorni)
    python3 scripts/update_kraken_daily.py --rebuild  # rigenera btc_prices da tutto lo storico ohlc

Cron:
    10 6 * * * cd /var/www/btcfunk/app && venv/bin/python3 scripts/update_kraken_daily.py >> /var/log/btcfunk_kraken.log 2>&1
"""
import os, sys, sqlite3
import requests
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "../btcfunk.sqlite")

KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"
PAIR        = "XBTUSD"
PAIR_KEY    = "XXBTZUSD"
TF          = 1440          # candele daily
OVERLAP_DAYS = 3            # riscarica gli ultimi N giorni: l'ultima candela è sempre parziale


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def _init(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS ohlc (
            tf     INTEGER NOT NULL,
            ts     INTEGER NOT NULL,
            open   REAL, high REAL, low REAL, close REAL,
            vol    REAL, trades INTEGER,
            PRIMARY KEY (tf, ts)
        )
    """)
    con.execute("CREATE TABLE IF NOT EXISTS btc_prices (day TEXT PRIMARY KEY, price REAL)")
    con.commit()


def sync_daily_candles(con):
    """Scarica le candele daily da Kraken e le inserisce in ohlc (tf=1440)."""
    row = con.execute("SELECT MAX(ts) FROM ohlc WHERE tf = ?", (TF,)).fetchone()
    last_ts = row[0] or 0
    since   = max(0, last_ts - OVERLAP_DAYS * 86400)

    try:
        r = requests.get(KRAKEN_OHLC,
                         params={"pair": PAIR, "interval": TF, "since": since},
                         timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log(f"ERRORE HTTP Kraken: {e}")
        return 0

    if data.get("error"):
        log(f"ERRORE API Kraken: {data['error']}")
        return 0

    result = data.get("result", {})
    candles = result.get(PAIR_KEY) or result.get(PAIR) or []
    if not candles:
        log("Kraken: nessuna candela restituita")
        return 0

    rows = [(TF, int(c[0]), float(c[1]), float(c[2]), float(c[3]),
             float(c[4]), float(c[6]), int(c[7])) for c in candles]
    con.executemany(
        "INSERT OR REPLACE INTO ohlc (tf, ts, open, high, low, close, vol, trades) "
        "VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()

    new = sum(1 for c in candles if int(c[0]) > last_ts)
    last_dt = datetime.fromtimestamp(int(candles[-1][0]), tz=timezone.utc).strftime("%Y-%m-%d")
    log(f"ohlc tf=1440: {len(rows)} candele scritte ({new} nuove) → ultima {last_dt}")
    return new


def sync_prices(con, rebuild=False):
    """Rigenera btc_prices dalle candele daily già in ohlc."""
    if rebuild:
        rows = con.execute(
            "SELECT DATE(ts,'unixepoch'), close FROM ohlc WHERE tf=? ORDER BY ts", (TF,)
        ).fetchall()
    else:
        row = con.execute("SELECT MAX(day) FROM btc_prices").fetchone()
        if row[0]:
            since_day = (datetime.strptime(row[0], "%Y-%m-%d")
                         - timedelta(days=OVERLAP_DAYS)).strftime("%Y-%m-%d")
        else:
            since_day = "1970-01-01"
        rows = con.execute(
            "SELECT DATE(ts,'unixepoch'), close FROM ohlc WHERE tf=? AND DATE(ts,'unixepoch') >= ? "
            "ORDER BY ts", (TF, since_day)
        ).fetchall()

    if not rows:
        log("btc_prices: nessuna riga da aggiornare")
        return

    con.executemany("INSERT OR REPLACE INTO btc_prices (day, price) VALUES (?,?)", rows)
    con.commit()

    last = con.execute("SELECT day, price FROM btc_prices ORDER BY day DESC LIMIT 1").fetchone()
    total = con.execute("SELECT COUNT(*) FROM btc_prices").fetchone()[0]
    log(f"btc_prices: {len(rows)} righe scritte · totale {total} · ultima {last[0]} = ${last[1]:,.0f}")


def check_gaps(con, days=90):
    """Segnala giorni mancanti negli ultimi N giorni della serie prezzi."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    have  = {r[0] for r in con.execute("SELECT day FROM btc_prices WHERE day >= ?", (since,))}
    today = datetime.now(timezone.utc).date()
    want  = {(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, days + 1)}
    missing = sorted(want - have)
    if missing:
        log(f"ATTENZIONE: {len(missing)} giorni mancanti negli ultimi {days}: "
            f"{', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}")
    else:
        log(f"Nessun buco negli ultimi {days} giorni")


if __name__ == "__main__":
    rebuild = "--rebuild" in sys.argv
    con = sqlite3.connect(DB_PATH)
    _init(con)
    sync_daily_candles(con)
    sync_prices(con, rebuild=rebuild)
    check_gaps(con)
    con.close()

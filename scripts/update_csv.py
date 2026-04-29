"""
Aggiorna i CSV storici con le candele più recenti da Kraken API.
Eseguire giornalmente via cron.
"""
import csv, json, os
import requests
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "../app/data")

PAIRS = [
    {"ohlc_pair": "XBTUSD", "ohlc_key": "XXBTZUSD", "interval": 1440, "file": "raw/XBTUSD_1440.csv"},
    {"ohlc_pair": "XBTUSD", "ohlc_key": "XXBTZUSD", "interval": 240,  "file": "raw/XBTUSD_240.csv"},
    {"ohlc_pair": "XBTUSD", "ohlc_key": "XXBTZUSD", "interval": 60,   "file": "raw/XBTUSD_60.csv"},
    {"ohlc_pair": "XBTUSD", "ohlc_key": "XXBTZUSD", "interval": 15,   "file": "raw/XBTUSD_15.csv"},
    {"ohlc_pair": "XBTUSD", "ohlc_key": "XXBTZUSD", "interval": 5,    "file": "raw/XBTUSD_5.csv"},
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def last_ts(path):
    last = 0
    if not os.path.exists(path): return 0
    with open(path, newline="") as f:
        for row in csv.reader(f):
            try:
                ts = int(row[0])
                if ts > last: last = ts
            except: pass
    return last

def fetch_and_append(pair):
    path = os.path.join(DATA_DIR, pair["file"])
    since = last_ts(path)
    if since == 0:
        log(f"⚠️ {pair['file']} non trovato — skip")
        return

    url = f"https://api.kraken.com/0/public/OHLC?pair={pair['ohlc_pair']}&interval={pair['interval']}&since={since}"
    data = requests.get(url, timeout=15).json()

    bars = data["result"][pair["ohlc_key"]][:-1]  # escludi candela incompleta
    new_bars = [b for b in bars if int(b[0]) > since]

    if not new_bars:
        log(f"  {pair['file']}: nessuna nuova candela")
        return

    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        for b in new_bars:
            w.writerow([int(b[0]), float(b[1]), float(b[2]), float(b[3]), float(b[4]), float(b[6]), int(b[7])])

    last_dt = datetime.fromtimestamp(int(new_bars[-1][0]), tz=timezone.utc).strftime("%d/%m/%Y %H:%M")
    log(f"  {pair['file']}: +{len(new_bars)} candele → ultima {last_dt}")

def resample_from_15m():
    """Rigenera 30min e 60min dal CSV 15min aggiornato."""
    src = os.path.join(DATA_DIR, "raw/XBTUSD_15.csv")
    if not os.path.exists(src):
        log("⚠️ raw/XBTUSD_15.csv non trovato — skip resample")
        return
    # 60min e 240min vengono aggiornati direttamente dall'API Kraken — non sovrascrivere
    targets = {"raw/XBTUSD_30.csv": 2}
    bars_15 = []
    with open(src) as f:
        for row in csv.reader(f):
            ts, o, h, l, c, vol, trades = row
            bars_15.append({"ts": int(ts), "open": float(o), "high": float(h),
                             "low": float(l), "close": float(c), "vol": float(vol), "trades": int(trades)})
    for filename, n in targets.items():
        period = n * 900
        buckets = {}
        for b in bars_15:
            bk_ts = (b["ts"] // period) * period
            if bk_ts not in buckets:
                buckets[bk_ts] = dict(b); buckets[bk_ts]["ts"] = bk_ts
            else:
                bk = buckets[bk_ts]
                if b["high"] > bk["high"]: bk["high"] = b["high"]
                if b["low"]  < bk["low"]:  bk["low"]  = b["low"]
                bk["close"] = b["close"]; bk["vol"] += b["vol"]; bk["trades"] += b["trades"]
        out = sorted(buckets.values(), key=lambda x: x["ts"])
        with open(os.path.join(DATA_DIR, filename), "w", newline="") as f:
            w = csv.writer(f)
            for b in out:
                w.writerow([b["ts"], f"{b['open']:.1f}", f"{b['high']:.1f}",
                             f"{b['low']:.1f}", f"{b['close']:.1f}", f"{b['vol']:.8f}", b["trades"]])
        log(f"  {filename}: {len(out)} candele (resample da 15min)")

def check_and_fill_gaps(min_days=20):
    """
    Verifica che le ultime min_days candele daily siano contigue (nessun gap).
    Se trova buchi, scarica le candele mancanti da Kraken e le inserisce.
    """
    path = os.path.join(DATA_DIR, "raw/XBTUSD_1440.csv")
    if not os.path.exists(path):
        log("⚠️ check_and_fill_gaps: CSV non trovato")
        return

    # Leggi tutte le candele
    rows = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            try: rows.append((int(row[0]), row))
            except: pass
    rows.sort(key=lambda x: x[0])

    if len(rows) < min_days:
        log(f"⚠️ check_and_fill_gaps: solo {len(rows)} candele nel CSV")
        return

    # Controlla gap negli ultimi min_days + buffer
    recent = rows[-(min_days + 5):]
    expected_interval = 86400  # 1 giorno in secondi
    gaps = []
    for i in range(1, len(recent)):
        diff = recent[i][0] - recent[i-1][0]
        if diff > expected_interval + 3600:  # tolleranza 1h per DST etc.
            missing_ts = recent[i-1][0] + expected_interval
            gaps.append(missing_ts)
            log(f"⚠️ Gap trovato: manca candela intorno a {datetime.fromtimestamp(missing_ts, tz=timezone.utc).strftime('%Y-%m-%d')}")

    if not gaps:
        log(f"  CSV daily: nessun gap negli ultimi {min_days} giorni ✓")
        return

    # Scarica le candele mancanti — usa since del primo gap - 2 giorni
    since = gaps[0] - 86400 * 2
    url = f"https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440&since={since}"
    try:
        data = requests.get(url, timeout=15).json()
        bars = data["result"]["XXBTZUSD"][:-1]
        existing_ts = {r[0] for r in rows}
        new_bars = [b for b in bars if int(b[0]) not in existing_ts]
        if new_bars:
            with open(path, "a", newline="") as f:
                w = csv.writer(f)
                for b in new_bars:
                    w.writerow([int(b[0]), float(b[1]), float(b[2]), float(b[3]),
                                 float(b[4]), float(b[6]), int(b[7])])
            log(f"  Gap riempito: +{len(new_bars)} candele inserite")
        else:
            log("⚠️ Gap non risolvibile — candele non trovate su Kraken")
    except Exception as e:
        log(f"⚠️ Errore fetch gap: {e}")


def check_daily_freshness():
    """Verifica che il CSV daily abbia la candela di ieri."""
    path = os.path.join(DATA_DIR, "raw/XBTUSD_1440.csv")
    last = last_ts(path)
    if last == 0:
        log("⚠️ XBTUSD_1440.csv non trovato")
        return
    last_dt = datetime.fromtimestamp(last, tz=timezone.utc).date()
    today   = datetime.now(timezone.utc).date()
    from datetime import timedelta
    yesterday = today - timedelta(days=1)
    if last_dt < yesterday:
        log(f"⚠️ CSV daily outdated: ultima candela {last_dt}, atteso {yesterday}")
    else:
        log(f"  CSV daily OK: ultima candela {last_dt}")

if __name__ == "__main__":
    log("=== Update CSV storici ===")
    for pair in PAIRS:
        fetch_and_append(pair)
    resample_from_15m()
    check_and_fill_gaps(min_days=20)  # garantisce 20 candele continue per BB
    check_daily_freshness()
    log("Done.")

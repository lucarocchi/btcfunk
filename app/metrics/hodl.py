import sqlite3, json
from datetime import datetime, timezone, date

DB_PATH = "btcfunk.sqlite"
CACHE_TTL_HOURS = 24

BANDS = [
    ("< 1 day",   0,    1),
    ("1d – 1w",   1,    7),
    ("1w – 1m",   7,    30),
    ("1m – 3m",   30,   90),
    ("3m – 6m",   90,   180),
    ("6m – 1y",   180,  365),
    ("1y – 2y",   365,  730),
    ("2y – 3y",   730,  1095),
    ("3y – 5y",   1095, 1825),
    ("5y – 7y",   1825, 2555),
    ("7y – 10y",  2555, 3650),
    ("> 10y",     3650, None),
]


def _cache_get(con, key):
    row = con.execute("SELECT value, updated_at FROM cache WHERE key=?", (key,)).fetchone()
    if not row: return None
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(row[1])).total_seconds() / 3600
    return json.loads(row[0]) if age < CACHE_TTL_HOURS else None


def _cache_set(con, key, value):
    con.execute("INSERT OR REPLACE INTO cache (key,value,updated_at) VALUES (?,?,?)",
                (key, json.dumps(value), datetime.now(timezone.utc).isoformat()))
    con.commit()


def get_hodl():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
    cached = _cache_get(con, "hodl")
    if cached: return cached

    utxos = {r[0]: float(r[1]) for r in
             con.execute("SELECT creation_day, btc_value FROM utxo_snapshot").fetchall()}
    if not utxos:
        return {"error": "utxo_snapshot vuota — esegui migrate_history.py"}

    today     = date.today()
    total_btc = sum(utxos.values())

    band_totals = {label: 0.0 for label, _, _ in BANDS}
    for creation_day_str, btc in utxos.items():
        try:
            creation_dt = date.fromisoformat(creation_day_str)
        except ValueError:
            continue
        age = (today - creation_dt).days
        for label, lo, hi in BANDS:
            if age >= lo and (hi is None or age < hi):
                band_totals[label] += btc
                break

    bands = [
        {
            "label": label,
            "btc":   round(band_totals[label], 2),
            "pct":   round(band_totals[label] / total_btc * 100, 2) if total_btc else 0,
        }
        for label, _, _ in BANDS
    ]

    lth_pct = sum(b["pct"] for b in bands if b["label"] in
                  {"1y – 2y", "2y – 3y", "3y – 5y", "5y – 7y", "7y – 10y", "> 10y"})

    result = {
        "lth_pct":    round(lth_pct, 2),
        "sth_pct":    round(100 - lth_pct, 2),
        "total_btc":  round(total_btc, 2),
        "bands":      bands,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(con, "hodl", result)
    return result

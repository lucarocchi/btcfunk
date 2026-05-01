import sqlite3
from datetime import datetime, timezone, date

DB_PATH = "btcfunk.sqlite"

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


def get_hodl():
    con = sqlite3.connect(DB_PATH)

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

    return {
        "lth_pct":    round(lth_pct, 2),
        "sth_pct":    round(100 - lth_pct, 2),
        "total_btc":  round(total_btc, 2),
        "bands":      bands,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

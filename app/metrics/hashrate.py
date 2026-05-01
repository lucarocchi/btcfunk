import sqlite3
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"


def _ma(values_dict, n):
    days = sorted(values_dict)
    out  = {}
    for i, d in enumerate(days):
        w = days[max(0, i - n + 1):i + 1]
        out[d] = sum(values_dict[x] for x in w) / len(w)
    return out


def get_hashrate():
    con = sqlite3.connect(DB_PATH)

    rows = con.execute("""
        SELECT day, hashrate_eh, block_count FROM hashrate_daily
        WHERE day >= date('now', '-365 days') ORDER BY day
    """).fetchall()

    labels       = [r[0] for r in rows]
    values       = [r[1] for r in rows]
    block_counts = [r[2] for r in rows]

    all_hr = {r[0]: r[1] for r in
              con.execute("SELECT day, hashrate_eh FROM hashrate_daily ORDER BY day").fetchall()}
    ma14 = _ma(all_hr, 14)

    return {
        "hashrate_eh": values[-1]       if values      else None,
        "ma14_eh":     round(ma14.get(labels[-1], 0), 4) if labels else None,
        "block_count": block_counts[-1] if block_counts else None,
        "labels":      labels,
        "values":      values,
        "updated_at":  datetime.now(timezone.utc).isoformat(),
    }

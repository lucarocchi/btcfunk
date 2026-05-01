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


def get_tx_stats():
    con = sqlite3.connect(DB_PATH)

    rows = con.execute("""
        SELECT day, tx_count, volume, fees FROM tx_stats_daily
        WHERE day >= date('now', '-365 days') ORDER BY day
    """).fetchall()

    labels    = [r[0] for r in rows]
    tx_counts = [r[1] for r in rows]
    volumes   = [round(r[2], 2) for r in rows]
    fees      = [round(r[3], 6) for r in rows]
    avg_fees  = [round(r[3] / r[1], 8) if r[1] else 0 for r in rows]

    all_tx = {r[0]: r[1] for r in
              con.execute("SELECT day, tx_count FROM tx_stats_daily ORDER BY day").fetchall()}
    ma30 = _ma(all_tx, 30)

    return {
        "tx_count":      tx_counts[-1]  if tx_counts else None,
        "tx_count_ma30": round(ma30.get(labels[-1], 0)) if labels else None,
        "volume_btc":    volumes[-1]    if volumes   else None,
        "avg_fee_btc":   avg_fees[-1]   if avg_fees  else None,
        "labels":        labels,
        "tx_counts":     tx_counts,
        "volumes":       volumes,
        "avg_fees":      avg_fees,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }

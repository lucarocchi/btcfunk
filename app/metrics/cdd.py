import sqlite3
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"


def _moving_avg(values_dict, n=90):
    days = sorted(values_dict)
    result = {}
    for i, d in enumerate(days):
        window = days[max(0, i - n + 1):i + 1]
        result[d] = sum(values_dict[w] for w in window) / len(window)
    return result


def get_cdd():
    con = sqlite3.connect(DB_PATH)

    rows = con.execute("""
        SELECT day, cdd FROM cdd_daily
        WHERE day >= date('now', '-365 days')
        ORDER BY day
    """).fetchall()

    labels  = [r[0] for r in rows]
    values  = [r[1] for r in rows]
    current = values[-1] if values else None

    all_rows = con.execute("SELECT day, cdd FROM cdd_daily ORDER BY day").fetchall()
    ma = _moving_avg({r[0]: r[1] for r in all_rows}, n=90)
    ma_current = ma.get(labels[-1]) if labels else None

    return {
        "current":    current,
        "ma90":       round(ma_current, 2) if ma_current else None,
        "labels":     labels,
        "values":     values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

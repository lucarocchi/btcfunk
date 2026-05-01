import sqlite3
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"


def get_sopr():
    con = sqlite3.connect(DB_PATH)

    rows = con.execute("""
        SELECT day, sopr FROM sopr_daily
        WHERE day >= date('now', '-365 days')
        ORDER BY day
    """).fetchall()

    labels  = [r[0] for r in rows]
    values  = [r[1] for r in rows]
    current = values[-1] if values else None

    return {
        "current":    current,
        "labels":     labels,
        "values":     values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

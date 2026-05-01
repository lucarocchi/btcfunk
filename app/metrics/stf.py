import sqlite3, math
from collections import deque
from datetime import datetime, timezone, timedelta

DB_PATH = "btcfunk.sqlite"


def _sf_model_price(sf):
    if sf <= 0:
        return None
    # PlanB approximation: price = 10^(2.66 × log10(SF) − 1.59)
    return round(10 ** (2.66 * math.log10(sf) - 1.59), 2)


def get_stf():
    con = sqlite3.connect(DB_PATH)

    row = con.execute(
        "SELECT SUM(revenue) FROM puell_daily WHERE day >= date('now', '-365 days')"
    ).fetchone()
    annual_issuance = row[0] if row and row[0] else None
    if not annual_issuance:
        return {"error": "run /api/puell first to populate puell_daily"}

    from app.metrics.mvrv import get_mvrv
    d     = get_mvrv()
    supply        = d["market_cap"] / d["current_price"]
    current_price = d["current_price"]

    sf             = round(supply / annual_issuance, 2)
    model_price    = _sf_model_price(sf)
    deviation_pct  = round((current_price - model_price) / model_price * 100, 1) if model_price else None

    # Historical SF — rolling 365d issuance window
    all_rows = con.execute(
        "SELECT day, revenue FROM puell_daily ORDER BY day"
    ).fetchall()
    all_puell = {r[0]: r[1] for r in all_rows}
    days = sorted(all_puell)

    cutoff  = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    window  = deque()
    win_sum = 0.0
    labels, values = [], []

    for day in days:
        dt = datetime.strptime(day, "%Y-%m-%d")
        window.append((dt, all_puell[day]))
        win_sum += all_puell[day]
        while window and (dt - window[0][0]).days > 365:
            win_sum -= window.popleft()[1]
        if day >= cutoff and win_sum > 0:
            labels.append(day)
            values.append(round(supply / win_sum, 2))

    return {
        "sf":              sf,
        "model_price":     model_price,
        "current_price":   current_price,
        "deviation_pct":   deviation_pct,
        "annual_issuance": round(annual_issuance, 2),
        "labels":          labels,
        "values":          values,
        "updated_at":      datetime.now(timezone.utc).isoformat(),
    }

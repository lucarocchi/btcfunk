import sqlite3
from datetime import datetime, timezone, timedelta

DB_PATH = "btcfunk.sqlite"


def _moving_avg(values_dict, n):
    days = sorted(values_dict)
    result = {}
    for i, d in enumerate(days):
        window = days[max(0, i - n + 1):i + 1]
        result[d] = sum(values_dict[w] for w in window) / len(window)
    return result


def get_puell():
    con = sqlite3.connect(DB_PATH)

    all_rows     = con.execute("SELECT day, revenue FROM puell_daily ORDER BY day").fetchall()
    revenue_dict = {r[0]: r[1] for r in all_rows}
    ma365        = _moving_avg(revenue_dict, 365)

    cutoff     = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    chart_days = sorted(d for d in revenue_dict if d >= cutoff)
    labels     = chart_days
    values     = [round(revenue_dict[d] / ma365[d], 4) if ma365.get(d) else None for d in chart_days]

    current_day     = chart_days[-1]  if chart_days else None
    current_puell   = values[-1]      if values     else None
    current_revenue = round(revenue_dict.get(current_day, 0), 2) if current_day else None
    current_ma365   = round(ma365.get(current_day, 0), 2)        if current_day else None

    return {
        "puell":         current_puell,
        "daily_revenue": current_revenue,
        "ma365_revenue": current_ma365,
        "labels":        labels,
        "values":        values,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }

import sqlite3, requests
from datetime import datetime, timezone, timedelta

DB_PATH = "btcfunk.sqlite"


def _moving_avg(values_dict, n=28):
    days = sorted(values_dict)
    result = {}
    for i, d in enumerate(days):
        window = days[max(0, i - n + 1):i + 1]
        result[d] = sum(values_dict[w] for w in window) / len(window)
    return result


def get_nvt():
    con = sqlite3.connect(DB_PATH)

    rows = con.execute(
        "SELECT day, btc_volume FROM nvt_daily WHERE day >= date('now','-430 days') ORDER BY day"
    ).fetchall()

    vol = {day: btc for day, btc in rows}
    ma  = _moving_avg(vol, n=28)

    supply_row = con.execute("SELECT SUM(btc_value) FROM utxo_snapshot").fetchone()
    circulating_supply = supply_row[0] if supply_row and supply_row[0] else None

    r = requests.get("https://api.kraken.com/0/public/Ticker", params={"pair": "XBTUSD"}, timeout=10)
    current_price = float(r.json()["result"][list(r.json()["result"])[0]]["c"][0])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    labels, values = [], []
    for day in sorted(ma):
        if day < cutoff or not circulating_supply or ma[day] == 0:
            continue
        labels.append(day)
        values.append(round(circulating_supply / ma[day], 2))

    current_nvt = None
    if labels and circulating_supply and ma.get(labels[-1]):
        current_nvt = round(circulating_supply / ma[labels[-1]], 2)

    return {
        "nvt":           current_nvt,
        "current_price": current_price,
        "labels":        labels,
        "values":        values,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }

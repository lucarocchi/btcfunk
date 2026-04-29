import sqlite3
from datetime import datetime, timezone, timedelta

DB_PATH = "mvrv_cache.sqlite"

# (label, lo_days, hi_days) — matches hodl.py
BANDS_META = [
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


def _nearest_price(prices, target_date_str):
    """Return closest price in prices dict to target_date_str (YYYY-MM-DD)."""
    if target_date_str in prices:
        return prices[target_date_str]
    from datetime import date
    target = date.fromisoformat(target_date_str)
    best, best_delta = None, None
    for d, p in prices.items():
        try:
            delta = abs((date.fromisoformat(d) - target).days)
        except ValueError:
            continue
        if best_delta is None or delta < best_delta:
            best, best_delta = p, delta
    return best


def get_rhodl():
    from app.metrics.hodl import get_hodl
    d = get_hodl()

    bands_by_label = {b["label"]: b for b in d["bands"]}

    # RHODL Ratio: 1y–2y band BTC / 1d–1w band BTC
    b_1y2y = bands_by_label.get("1y – 2y", {}).get("btc", 0)
    b_1d1w = bands_by_label.get("1d – 1w", {}).get("btc", 0)
    rhodl  = round(b_1y2y / b_1d1w, 2) if b_1d1w > 0 else None

    # Supply in Profit: estimate acquisition price as price at midpoint age
    con = sqlite3.connect(DB_PATH)
    prices = {r[0]: r[1] for r in con.execute("SELECT day, price FROM btc_prices").fetchall()}
    con.close()

    from app.metrics.mvrv import _fetch_live_price
    current_price = _fetch_live_price()
    today = datetime.now(timezone.utc).date()

    profit_btc = 0.0
    bands_profit = []  # for frontend coloring
    total_btc = d.get("total_btc", 0)

    for label, lo, hi in BANDS_META:
        mid = (lo + (hi if hi is not None else lo * 2)) / 2
        acq_date = (today - timedelta(days=mid)).isoformat()
        acq_price = _nearest_price(prices, acq_date)
        btc = bands_by_label.get(label, {}).get("btc", 0)
        pct = bands_by_label.get(label, {}).get("pct", 0)
        in_profit = acq_price is not None and acq_price < current_price
        if in_profit:
            profit_btc += btc
        bands_profit.append({
            "label":     label,
            "btc":       btc,
            "pct":       pct,
            "in_profit": in_profit,
            "acq_price": round(acq_price, 0) if acq_price else None,
        })

    supply_in_profit_pct = round(profit_btc / total_btc * 100, 2) if total_btc else None

    return {
        "rhodl":                rhodl,
        "supply_in_profit_pct": supply_in_profit_pct,
        "profit_btc":           round(profit_btc, 2),
        "total_btc":            round(total_btc, 2),
        "bands_profit":         bands_profit,
        "current_price":        current_price,
        "updated_at":           d["updated_at"],
    }

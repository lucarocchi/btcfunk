import sqlite3, json
from datetime import datetime, timezone, timedelta

DB_PATH = "mvrv_cache.sqlite"
CACHE_TTL_HOURS = 24

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
LTH_LABELS = {"1y – 2y", "2y – 3y", "3y – 5y", "5y – 7y", "7y – 10y", "> 10y"}


def _nearest_price(prices, target):
    if target in prices:
        return prices[target]
    from datetime import date
    t = date.fromisoformat(target)
    best, best_d = None, None
    for d, p in prices.items():
        try:
            delta = abs((date.fromisoformat(d) - t).days)
        except ValueError:
            continue
        if best_d is None or delta < best_d:
            best, best_d = p, delta
    return best


def _cache_get(con, key):
    row = con.execute("SELECT value, updated_at FROM cache WHERE key=?", (key,)).fetchone()
    if not row: return None
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(row[1])).total_seconds() / 3600
    return json.loads(row[0]) if age < CACHE_TTL_HOURS else None


def _cache_set(con, key, value):
    con.execute("INSERT OR REPLACE INTO cache (key,value,updated_at) VALUES (?,?,?)",
                (key, json.dumps(value), datetime.now(timezone.utc).isoformat()))
    con.commit()


def get_lth_sth():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
    cached = _cache_get(con, "lth_sth")
    if cached:
        return cached

    from app.metrics.hodl import get_hodl
    d = get_hodl()

    prices = {r[0]: r[1] for r in con.execute(
        "SELECT day, price FROM btc_prices").fetchall()}
    today = datetime.now(timezone.utc).date()

    lth_btc = sth_btc = lth_rc = sth_rc = 0.0
    bands_by_label = {b["label"]: b for b in d["bands"]}

    for label, lo, hi in BANDS_META:
        mid      = (lo + (hi if hi is not None else lo * 2)) / 2
        acq_date = (today - timedelta(days=mid)).isoformat()
        price    = _nearest_price(prices, acq_date) or 0
        btc      = bands_by_label.get(label, {}).get("btc", 0)
        if label in LTH_LABELS:
            lth_btc += btc
            lth_rc  += btc * price
        else:
            sth_btc += btc
            sth_rc  += btc * price

    result = {
        "lth_supply":         round(lth_btc, 2),
        "sth_supply":         round(sth_btc, 2),
        "lth_realized_price": round(lth_rc / lth_btc, 2) if lth_btc else None,
        "sth_realized_price": round(sth_rc / sth_btc, 2) if sth_btc else None,
        "total_btc":          d["total_btc"],
        "bands":              d["bands"],
        "updated_at":         d["updated_at"],
    }
    _cache_set(con, "lth_sth", result)
    return result

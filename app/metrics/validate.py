import requests
import sqlite3
import json
from datetime import datetime, timezone, timedelta

DB_PATH = "mvrv_cache.sqlite"
CM_URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"


def _our_mvrv():
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT value FROM cache WHERE key = 'realized_cap'").fetchone()
    sopr_row = con.execute("SELECT sopr FROM sopr_daily ORDER BY day DESC LIMIT 1").fetchone()
    con.close()
    return (
        json.loads(row[0]) if row else None,
        sopr_row[0] if sopr_row else None,
    )


def _cm_mvrv():
    since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    r = requests.get(CM_URL, params={"assets": "btc", "metrics": "CapMVRVCur", "start_time": since}, timeout=10)
    r.raise_for_status()
    rows = r.json().get("data", [])
    if not rows:
        return None, None
    latest = rows[-1]
    return float(latest["CapMVRVCur"]), latest["time"][:10]


def get_validation():
    cached, our_sopr = _our_mvrv()
    our_mvrv_val = None

    if cached and "realized_cap" in cached and "circulating_supply" in cached:
        r = requests.get("https://api.kraken.com/0/public/Ticker", params={"pair": "XBTUSD"}, timeout=10)
        price = float(r.json()["result"][list(r.json()["result"].keys())[0]]["c"][0])
        market_cap = cached["circulating_supply"] * price
        our_mvrv_val = round(market_cap / cached["realized_cap"], 4) if cached["realized_cap"] else None

    cm_val, cm_date = _cm_mvrv()

    mvrv_diff = None
    if our_mvrv_val and cm_val:
        mvrv_diff = round((our_mvrv_val - cm_val) / cm_val * 100, 2)

    sopr_ok = our_sopr is not None and 0.5 <= our_sopr <= 3.0

    return {
        "mvrv": {
            "ours": our_mvrv_val,
            "coinmetrics": cm_val,
            "coinmetrics_date": cm_date,
            "diff_pct": mvrv_diff,
            "status": "ok" if mvrv_diff is not None and abs(mvrv_diff) < 5 else ("warning" if mvrv_diff is not None else "no_data"),
        },
        "sopr": {
            "ours": round(our_sopr, 4) if our_sopr else None,
            "external": None,
            "external_note": "SOPR not available on CoinMetrics free tier",
            "range_check": "ok" if sopr_ok else ("warning" if our_sopr is not None else "no_data"),
            "expected_range": "0.5 – 3.0",
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

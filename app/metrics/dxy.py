import requests
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"


def _fetch_yahoo(ticker):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "range": "5y"}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; btcfunk/1.0)"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    labels, values = [], []
    for ts, cl in zip(timestamps, closes):
        if cl is None:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        labels.append(dt.strftime("%Y-%m-%d"))
        values.append(round(cl, 2))
    return labels, values


def get_dxy():
    dxy_labels, dxy_values = _fetch_yahoo("DX-Y.NYB")
    btc_labels, btc_values = _fetch_yahoo("BTC-USD")

    return {
        "labels": dxy_labels,
        "values": dxy_values,
        "current": dxy_values[-1] if dxy_values else None,
        "btc_labels": btc_labels,
        "btc_close": btc_values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

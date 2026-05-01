import sqlite3, requests
from datetime import datetime, timezone, timedelta

DB_PATH = "btcfunk.sqlite"


def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS btc_prices (day TEXT PRIMARY KEY, price REAL)")
    con.commit()
    return con


def _import_from_ohlc(con):
    count = con.execute("SELECT COUNT(*) FROM btc_prices").fetchone()[0]
    if count > 0: return
    rows = con.execute(
        "SELECT DATE(ts,'unixepoch') AS day, close FROM ohlc WHERE tf=1440 ORDER BY ts"
    ).fetchall()
    if rows:
        con.executemany("INSERT OR REPLACE INTO btc_prices (day,price) VALUES (?,?)", rows)
        con.commit()


def _update_prices(con):
    row = con.execute("SELECT MAX(day) FROM btc_prices").fetchone()
    if not row[0]: return
    last_day = datetime.strptime(row[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    since = int(last_day.timestamp())
    r = requests.get("https://api.kraken.com/0/public/OHLC",
                     params={"pair": "XBTUSD", "interval": 1440, "since": since}, timeout=30)
    r.raise_for_status()
    data = r.json()
    candles = data["result"].get("XXBTZUSD") or data["result"].get("XBTUSD", [])
    new_rows = [(datetime.fromtimestamp(int(c[0]), tz=timezone.utc).strftime("%Y-%m-%d"), float(c[4]))
                for c in candles]
    if new_rows:
        con.executemany("INSERT OR REPLACE INTO btc_prices (day,price) VALUES (?,?)", new_rows)
        con.commit()


def _get_prices(con):
    return {r[0]: r[1] for r in con.execute("SELECT day, price FROM btc_prices").fetchall()}


def _fetch_live_price():
    r = requests.get("https://api.kraken.com/0/public/Ticker", params={"pair": "XBTUSD"}, timeout=10)
    r.raise_for_status()
    ticker = r.json()["result"]
    return float(ticker[list(ticker)[0]]["c"][0])


def get_mvrv():
    con = _init_db()

    _import_from_ohlc(con)
    _update_prices(con)
    prices = _get_prices(con)
    utxos = {r[0]: float(r[1]) for r in
             con.execute("SELECT creation_day, btc_value FROM utxo_snapshot").fetchall()}
    if not utxos:
        return {"error": "utxo_snapshot vuota — esegui migrate_history.py"}
    circulating_supply = sum(utxos.values())
    realized_cap = sum(btc * prices.get(day, 0) for day, btc in utxos.items())

    current_price = _fetch_live_price()
    market_cap    = circulating_supply * current_price

    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    prices = _get_prices(con)
    hist   = sorted((d, p) for d, p in prices.items() if d >= cutoff)
    labels = [d for d, _ in hist]
    values = [round((circulating_supply * p) / realized_cap, 4) for _, p in hist] if realized_cap else []

    return {
        "mvrv":          round(market_cap / realized_cap, 4) if realized_cap else 0,
        "market_cap":    market_cap,
        "realized_cap":  realized_cap,
        "current_price": current_price,
        "labels":        labels,
        "values":        values,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }

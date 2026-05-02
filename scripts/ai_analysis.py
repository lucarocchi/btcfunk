"""
Genera un'analisi di mercato BTC usando Claude AI.
Legge tutti i dati disponibili (price/TA + on-chain) e produce un report.
Output: app/static/analysis.json
"""
import os, sys, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../app/static/analysis.json")


def _safe(fn):
    try:
        return fn()
    except Exception as e:
        return {"error": str(e)}


def collect_data():
    from app.metrics.price       import get_price
    from app.metrics.rsi         import get_rsi
    from app.metrics.bb          import get_bb
    from app.metrics.ema         import get_ema
    from app.metrics.mvrv        import get_mvrv
    from app.metrics.sopr        import get_sopr
    from app.metrics.nvt         import get_nvt
    from app.metrics.nupl        import get_nupl
    from app.metrics.cdd         import get_cdd
    from app.metrics.exchange_flow import get_exchange_flow
    from app.metrics.mvrv_zscore import get_mvrv_zscore
    from app.metrics.puell       import get_puell
    from app.metrics.active_addresses import get_active_addresses
    from app.metrics.whale_tx    import get_whale_tx
    from app.metrics.hashrate    import get_hashrate
    from app.metrics.lth_sth     import get_lth_sth
    from app.metrics.rhodl       import get_rhodl
    from app.metrics.stf         import get_stf
    from app.metrics.coinbase_premium import get_coinbase_premium

    tfs = [1440, 240, 60, 15]
    price_d = _safe(lambda: get_price(1440))
    price_4h = _safe(lambda: get_price(240))
    price_1h = _safe(lambda: get_price(60))
    price_15 = _safe(lambda: get_price(15))

    rsi_d   = _safe(lambda: get_rsi(1440))
    rsi_4h  = _safe(lambda: get_rsi(240))
    rsi_1h  = _safe(lambda: get_rsi(60))
    rsi_15  = _safe(lambda: get_rsi(15))

    bb_d    = _safe(lambda: get_bb(1440))
    bb_4h   = _safe(lambda: get_bb(240))
    bb_1h   = _safe(lambda: get_bb(60))
    bb_15   = _safe(lambda: get_bb(15))

    ema_d   = _safe(lambda: get_ema(1440))

    return {
        "price": {
            "current":    price_d.get("current_price"),
            "daily": {
                "open":   price_d.get("open",  [None])[-1],
                "high":   price_d.get("high",  [None])[-1],
                "low":    price_d.get("low",   [None])[-1],
                "close":  price_d.get("close", [None])[-1],
                "volume": price_d.get("volume",[None])[-1],
            },
            "4h":   { "close": price_4h.get("close",[None])[-1], "volume": price_4h.get("volume",[None])[-1] },
            "1h":   { "close": price_1h.get("close",[None])[-1], "volume": price_1h.get("volume",[None])[-1] },
            "15m":  { "close": price_15.get("close",[None])[-1], "volume": price_15.get("volume",[None])[-1] },
        },
        "rsi":  { "1d": rsi_d.get("current"), "4h": rsi_4h.get("current"), "1h": rsi_1h.get("current"), "15m": rsi_15.get("current") },
        "bb": {
            "1d":  { "upper": bb_d.get("upper",[None])[-1],  "middle": bb_d.get("middle",[None])[-1],  "lower": bb_d.get("lower",[None])[-1],  "width": bb_d.get("width",[None])[-1]  },
            "4h":  { "upper": bb_4h.get("upper",[None])[-1], "middle": bb_4h.get("middle",[None])[-1], "lower": bb_4h.get("lower",[None])[-1], "width": bb_4h.get("width",[None])[-1] },
            "1h":  { "upper": bb_1h.get("upper",[None])[-1], "middle": bb_1h.get("middle",[None])[-1], "lower": bb_1h.get("lower",[None])[-1], "width": bb_1h.get("width",[None])[-1] },
            "15m": { "upper": bb_15.get("upper",[None])[-1], "middle": bb_15.get("middle",[None])[-1], "lower": bb_15.get("lower",[None])[-1], "width": bb_15.get("width",[None])[-1] },
        },
        "ema": { "20": ema_d.get("ema20",[None])[-1], "50": ema_d.get("ema50",[None])[-1], "200": ema_d.get("ema200",[None])[-1] },
        "onchain": {
            "mvrv":             _safe(get_mvrv).get("mvrv"),
            "sopr":             _safe(get_sopr).get("current"),
            "nvt":              _safe(get_nvt).get("nvt"),
            "nupl":             _safe(get_nupl).get("nupl"),
            "cdd":              { "current": _safe(get_cdd).get("current"), "ma90": _safe(get_cdd).get("ma90") },
            "exchange_flow_net":_safe(get_exchange_flow).get("current_net"),
            "mvrv_zscore":      _safe(get_mvrv_zscore).get("z_score"),
            "puell":            _safe(get_puell).get("puell"),
            "active_addr":      { "current": _safe(get_active_addresses).get("current"), "ma30": _safe(get_active_addresses).get("ma30") },
            "whale_tx":         { "current": _safe(get_whale_tx).get("current"), "ma30": _safe(get_whale_tx).get("ma30") },
            "hashrate_eh":      _safe(get_hashrate).get("hashrate_eh"),
            "lth_supply":       _safe(get_lth_sth).get("lth_supply"),
            "sth_supply":       _safe(get_lth_sth).get("sth_supply"),
            "rhodl":            _safe(get_rhodl).get("rhodl"),
            "stf_deviation":    _safe(get_stf).get("deviation_pct"),
            "coinbase_premium": _safe(get_coinbase_premium).get("current"),
        }
    }


def build_prompt(d):
    p = d["price"]
    r = d["rsi"]
    b = d["bb"]
    e = d["ema"]
    o = d["onchain"]
    now = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    def f(v, decimals=0):
        if v is None: return "N/A"
        return f"{v:,.{decimals}f}"

    bb_dist = lambda price, upper: f"{(price/upper - 1)*100:.2f}" if price and upper else "N/A"

    return f"""You are a professional Bitcoin market analyst. Analyze the following real-time data and write a concise, structured market analysis in English.

DATA AS OF {now}:

=== PRICE & TECHNICALS ===

DAILY (1D):
- Price: ${f(p['current'])} | Open: ${f(p['daily']['open'])} | High: ${f(p['daily']['high'])} | Low: ${f(p['daily']['low'])}
- Volume: {f(p['daily']['volume'], 2)} BTC
- RSI(14): {f(r['1d'], 1)}
- BB Upper: ${f(b['1d']['upper'])} | Middle: ${f(b['1d']['middle'])} | Lower: ${f(b['1d']['lower'])} | Width: {f(b['1d']['width'], 2)}%
- Distance from BB Upper: {bb_dist(p['current'], b['1d']['upper'])}%
- EMA20: ${f(e['20'])} | EMA50: ${f(e['50'])} | EMA200: ${f(e['200'])}

4-HOUR (4H):
- Price: ${f(p['4h']['close'])} | Volume: {f(p['4h']['volume'], 2)} BTC
- RSI(14): {f(r['4h'], 1)}
- BB Upper: ${f(b['4h']['upper'])} | Width: {f(b['4h']['width'], 2)}%
- Distance from BB Upper: {bb_dist(p['4h']['close'], b['4h']['upper'])}%

1-HOUR (1H):
- Price: ${f(p['1h']['close'])} | Volume: {f(p['1h']['volume'], 2)} BTC
- RSI(14): {f(r['1h'], 1)}
- BB Width: {f(b['1h']['width'], 2)}%

15-MINUTE (15m):
- Price: ${f(p['15m']['close'])} | Volume: {f(p['15m']['volume'], 2)} BTC
- RSI(14): {f(r['15m'], 1)}
- BB Width: {f(b['15m']['width'], 2)}%

=== ON-CHAIN METRICS ===

- MVRV Ratio: {f(o['mvrv'], 2)} (< 1 = undervalued, > 3.5 = top zone)
- MVRV Z-Score: {f(o['mvrv_zscore'], 2)} (> 7 = top zone, < 0 = bottom)
- SOPR: {f(o['sopr'], 4)} (< 1 = selling at loss, > 1 = at profit)
- NUPL: {f(o['nupl'], 3)} (< 0 = capitulation, > 0.75 = euphoria)
- NVT Ratio: {f(o['nvt'], 1)} (< 50 = undervalued, > 150 = overvalued)
- Puell Multiple: {f(o['puell'], 3)} (< 0.5 = miner bottom, > 4 = top)
- CDD: {f(o['cdd']['current'], 0)} vs MA90 {f(o['cdd']['ma90'], 0)} (high = old coins moving)
- Exchange Net Flow: {f(o['exchange_flow_net'], 2)} BTC (negative = outflow = bullish)
- Active Addresses: {f(o['active_addr']['current'], 0)} vs MA30 {f(o['active_addr']['ma30'], 0)}
- Whale Transactions (>100 BTC): {f(o['whale_tx']['current'], 0)} vs MA30 {f(o['whale_tx']['ma30'], 0)}
- Hash Rate: {f(o['hashrate_eh'], 1)} EH/s
- LTH Supply: {f(o['lth_supply'], 0)} BTC | STH Supply: {f(o['sth_supply'], 0)} BTC
- RHODL Ratio: {f(o['rhodl'], 2)} (> 50,000 = top zone)
- Stock-to-Flow deviation: {f(o['stf_deviation'], 1)}%
- Coinbase Premium Index: {f(o['coinbase_premium'], 4)}% (> 0 = US buying, < 0 = US selling)

=== INSTRUCTIONS ===

Write the analysis in English with this structure:
1. **Market Snapshot** — 2-3 sentences summarizing the overall picture
2. **Price & TA** — key signals per timeframe (1D, 4H, 1H/15m) — use actual numbers
3. **On-Chain** — what the on-chain data says about market structure, holder behavior, and cycle position
4. **Outlook** — probable short-term scenario with key levels to watch

Be direct and specific. Use the actual numbers from the data. Avoid generic statements. Max 450 words."""


def run():
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print("Collecting data...", flush=True)
    d = collect_data()

    print("Calling Claude...", flush=True)
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": build_prompt(d)}]
    )
    text = msg.content[0].text
    tokens_in  = msg.usage.input_tokens
    tokens_out = msg.usage.output_tokens

    result = {
        "text":         text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model":        msg.model,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(result, f)

    print(f"\nTokens: {tokens_in} in / {tokens_out} out")
    print("-" * 60)
    print(text)
    print("-" * 60)
    print(f"Saved to {OUT_PATH}")


if __name__ == "__main__":
    run()

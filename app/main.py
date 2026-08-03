import os
import secrets

from fastapi import Depends, FastAPI, Request, Query, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, Response, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.metrics_meta import METRICS_META, METRIC_LABELS, METRIC_QUERIES, HIDDEN_METRICS, VISIBLE_METRICS

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(title="BTCFunk Analytics")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return RedirectResponse(url="/")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def _resp(data: dict, summary: bool) -> dict:
    if not summary:
        return data
    return {k: v for k, v in data.items() if not isinstance(v, list)}


_S = Query(False, description="Return only scalar fields, omit time-series arrays")
_TF = Query(1440, description="Timeframe in minutes: 15, 30, 60, 240, 720, 1440")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "hidden_metrics": sorted(HIDDEN_METRICS)},
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return """User-agent: *
Allow: /
Disallow: /invoices
Sitemap: https://btcfunk.com/sitemap.xml
"""


@app.get("/api/health")
@limiter.limit("100/minute")
async def health(request: Request):
    return {"status": "ok"}


@app.get("/api/mvrv")
@limiter.limit("100/minute")
async def mvrv(request: Request, summary: bool = _S):
    from app.metrics.mvrv import get_mvrv
    return _resp(get_mvrv(), summary)


@app.get("/api/sopr")
@limiter.limit("100/minute")
async def sopr(request: Request, summary: bool = _S):
    from app.metrics.sopr import get_sopr
    return _resp(get_sopr(), summary)


@app.get("/api/nvt")
@limiter.limit("100/minute")
async def nvt(request: Request, summary: bool = _S):
    from app.metrics.nvt import get_nvt
    return _resp(get_nvt(), summary)


@app.get("/api/cdd")
@limiter.limit("100/minute")
async def cdd(request: Request, summary: bool = _S):
    from app.metrics.cdd import get_cdd
    return _resp(get_cdd(), summary)


@app.get("/api/hodl")
@limiter.limit("100/minute")
async def hodl(request: Request, summary: bool = _S):
    from app.metrics.hodl import get_hodl
    return _resp(get_hodl(), summary)


@app.get("/api/validate")
@limiter.limit("100/minute")
async def validate(request: Request):
    from app.metrics.validate import get_validation
    return get_validation()


@app.get("/api/exchange_flow")
@limiter.limit("100/minute")
async def exchange_flow(request: Request, summary: bool = _S):
    from app.metrics.exchange_flow import get_exchange_flow
    return _resp(get_exchange_flow(), summary)


@app.get("/api/nupl")
@limiter.limit("100/minute")
async def nupl(request: Request, summary: bool = _S):
    from app.metrics.nupl import get_nupl
    return _resp(get_nupl(), summary)


@app.get("/api/rhodl")
@limiter.limit("100/minute")
async def rhodl(request: Request, summary: bool = _S):
    from app.metrics.rhodl import get_rhodl
    return _resp(get_rhodl(), summary)


@app.get("/api/puell")
@limiter.limit("100/minute")
async def puell(request: Request, summary: bool = _S):
    from app.metrics.puell import get_puell
    return _resp(get_puell(), summary)


@app.get("/api/active_addresses")
@limiter.limit("100/minute")
async def active_addresses(request: Request, summary: bool = _S):
    from app.metrics.active_addresses import get_active_addresses
    return _resp(get_active_addresses(), summary)


@app.get("/api/whale_tx")
@limiter.limit("100/minute")
async def whale_tx(request: Request, summary: bool = _S):
    from app.metrics.whale_tx import get_whale_tx
    return _resp(get_whale_tx(), summary)


@app.get("/api/mvrv_zscore")
@limiter.limit("100/minute")
async def mvrv_zscore(request: Request, summary: bool = _S):
    from app.metrics.mvrv_zscore import get_mvrv_zscore
    return _resp(get_mvrv_zscore(), summary)


@app.get("/api/lth_sth")
@limiter.limit("100/minute")
async def lth_sth(request: Request, summary: bool = _S):
    from app.metrics.lth_sth import get_lth_sth
    return _resp(get_lth_sth(), summary)


@app.get("/api/stf")
@limiter.limit("100/minute")
async def stf(request: Request, summary: bool = _S):
    from app.metrics.stf import get_stf
    return _resp(get_stf(), summary)


@app.get("/api/tx_stats")
@limiter.limit("100/minute")
async def tx_stats(request: Request, summary: bool = _S):
    from app.metrics.tx_stats import get_tx_stats
    return _resp(get_tx_stats(), summary)


@app.get("/api/hashrate")
@limiter.limit("100/minute")
async def hashrate(request: Request, summary: bool = _S):
    from app.metrics.hashrate import get_hashrate
    return _resp(get_hashrate(), summary)


@app.get("/api/dxy")
@limiter.limit("100/minute")
async def dxy(request: Request, summary: bool = _S):
    from app.metrics.dxy import get_dxy
    return _resp(get_dxy(), summary)


@app.get("/api/mempool")
@limiter.limit("60/minute")
async def mempool(request: Request):
    from app.metrics.mempool import get_mempool
    return get_mempool()


@app.get("/api/prices")
@limiter.limit("120/minute")
async def prices(request: Request):
    import httpx, time
    _cache = getattr(app.state, "_prices_cache", None)
    if _cache and time.time() - _cache["ts"] < 120:
        return _cache["data"]
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("https://mempool.space/api/v1/prices")
            data = r.json()
    except Exception:
        data = _cache["data"] if _cache else {}
    app.state._prices_cache = {"data": data, "ts": time.time()}
    return data


@app.get("/api/fear_greed")
@limiter.limit("60/minute")
async def fear_greed(request: Request):
    from app.metrics.fear_greed import get_fear_greed
    return get_fear_greed()


@app.get("/api/coinbase_premium")
@limiter.limit("100/minute")
async def coinbase_premium(request: Request, summary: bool = _S):
    from app.metrics.coinbase_premium import get_coinbase_premium
    return _resp(get_coinbase_premium(), summary)


@app.get("/api/price")
@limiter.limit("100/minute")
async def price(request: Request, tf: int = _TF, summary: bool = _S):
    from app.metrics.price import get_price
    return _resp(get_price(tf=tf), summary)


@app.get("/api/rsi")
@limiter.limit("100/minute")
async def rsi(request: Request, tf: int = _TF, summary: bool = _S):
    from app.metrics.rsi import get_rsi
    return _resp(get_rsi(tf=tf), summary)


@app.get("/api/ema")
@limiter.limit("100/minute")
async def ema(request: Request, tf: int = _TF, summary: bool = _S):
    from app.metrics.ema import get_ema
    return _resp(get_ema(tf=tf), summary)


@app.get("/api/bb")
@limiter.limit("100/minute")
async def bb(request: Request, tf: int = _TF, summary: bool = _S):
    from app.metrics.bb import get_bb
    return _resp(get_bb(tf=tf), summary)


_PAY_ADMIN_USER = os.environ.get("BTCFUNKPAY_ADMIN_USERNAME", "admin")
_PAY_ADMIN_PASS = os.environ.get("BTCFUNKPAY_ADMIN_PASSWORD", "")

_http_basic = HTTPBasic()

def _require_admin(credentials: HTTPBasicCredentials = Depends(_http_basic)):
    pw = _PAY_ADMIN_PASS
    if not pw:
        raise HTTPException(status_code=503, detail="Admin password not configured")
    ok_user = secrets.compare_digest(credentials.username.encode(), _PAY_ADMIN_USER.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), pw.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )

@app.get("/invoices")
async def invoices_page(
    request: Request,
    status: str = None,
    _: HTTPBasicCredentials = Depends(_require_admin),
):
    import httpx
    params = {}
    if status:
        params["status"] = status
    try:
        auth = (_PAY_ADMIN_USER, _PAY_ADMIN_PASS) if _PAY_ADMIN_PASS else None
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8001/invoices", params=params, auth=auth)
            invoices = r.json() if r.status_code == 200 else []
    except Exception:
        invoices = []

    status_colors = {
        "confirmed": "#22c55e",
        "overpaid":  "#22c55e",
        "detected":  "#f7931a",
        "pending":   "#aaaaaa",
        "expired":   "#ef4444",
    }

    rows = ""
    for inv in invoices:
        color = status_colors.get(inv.get("status", ""), "#aaaaaa")
        created = (inv.get("created_at") or "")[:16].replace("T", " ")
        confirmed = (inv.get("confirmed_at") or "—")[:16].replace("T", " ")
        amount = f"{inv.get('amount_sat') or '—'}"
        received = inv.get("received_sat") or 0
        txid = inv.get("txid") or "—"
        txid_short = txid[:12] + "…" if txid != "—" else "—"
        pid = inv.get("payment_id") or "—"
        pid_short = pid[:8] + "…" if pid != "—" else "—"
        rows += f"""
        <tr>
          <td style="color:#aaa;font-size:11px">{created}</td>
          <td style="font-family:monospace;font-size:11px;color:#aaa" title="{pid}">{pid_short}</td>
          <td>{inv.get('label') or '—'}</td>
          <td style="text-align:right">{amount}</td>
          <td style="text-align:right;color:#22c55e">{received}</td>
          <td><span style="color:{color};font-weight:600">{inv.get('status')}</span></td>
          <td style="font-family:monospace;font-size:11px" title="{txid}">{txid_short}</td>
          <td style="color:#aaa;font-size:11px">{confirmed}</td>
        </tr>"""

    filters = " ".join(
        f'<a href="/invoices?status={s}" style="padding:4px 10px;border-radius:4px;font-size:12px;text-decoration:none;background:{"#333" if status==s else "#1a1a1a"};color:{c}">{s}</a>'
        for s, c in status_colors.items()
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>FunkPay Invoices</title>
<style>
  body {{ font-family: sans-serif; background: #0f0f0f; color: #eee; padding: 2rem; }}
  h1 {{ font-size: 1.2rem; margin-bottom: 1rem; }}
  .filters {{ display: flex; gap: 8px; margin-bottom: 1.5rem; flex-wrap: wrap; align-items: center; }}
  .filters-right {{ margin-left: auto; }}
  #receipt-search {{ background: #1a1a1a; border: 1px solid #333; color: #eee; padding: 4px 10px; border-radius: 4px; font-size: 12px; width: 220px; outline: none; }}
  #receipt-search::placeholder {{ color: #555; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; color: #666; font-weight: 600; font-size: 11px; text-transform: uppercase; padding: 6px 8px; border-bottom: 1px solid #222; }}
  td {{ padding: 8px; border-bottom: 1px solid #1a1a1a; vertical-align: middle; }}
  tr:hover td {{ background: #1a1a1a; }}
  a.back {{ color: #f7931a; text-decoration: none; font-size: 13px; display: inline-block; margin-bottom: 1.5rem; }}
</style>
</head><body>
  <a class="back" href="/">← BTCFunk</a>
  <h1>FunkPay — Invoices ({len(invoices)})</h1>
  <div class="filters">
    <a href="/invoices" style="padding:4px 10px;border-radius:4px;font-size:12px;text-decoration:none;background:{"#333" if not status else "#1a1a1a"};color:#eee">all</a>
    {filters}
    <div class="filters-right">
      <input id="receipt-search" type="text" placeholder="Search receipt…">
    </div>
  </div>
  <script>
    document.getElementById('receipt-search').addEventListener('input', function() {{
      var q = this.value.toLowerCase();
      document.querySelectorAll('tbody tr').forEach(function(row) {{
        var receipt = (row.cells[1] ? row.cells[1].getAttribute('title') || row.cells[1].textContent : '').toLowerCase();
        row.style.display = (!q || receipt.includes(q)) ? '' : 'none';
      }});
    }});
  </script>
  <table>
    <thead><tr>
      <th>Created</th><th>Receipt</th><th>Label</th><th style="text-align:right">Amount (sat)</th>
      <th style="text-align:right">Received (sat)</th><th>Status</th><th>Txid</th><th>Confirmed</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body></html>"""

    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)


@app.get("/funkpay")
async def funkpay_page():
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FunkPay — Bitcoin On-Chain Payments</title>
  <meta name="description" content="FunkPay is a self-custodial Bitcoin payment library. Accept BTC payments with no middlemen, no custody, no third party. Your keys, your coins.">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f0f0f; color: #eee; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 3rem 1.25rem 4rem; }
    .back { align-self: flex-start; color: #f7931a; text-decoration: none; font-size: 0.8rem; margin-bottom: 2.5rem; }
    .back:hover { opacity: 0.8; }
    .sub { color: #aaa; font-size: 0.9rem; margin-bottom: 2.5rem; }
    .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; width: 100%; max-width: 680px; margin-bottom: 2.5rem; }
    .feature { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 1rem 1.25rem; }
    .feature strong { display: block; font-size: 0.85rem; color: #f7931a; margin-bottom: 0.3rem; }
    .feature span { font-size: 0.8rem; color: #999; line-height: 1.5; }
    .links { display: flex; gap: 1rem; margin-bottom: 3rem; }
    .btn { padding: 0.6rem 1.4rem; border-radius: 6px; font-size: 0.85rem; font-weight: 500; text-decoration: none; }
    .btn-primary { background: #f7931a; color: #000; }
    .btn:hover { opacity: 0.85; }
    #funkpay { width: 100%; max-width: 380px; }
    footer { margin-top: auto; padding-top: 3rem; font-size: 0.72rem; color: #555; }
    footer a { color: #555; text-decoration: none; }
    footer a:hover { color: #aaa; }
    @media (prefers-color-scheme: light) {
      body { background: #f5f5f5; color: #111; }
      .sub { color: #333; }
      .feature { background: #fff; border-color: #ddd; }
      .feature span { color: #333; }
      footer { color: #666; }
      footer a { color: #666; }
      footer a:hover { color: #111; }
    }
  </style>
</head>
<body>
  <a class="back" href="/">← BTCFunk</a>

  <img src="/static/logo_funkpay.png" alt="FunkPay" style="width:100px;margin-bottom:1.5rem;">
  <p class="sub">Self-custodial Bitcoin on-chain payments &mdash; no middlemen, no custody.</p>

  <div class="features">
    <div class="feature"><strong>Your keys, your coins</strong><span>Funds go directly to your wallet. FunkPay never touches private keys.</span></div>
    <div class="feature"><strong>No third party</strong><span>Your Bitcoin Core node, your database, your data.</span></div>
    <div class="feature"><strong>Embeddable widget</strong><span>One &lt;script&gt; tag. Shadow DOM isolation. Works on any website.</span></div>
    <div class="feature"><strong>Mempool-first UX</strong><span>Instant detection on 0-conf. Confirmed callback when settled on-chain.</span></div>
    <div class="feature"><strong>Webhook support</strong><span>Server-side notifications fire even if the user closes the browser.</span></div>
    <div class="feature"><strong>Multi-currency</strong><span>Fiat display in USD, EUR, GBP, JPY, CAD, CHF, AUD. Always pays in BTC.</span></div>
  </div>

  <div id="funkpay" data-server="https://btcfunk.com/pay" data-currency="USD" data-theme="auto"></div>

  <div class="links" style="margin-top:2rem;">
    <a class="btn btn-primary" href="https://github.com/lucarocchi/btcfunkpay" target="_blank" rel="noopener">GitHub</a>
  </div>

  <footer><a href="/">BTCFunk</a> &nbsp;&middot;&nbsp; <a href="mailto:lucarocchi@outlook.it">Contact</a></footer>

  <script src="https://btcfunk.com/pay/funkpay.js"></script>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/sitemap.xml")
async def sitemap_dynamic():
    urls = ['https://btcfunk.com/', 'https://btcfunk.com/funkpay'] + [f'https://btcfunk.com/{k}' for k in VISIBLE_METRICS]
    items = ''.join(
        f'  <url><loc>{u}</loc><changefreq>daily</changefreq><priority>{"1.0" if u.endswith("/") else "0.8"}</priority></url>\n'
        for u in urls
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{items}</urlset>'
    return Response(content=xml, media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/{metric_id}")
async def metric_page(request: Request, metric_id: str):
    if metric_id not in VISIBLE_METRICS:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "metric.html",
        {
            "request": request,
            "metric_id": metric_id,
            "meta": METRICS_META[metric_id],
            "related_labels": {k: v for k, v in METRIC_LABELS.items() if k not in HIDDEN_METRICS},
            "query": METRIC_QUERIES.get(metric_id),
        },
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )

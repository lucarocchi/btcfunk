from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.metrics_meta import METRICS_META, METRIC_LABELS, METRIC_QUERIES

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(title="BTCFunk Analytics")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
        "index.html", {"request": request},
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return """User-agent: *
Allow: /
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


@app.get("/sitemap.xml")
async def sitemap_dynamic():
    urls = ['https://btcfunk.com/'] + [f'https://btcfunk.com/{k}' for k in METRICS_META]
    items = ''.join(
        f'  <url><loc>{u}</loc><changefreq>daily</changefreq><priority>{"1.0" if u.endswith("/") else "0.8"}</priority></url>\n'
        for u in urls
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{items}</urlset>'
    return Response(content=xml, media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/{metric_id}")
async def metric_page(request: Request, metric_id: str):
    if metric_id not in METRICS_META:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "metric.html",
        {
            "request": request,
            "metric_id": metric_id,
            "meta": METRICS_META[metric_id],
            "related_labels": METRIC_LABELS,
            "query": METRIC_QUERIES.get(metric_id),
        },
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )

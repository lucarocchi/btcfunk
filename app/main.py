from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse

app = FastAPI(title="BTCFunk Analytics")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def _resp(data: dict, summary: bool) -> dict:
    if not summary:
        return data
    return {k: v for k, v in data.items() if not isinstance(v, list)}


_S = Query(False, description="Return only scalar fields, omit time-series arrays")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return """User-agent: *
Allow: /
Sitemap: https://btcfunk.com/static/sitemap.xml
"""


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/mvrv")
async def mvrv(summary: bool = _S):
    from app.metrics.mvrv import get_mvrv
    return _resp(get_mvrv(), summary)


@app.get("/api/sopr")
async def sopr(summary: bool = _S):
    from app.metrics.sopr import get_sopr
    return _resp(get_sopr(), summary)


@app.get("/api/nvt")
async def nvt(summary: bool = _S):
    from app.metrics.nvt import get_nvt
    return _resp(get_nvt(), summary)


@app.get("/api/cdd")
async def cdd(summary: bool = _S):
    from app.metrics.cdd import get_cdd
    return _resp(get_cdd(), summary)


@app.get("/api/hodl")
async def hodl(summary: bool = _S):
    from app.metrics.hodl import get_hodl
    return _resp(get_hodl(), summary)


@app.get("/api/validate")
async def validate():
    from app.metrics.validate import get_validation
    return get_validation()


@app.get("/api/exchange_flow")
async def exchange_flow(summary: bool = _S):
    from app.metrics.exchange_flow import get_exchange_flow
    return _resp(get_exchange_flow(), summary)


@app.get("/api/nupl")
async def nupl(summary: bool = _S):
    from app.metrics.nupl import get_nupl
    return _resp(get_nupl(), summary)


@app.get("/api/rhodl")
async def rhodl(summary: bool = _S):
    from app.metrics.rhodl import get_rhodl
    return _resp(get_rhodl(), summary)


@app.get("/api/puell")
async def puell(summary: bool = _S):
    from app.metrics.puell import get_puell
    return _resp(get_puell(), summary)


@app.get("/api/active_addresses")
async def active_addresses(summary: bool = _S):
    from app.metrics.active_addresses import get_active_addresses
    return _resp(get_active_addresses(), summary)


@app.get("/api/whale_tx")
async def whale_tx(summary: bool = _S):
    from app.metrics.whale_tx import get_whale_tx
    return _resp(get_whale_tx(), summary)


@app.get("/api/mvrv_zscore")
async def mvrv_zscore(summary: bool = _S):
    from app.metrics.mvrv_zscore import get_mvrv_zscore
    return _resp(get_mvrv_zscore(), summary)


@app.get("/api/lth_sth")
async def lth_sth(summary: bool = _S):
    from app.metrics.lth_sth import get_lth_sth
    return _resp(get_lth_sth(), summary)


@app.get("/api/stf")
async def stf(summary: bool = _S):
    from app.metrics.stf import get_stf
    return _resp(get_stf(), summary)


@app.get("/api/tx_stats")
async def tx_stats(summary: bool = _S):
    from app.metrics.tx_stats import get_tx_stats
    return _resp(get_tx_stats(), summary)


@app.get("/api/hashrate")
async def hashrate(summary: bool = _S):
    from app.metrics.hashrate import get_hashrate
    return _resp(get_hashrate(), summary)

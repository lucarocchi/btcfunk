from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse

app = FastAPI(title="BTCFunk Analytics")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


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
async def mvrv():
    from app.metrics.mvrv import get_mvrv
    return get_mvrv()


@app.get("/api/sopr")
async def sopr():
    from app.metrics.sopr import get_sopr
    return get_sopr()


@app.get("/api/nvt")
async def nvt():
    from app.metrics.nvt import get_nvt
    return get_nvt()


@app.get("/api/cdd")
async def cdd():
    from app.metrics.cdd import get_cdd
    return get_cdd()


@app.get("/api/hodl")
async def hodl():
    from app.metrics.hodl import get_hodl
    return get_hodl()


@app.get("/api/validate")
async def validate():
    from app.metrics.validate import get_validation
    return get_validation()


@app.get("/api/exchange_flow")
async def exchange_flow():
    from app.metrics.exchange_flow import get_exchange_flow
    return get_exchange_flow()


@app.get("/api/nupl")
async def nupl():
    from app.metrics.nupl import get_nupl
    return get_nupl()


@app.get("/api/rhodl")
async def rhodl():
    from app.metrics.rhodl import get_rhodl
    return get_rhodl()


@app.get("/api/puell")
async def puell():
    from app.metrics.puell import get_puell
    return get_puell()


@app.get("/api/active_addresses")
async def active_addresses():
    from app.metrics.active_addresses import get_active_addresses
    return get_active_addresses()


@app.get("/api/whale_tx")
async def whale_tx():
    from app.metrics.whale_tx import get_whale_tx
    return get_whale_tx()


@app.get("/api/mvrv_zscore")
async def mvrv_zscore():
    from app.metrics.mvrv_zscore import get_mvrv_zscore
    return get_mvrv_zscore()


@app.get("/api/lth_sth")
async def lth_sth():
    from app.metrics.lth_sth import get_lth_sth
    return get_lth_sth()


@app.get("/api/stf")
async def stf():
    from app.metrics.stf import get_stf
    return get_stf()


@app.get("/api/tx_stats")
async def tx_stats():
    from app.metrics.tx_stats import get_tx_stats
    return get_tx_stats()


@app.get("/api/hashrate")
async def hashrate():
    from app.metrics.hashrate import get_hashrate
    return get_hashrate()

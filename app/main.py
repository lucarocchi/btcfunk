from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="BTCFunk Analytics")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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

from contextlib import asynccontextmanager
from dataclasses import asdict
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db.session import SessionLocal, init_db
from db import crud
from jobs.ratelimit import check_and_reserve
from jobs.queue import enqueue_job
from web.forms import build_spec


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="WycenaFinder", lifespan=lifespan)
templates = Jinja2Templates(directory="web/templates")
templates.env.filters["fmt"] = lambda n: f"{int(n):,}".replace(",", " ") if n is not None else "—"


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/search")
async def search(request: Request):
    form = await request.form()
    try:
        spec = build_spec(form)
    except ValueError as e:
        return templates.TemplateResponse(
            request, "index.html", {"error": str(e)}, status_code=400)
    ip = request.client.host if request.client else "unknown"
    ok, reason = check_and_reserve(ip)
    if not ok:
        msg = ("Masz aktywne zlecenie — odczekaj 5 min."
               if reason == "active" else "Limit 20 zleceń na dobę osiągnięty.")
        return templates.TemplateResponse(
            request, "index.html", {"error": msg}, status_code=429)
    session = SessionLocal()
    try:
        job = crud.create_job(session, ip, asdict(spec))
        job_id = job.id
    finally:
        session.close()
    enqueue_job(job_id)
    return RedirectResponse(f"/job/{job_id}", status_code=303)

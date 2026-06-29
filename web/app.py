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
from pipeline.geo import list_regions, cities_for_region, districts_for_city, resolve_city


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="WycenaFinder", lifespan=lifespan)
templates = Jinja2Templates(directory="web/templates")
templates.env.filters["fmt"] = lambda n: f"{int(n):,}".replace(",", " ") if n is not None else "—"


def _href_safe(u):
    u = str(u or "")
    return u if u.startswith(("http://", "https://")) else "#"
templates.env.filters["href_safe"] = _href_safe


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"regions": list_regions()})


@app.get("/geo/cities", response_class=HTMLResponse)
def geo_cities(request: Request, woj: str = ""):
    return templates.TemplateResponse(
        request, "_geo_cities.html", {"cities": cities_for_region(woj)})


@app.get("/geo/districts", response_class=HTMLResponse)
def geo_districts(request: Request, woj: str = "", miasto: str = ""):
    city = resolve_city(woj, miasto)
    districts = ([d["name"] for d in districts_for_city(city["city_id"])]
                 if city and city.get("has_districts") else [])
    return templates.TemplateResponse(
        request, "_geo_districts.html", {"districts": districts})


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


@app.get("/job/{job_id}", response_class=HTMLResponse)
def job_page(request: Request, job_id: str):
    session = SessionLocal()
    try:
        job = crud.get_job(session, job_id)
    finally:
        session.close()
    if not job:
        return HTMLResponse("Nie znaleziono zlecenia.", status_code=404)
    return templates.TemplateResponse(request, "job.html", {"job_id": job_id})


@app.get("/job/{job_id}/status", response_class=HTMLResponse)
def job_status(request: Request, job_id: str):
    session = SessionLocal()
    try:
        job = crud.get_job(session, job_id)
        if not job:
            return HTMLResponse("Nie znaleziono.", status_code=404)
        if job.status in ("queued", "processing"):
            return templates.TemplateResponse(
                request, "_status.html", {"job_id": job_id, "status": job.status})
        if job.status == "error":
            return templates.TemplateResponse(
                request, "_error.html", {"error": job.error_msg})
        if job.status == "done":
            results = [r.data for r in sorted(job.results, key=lambda r: r.rank)]
            return templates.TemplateResponse(request, "_results.html", {"results": results, "job": job})
        return templates.TemplateResponse(request, "_error.html", {"error": f"nieznany status: {job.status}"})
    finally:
        session.close()

from datetime import datetime, timezone
from db.session import SessionLocal
from db import crud
from db.cache import install_db_valuation_cache, uninstall_db_valuation_cache
from pipeline.spec import SearchSpec
from pipeline.search import run_search
from config import SLICE_TTL_SECONDS, MAX_PAGES

HEAVY_KEYS = ("text", "map")


def _snapshot(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in HEAVY_KEYS}


def _now():
    return datetime.now(timezone.utc)


def process_job(job_id: str) -> None:
    session = SessionLocal()
    try:
        job = crud.get_job(session, job_id)
        if not job:
            return
        crud.set_status(session, job_id, "processing", started_at=_now())

        cached = crud.find_fresh_slice(session, job.spec_hash, SLICE_TTL_SECONDS, exclude_id=job_id)
        if cached:
            rows = [r.data for r in sorted(cached.results, key=lambda r: r.rank)]
            crud.add_results(session, job_id, rows)
            crud.set_status(session, job_id, "done", from_cache=True,
                            count_qualified=cached.count_qualified, finished_at=_now())
            return

        spec = SearchSpec(**job.spec).normalized()
        install_db_valuation_cache()
        try:
            out = run_search(spec, max_pages=MAX_PAGES)
        finally:
            uninstall_db_valuation_cache()

        if out.get("error"):
            crud.set_status(session, job_id, "error", error_msg=out["error"], finished_at=_now())
            return

        crud.add_results(session, job_id, [_snapshot(r) for r in out["results"]])
        crud.set_status(session, job_id, "done",
                        count_qualified=out.get("count_qualified"), finished_at=_now())
    except Exception as e:  # noqa: BLE001  surface any failure to the user as job error
        crud.set_status(session, job_id, "error", error_msg=str(e)[:500], finished_at=_now())
    finally:
        session.close()

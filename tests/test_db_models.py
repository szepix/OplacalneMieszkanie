def test_init_db_creates_tables_on_real_postgres(db):
    from sqlalchemy import text
    rows = db.execute(text(
        "select tablename from pg_tables where schemaname='public'"
    )).fetchall()
    names = {r[0] for r in rows}
    assert {"jobs", "job_results", "valuations_cache"} <= names


def test_create_and_get_job_roundtrips_spec(db):
    from db import crud
    spec = {"woj": "malopolskie", "miasto": "krakow", "rooms": [2, 3], "price_min": 0}
    job = crud.create_job(db, "1.2.3.4", spec)
    assert job.id and job.status == "queued" and len(job.spec_hash) == 64
    again = crud.get_job(db, job.id)
    assert again.spec == spec and again.ip == "1.2.3.4"


def test_add_results_ranks_in_order(db):
    from db import crud
    job = crud.create_job(db, "1.2.3.4", {"woj": "x", "miasto": "y", "rooms": []})
    crud.add_results(db, job.id, [{"url": "a", "value": 1.2}, {"url": "b", "value": 1.1}])
    db.refresh(job)
    ranked = sorted(job.results, key=lambda r: r.rank)
    assert [r.rank for r in ranked] == [1, 2]
    assert ranked[0].data["url"] == "a"


def test_find_fresh_slice_respects_ttl_status_and_exclude(db):
    from datetime import datetime, timezone, timedelta
    from db import crud
    spec = {"woj": "x", "miasto": "y", "rooms": [2]}
    h = crud.spec_hash(spec)
    old = crud.create_job(db, "ip", spec)
    crud.set_status(db, old.id, "done",
                    finished_at=datetime.now(timezone.utc) - timedelta(hours=10))
    fresh = crud.create_job(db, "ip", spec)
    crud.set_status(db, fresh.id, "done",
                    finished_at=datetime.now(timezone.utc) - timedelta(minutes=5))
    new = crud.create_job(db, "ip", spec)
    hit = crud.find_fresh_slice(db, h, 6 * 3600, exclude_id=new.id)
    assert hit is not None and hit.id == fresh.id  # 6h-old excluded, self excluded
    assert crud.find_fresh_slice(db, h, 60, exclude_id=new.id) is None  # 60s TTL → none fresh

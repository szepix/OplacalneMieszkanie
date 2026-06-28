def _run_burst(redis_conn):
    from rq import SimpleWorker, Queue
    q = Queue("wf", connection=redis_conn)
    SimpleWorker([q], connection=redis_conn).work(burst=True)


def test_process_job_persists_results_and_marks_done(db, redis_conn, monkeypatch):
    from db import crud
    from jobs.queue import enqueue_job
    import worker.process as wp

    fake = {"city": {"city_id": 1}, "count_raw": 2, "count_qualified": 1, "error": None,
            "results": [{"url": "u1", "value": 1.3, "eff_price": 500000, "area": 50,
                         "wycena": 650000, "src": "OLX", "text": "x", "map": {"lat": 1}}]}
    monkeypatch.setattr(wp, "run_search", lambda spec, max_pages=2: fake)

    spec = {"woj": "malopolskie", "miasto": "krakow", "rooms": [2], "price_min": 0,
            "price_max": 10000000, "area_min": None, "area_max": None, "year_min": None,
            "floor": None, "required_features": [], "keywords": [], "rynek": "any", "sort": "value"}
    job = crud.create_job(db, "1.1.1.1", spec)
    enqueue_job(job.id, conn=redis_conn)
    _run_burst(redis_conn)

    db.expire_all()
    done = crud.get_job(db, job.id)
    assert done.status == "done" and done.count_qualified == 1
    assert done.finished_at is not None and done.started_at is not None
    row = sorted(done.results, key=lambda r: r.rank)[0].data
    assert row["url"] == "u1" and "text" not in row and "map" not in row  # heavy keys stripped


def test_slice_cache_reuses_recent_identical_job(db, redis_conn, monkeypatch):
    from db import crud
    from jobs.queue import enqueue_job
    import worker.process as wp

    calls = {"n": 0}

    def counting(spec, max_pages=2):
        calls["n"] += 1
        return {"city": {"city_id": 1}, "count_raw": 1, "count_qualified": 1, "error": None,
                "results": [{"url": "u1", "value": 1.1, "eff_price": 1, "area": 1,
                             "wycena": 1, "src": "OLX"}]}

    monkeypatch.setattr(wp, "run_search", counting)
    spec = {"woj": "x", "miasto": "y", "rooms": [2], "price_min": 0, "price_max": 1,
            "area_min": None, "area_max": None, "year_min": None, "floor": None,
            "required_features": [], "keywords": [], "rynek": "any", "sort": "value"}

    j1 = crud.create_job(db, "ip", spec)
    enqueue_job(j1.id, conn=redis_conn)
    _run_burst(redis_conn)
    j2 = crud.create_job(db, "ip", spec)
    enqueue_job(j2.id, conn=redis_conn)
    _run_burst(redis_conn)

    db.expire_all()
    d2 = crud.get_job(db, j2.id)
    assert d2.status == "done" and d2.from_cache is True
    assert calls["n"] == 1  # second job reused slice, no second scrape
    assert sorted(d2.results, key=lambda r: r.rank)[0].data["url"] == "u1"


def test_process_job_marks_error_on_pipeline_error(db, redis_conn, monkeypatch):
    from db import crud
    from jobs.queue import enqueue_job
    import worker.process as wp
    monkeypatch.setattr(wp, "run_search",
                        lambda spec, max_pages=2: {"error": "city_not_found", "results": [],
                                                   "count_qualified": 0, "city": None})
    spec = {"woj": "nowhere", "miasto": "nowhere", "rooms": [], "price_min": 0,
            "price_max": 1, "area_min": None, "area_max": None, "year_min": None,
            "floor": None, "required_features": [], "keywords": [], "rynek": "any", "sort": "value"}
    job = crud.create_job(db, "ip", spec)
    enqueue_job(job.id, conn=redis_conn)
    _run_burst(redis_conn)
    db.expire_all()
    err = crud.get_job(db, job.id)
    assert err.status == "error" and err.error_msg == "city_not_found"

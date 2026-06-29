import threading

import pytest


@pytest.fixture
def client(db, redis_conn):
    from fastapi.testclient import TestClient
    from web.app import app
    return TestClient(app)


@pytest.mark.e2e
def test_full_journey_submit_process_render(client, db, redis_conn):
    from rq import SimpleWorker, Queue

    # 1. Browser submits the search form.
    r = client.post("/search", data={"woj": "malopolskie", "miasto": "krakow",
                                      "rooms": ["2"], "price_min": "300000",
                                      "price_max": "750000", "rynek": "any"},
                    follow_redirects=False)
    assert r.status_code == 303
    job_id = r.headers["location"].rsplit("/", 1)[1]

    # 2. Status page shows it is still being processed (polling fragment).
    poll = client.get(f"/job/{job_id}/status")
    assert poll.status_code == 200 and "every 2s" in poll.text

    # 3. Real worker drains the queue (real OLX/Otodom/deweloperuch).
    SimpleWorker([Queue("wf", connection=redis_conn)], connection=redis_conn).work(burst=True)

    # 4. Status now renders a terminal page; polling has stopped.
    final = client.get(f"/job/{job_id}/status")
    assert final.status_code == 200
    assert "every 2s" not in final.text

    # 5. The job reached a valid terminal state with a consistent table.
    from db import crud
    db.expire_all()
    job = crud.get_job(db, job_id)
    assert job.status in ("done", "error")
    if job.status == "done":
        assert "Gotowe" in final.text
        for res in job.results:
            assert res.data["value"] > 0 and res.data["eff_price"] > 0
            assert res.data["url"].startswith("http")


@pytest.mark.e2e
def test_concurrent_journeys_all_complete_under_shared_throttle(client, db, redis_conn):
    """Two distinct searches processed by two concurrent real workers; the
    installed throttle keeps outbound polite while both jobs reach a terminal
    state — the throughput-scaling path end to end."""
    from rq import SimpleWorker, Queue
    from rq.timeouts import TimerDeathPenalty
    from db import crud
    from worker.run import setup_throttle
    import pipeline.http as H

    specs = [
        {"woj": "malopolskie", "miasto": "krakow", "rooms": ["2"],
         "price_min": "300000", "price_max": "750000", "rynek": "any"},
        {"woj": "dolnoslaskie", "miasto": "wroclaw", "rooms": ["3"],
         "price_min": "300000", "price_max": "900000", "rynek": "any"},
    ]
    job_ids = []
    for s in specs:
        redis_conn.delete("wf:active:testclient")  # distinct users → distinct IPs
        r = client.post("/search", data=s, follow_redirects=False)
        assert r.status_code == 303
        job_ids.append(r.headers["location"].rsplit("/", 1)[1])

    class _ThreadWorker(SimpleWorker):
        death_penalty_class = TimerDeathPenalty  # SIGALRM is main-thread only

        def _install_signal_handlers(self):
            pass

    setup_throttle(redis_conn)
    try:
        def drain():
            _ThreadWorker([Queue("wf", connection=redis_conn)],
                          connection=redis_conn).work(burst=True)
        workers = [threading.Thread(target=drain) for _ in range(2)]
        for w in workers:
            w.start()
        for w in workers:
            w.join()
    finally:
        H.clear_throttle()

    db.expire_all()
    for jid in job_ids:
        job = crud.get_job(db, jid)
        assert job.status in ("done", "error")
        final = client.get(f"/job/{jid}/status")
        assert final.status_code == 200 and "every 2s" not in final.text


@pytest.mark.e2e
def test_journey_warszawa_district_filters_to_mokotow(client, db, redis_conn):
    from rq import SimpleWorker, Queue
    from db import crud

    r = client.post("/search", data={"woj": "mazowieckie", "miasto": "warszawa",
                                      "rooms": ["2", "3"], "price_min": "0",
                                      "price_max": "5000000", "dzielnica": "Mokotów",
                                      "rynek": "any"}, follow_redirects=False)
    assert r.status_code == 303
    job_id = r.headers["location"].rsplit("/", 1)[1]

    SimpleWorker([Queue("wf", connection=redis_conn)], connection=redis_conn).work(burst=True)

    db.expire_all()
    job = crud.get_job(db, job_id)
    assert job.spec["dzielnica"] == "mokotów"
    assert job.status in ("done", "error")
    if job.status == "done":
        for res in job.results:  # district filter: nothing outside Mokotów
            assert (res.data.get("district") or "").strip().lower() == "mokotów"

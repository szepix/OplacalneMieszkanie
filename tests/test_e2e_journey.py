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

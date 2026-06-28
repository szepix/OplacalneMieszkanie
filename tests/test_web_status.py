import pytest
from datetime import datetime, timezone


@pytest.fixture
def client(db, redis_conn):
    from fastapi.testclient import TestClient
    from web.app import app
    return TestClient(app)


def test_job_page_404_for_unknown(client):
    assert client.get("/job/deadbeef").status_code == 404


def test_status_fragment_polls_while_processing(client, db):
    from db import crud
    job = crud.create_job(db, "1.1.1.1", {"woj": "x", "miasto": "y", "rooms": []})
    r = client.get(f"/job/{job.id}/status")
    assert r.status_code == 200
    assert "every 2s" in r.text  # fragment re-arms HTMX polling


def test_status_fragment_renders_results_when_done(client, db):
    from db import crud
    job = crud.create_job(db, "1.1.1.1", {"woj": "x", "miasto": "y", "rooms": []})
    crud.add_results(db, job.id, [{"url": "https://olx/x", "value": 1.42,
                                   "eff_price": 500000, "area": 52.0, "wycena": 710000,
                                   "wycena_med": 700000, "src": "OLX", "district": "Centrum",
                                   "reliable": False, "suspect": True}])
    crud.set_status(db, job.id, "done", count_qualified=1,
                    finished_at=datetime.now(timezone.utc))
    r = client.get(f"/job/{job.id}/status")
    assert r.status_code == 200
    assert "1.42" in r.text and "https://olx/x" in r.text
    assert "every 2s" not in r.text  # polling stops when done


def test_status_fragment_shows_error(client, db):
    from db import crud
    job = crud.create_job(db, "1.1.1.1", {"woj": "x", "miasto": "y", "rooms": []})
    crud.set_status(db, job.id, "error", error_msg="city_not_found",
                    finished_at=datetime.now(timezone.utc))
    r = client.get(f"/job/{job.id}/status")
    assert "city_not_found" in r.text and "every 2s" not in r.text

import pytest


@pytest.fixture
def client(db, redis_conn):
    from fastapi.testclient import TestClient
    from web.app import app
    return TestClient(app)


def test_get_index_renders_form(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'name="woj"' in r.text
    assert 'id="city-slot"' in r.text  # miasto combo loads here via /geo/cities


def test_submit_creates_queued_job_and_redirects(client, db):
    from db import crud
    r = client.post("/search", data={"woj": "malopolskie", "miasto": "krakow",
                                      "rooms": ["2", "3"], "price_min": "0",
                                      "price_max": "1200000", "rynek": "any"},
                    follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert loc.startswith("/job/")
    job_id = loc.rsplit("/", 1)[1]
    db.expire_all()
    job = crud.get_job(db, job_id)
    assert job.status == "queued"
    assert job.spec["rooms"] == [2, 3] and job.spec["miasto"] == "krakow"


def test_second_submit_same_ip_is_rate_limited(client):
    data = {"woj": "malopolskie", "miasto": "krakow", "rooms": ["2"], "rynek": "any"}
    first = client.post("/search", data=data, follow_redirects=False)
    assert first.status_code == 303
    second = client.post("/search", data=data, follow_redirects=False)
    assert second.status_code == 429
    assert "5 min" in second.text


def test_submit_stores_dzielnica(client, db):
    from db import crud
    r = client.post("/search", data={"woj": "mazowieckie", "miasto": "warszawa",
                                      "rooms": ["2"], "dzielnica": "Mokotów",
                                      "rynek": "any"}, follow_redirects=False)
    assert r.status_code == 303
    job_id = r.headers["location"].rsplit("/", 1)[1]
    db.expire_all()
    job = crud.get_job(db, job_id)
    assert job.spec["dzielnica"] == "mokotów"


def test_invalid_feature_returns_400(client):
    r = client.post("/search", data={"woj": "malopolskie", "miasto": "krakow",
                                     "rooms": ["2"], "features": ["teleporter"],
                                     "rynek": "any"}, follow_redirects=False)
    assert r.status_code == 400


def test_geo_cities_returns_city_combo(client):
    r = client.get("/geo/cities", params={"woj": "mazowieckie"})
    assert r.status_code == 200
    assert "Warszawa" in r.text
    assert 'name="miasto"' in r.text


def test_geo_districts_warszawa_has_mokotow(client):
    r = client.get("/geo/districts", params={"woj": "mazowieckie", "miasto": "warszawa"})
    assert r.status_code == 200
    assert "Mokotów" in r.text
    assert 'name="dzielnica"' in r.text


def test_geo_districts_city_without_districts_is_empty(client):
    r = client.get("/geo/districts", params={"woj": "mazowieckie", "miasto": "radom"})
    assert r.status_code == 200
    assert 'name="dzielnica"' not in r.text


def test_index_has_woj_combo_with_regions(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Mazowieckie" in r.text and "Małopolskie" in r.text

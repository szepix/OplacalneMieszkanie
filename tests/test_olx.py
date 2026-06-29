from pipeline.sources import olx
from pipeline.spec import SearchSpec


def test_fetch_olx_warszawa_3pok():
    spec = SearchSpec(woj="mazowieckie", miasto="warszawa", rooms=[3],
                      price_min=600000, price_max=1500000).normalized()
    rows = olx.fetch_olx(spec, city_id=17871, max_pages=1)
    assert rows, "no OLX rows fetched"
    r = rows[0]
    assert r["src"] == "OLX" and r["price"] > 0 and r["area"] >= 0


def test_fetch_olx_district_filter_mokotow():
    spec = SearchSpec(woj="mazowieckie", miasto="warszawa", rooms=[2, 3],
                      price_min=0, price_max=5_000_000).normalized()
    rows = olx.fetch_olx(spec, city_id=17871, district_id=353, max_pages=1)
    assert rows, "no OLX rows for Mokotów"
    assert all(r["district"] == "Mokotów" for r in rows)

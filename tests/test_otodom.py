from pipeline.sources import otodom
from pipeline.spec import SearchSpec

def test_oto_search_url_builds():
    spec = SearchSpec(woj="malopolskie", miasto="krakow", rooms=[3]).normalized()
    url = otodom.oto_search_url(spec, "malopolskie", "krakow")
    assert "malopolskie" in url and "krakow" in url
    assert url.startswith("https://www.otodom.pl/")

def test_fetch_otodom_krakow_small():
    spec = SearchSpec(woj="malopolskie", miasto="krakow", rooms=[3],
                      price_min=500000, price_max=1500000).normalized()
    rows = otodom.fetch_otodom(spec, "malopolskie", "krakow", max_pages=1)
    # Otodom may rate-limit; allow empty but require correct shape when present
    for r in rows[:1]:
        assert r["src"] == "Otodom" and "price" in r

from pipeline import valuation
from pipeline.spec import SearchSpec

def test_wycena_krakow_real():
    w = valuation.wycena(50.0617, 19.9373, 60)
    assert w and w["value"] > 0
    assert w["median"] > 0

def test_value_of_uses_offer_coords():
    spec = SearchSpec(woj="malopolskie", miasto="krakow", rooms=[3]).normalized()
    r = {"src": "Otodom", "area": 60.0, "eff_price": 1_000_000,
         "coords": (50.0617, 19.9373), "map": {}, "street": None, "year": 2018}
    out = valuation.value_of(r, spec)
    assert out and out["wycena"] > 0
    assert out["geo_src"] == "oferta"
    assert 0 < out["value"] < 5
    assert out["reliable"] is False
    assert out["suspect"] is True

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


def _seed(lat, lng, area, **w):
    key = f"{round(lat,5)},{round(lng,5)},{int(area)}"
    valuation.cache_set(key, w)


def _row(lat, lng, area, eff_price):
    return {"src": "OLX", "area": float(area), "eff_price": eff_price,
            "coords": (lat, lng), "map": {}, "street": None}


def _spec():
    return SearchSpec(woj="mazowieckie", miasto="warszawa", rooms=[]).normalized()


def test_value_of_clean_listing_is_reliable():
    _seed(52.10, 21.10, 60, value=600_000, ppsqm=10_000, median=10_000,
          count=10, radius="budynek", reliable=True, r2=0.9)
    out = valuation.value_of(_row(52.10, 21.10, 60, 600_000), _spec())
    assert out["suspect"] is False
    assert out["reliable"] is True


def test_value_of_too_good_to_be_true_is_suspect():
    _seed(52.11, 21.11, 60, value=1_200_000, ppsqm=10_000, median=10_000,
          count=10, radius="budynek", reliable=True, r2=0.9)
    out = valuation.value_of(_row(52.11, 21.11, 60, 600_000), _spec())
    assert out["suspect"] is True
    assert out["reliable"] is False


def test_value_of_thin_comps_is_suspect():
    _seed(52.12, 21.12, 60, value=600_000, ppsqm=10_000, median=10_000,
          count=3, radius="budynek", reliable=True, r2=0.9)
    out = valuation.value_of(_row(52.12, 21.12, 60, 600_000), _spec())
    assert out["suspect"] is True
    assert out["reliable"] is False


def test_value_of_coarse_radius_is_suspect():
    _seed(52.13, 21.13, 60, value=600_000, ppsqm=10_000, median=10_000,
          count=10, radius="miasto", reliable=True, r2=0.9)
    out = valuation.value_of(_row(52.13, 21.13, 60, 600_000), _spec())
    assert out["suspect"] is True
    assert out["reliable"] is False

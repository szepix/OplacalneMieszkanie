from pipeline import geo

def test_resolve_warszawa():
    c = geo.resolve_city("Mazowieckie", "Warszawa")
    assert c and c["city_id"] == 17871
    assert c["region_id"] == 2

def test_resolve_krakow():
    c = geo.resolve_city("Małopolskie", "Kraków")
    assert c and c["city_id"] > 0
    assert 49.9 < c["lat"] < 50.2

def test_resolve_unknown_city():
    assert geo.resolve_city("Mazowieckie", "Nieistniejewo123") is None

def test_nearest_metro_centrum():
    name, line, m = geo.nearest_metro(52.2310, 21.0102)
    assert name == "Centrum"
    assert m < 200
    assert line in ("M1", "M1/M2")

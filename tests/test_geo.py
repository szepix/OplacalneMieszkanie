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

def test_list_regions_has_16_wojewodztwa():
    regs = geo.list_regions()
    assert len(regs) == 16
    assert "Mazowieckie" in regs
    assert "Małopolskie" in regs

def test_cities_for_region_warszawa():
    cities = geo.cities_for_region("Mazowieckie")
    assert "Warszawa" in cities
    assert cities == sorted(cities)

def test_cities_for_region_unknown():
    assert geo.cities_for_region("Nieistniejewo123") == []

def test_districts_for_city_warszawa():
    d = geo.districts_for_city(17871)
    names = [x["name"] for x in d]
    assert "Mokotów" in names
    assert any(x["id"] == 353 and x["name"] == "Mokotów" for x in d)

def test_resolve_district_mokotow():
    assert geo.resolve_district(17871, "Mokotów") == 353
    assert geo.resolve_district(17871, "mokotow") == 353

def test_resolve_district_unknown():
    assert geo.resolve_district(17871, "Nieistnieje") is None

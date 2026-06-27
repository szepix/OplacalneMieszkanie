from pipeline.features import enrich, qualifies, keywords_match
from pipeline.spec import SearchSpec

def _row(text, price=900000, area=70, rooms="3", market="wtorny", floor=0):
    return {"src": "OLX", "id": "x", "url": "", "title": "", "text": text,
            "price": price, "area": area, "rooms": rooms, "district": "",
            "market": market, "floor": floor, "year": None, "coords": None, "map": {}}

def test_keywords_and():
    assert keywords_match("ładne mieszkanie z klimatyzacją i windą", ["klimatyzacja", "winda"])
    assert not keywords_match("ładne mieszkanie z windą", ["klimatyzacja", "winda"])

def test_enrich_detects_features():
    r = enrich(_row("Mieszkanie z ogródkiem, miejsce postojowe w garażu, klimatyzacja, komórka lokatorska", floor=0))
    assert r["garden"] and r["parking"] and r["aircon"] and r["komorka"]

def test_qualifies_required_features():
    spec = SearchSpec(woj="x", miasto="y", rooms=[3], price_min=500000, price_max=2000000,
                      required_features=["ogrod", "parking"]).normalized()
    ok = enrich(_row("3 pokoje, ogródek na parterze, miejsce parkingowe, klimatyzacja", rooms="3", floor=0))
    assert qualifies(ok, spec)
    no_park = enrich(_row("3 pokoje, ogródek na parterze, klimatyzacja", rooms="3", floor=0))
    assert not qualifies(no_park, spec)

def test_qualifies_rooms_and_price():
    spec = SearchSpec(woj="x", miasto="y", rooms=[2], price_min=500000, price_max=800000).normalized()
    r = enrich(_row("2 pokoje", rooms="3", price=900000))
    assert not qualifies(r, spec)  # wrong rooms + over price

def test_qualifies_keywords():
    spec = SearchSpec(woj="x", miasto="y", rooms=[3], keywords=["winda"]).normalized()
    has = enrich(_row("3 pokoje, jest winda w bloku", rooms="3"))
    hasnt = enrich(_row("3 pokoje, bez wzmianki", rooms="3"))
    assert qualifies(has, spec) and not qualifies(hasnt, spec)

def test_olx_4plus_bucket_excludes_5pok_when_4_requested():
    spec = SearchSpec(woj="x", miasto="y", rooms=[4]).normalized()
    r = enrich(_row("Przestronne 5 pokoi z widokiem", rooms="4 i więcej"))
    assert not qualifies(r, spec)  # actually 5 rooms, not 4

def test_olx_4plus_bucket_matches_5_when_5_requested():
    spec = SearchSpec(woj="x", miasto="y", rooms=[5]).normalized()
    r = enrich(_row("Przestronne 5 pokoi z widokiem", rooms="4 i więcej"))
    assert qualifies(r, spec)

def test_olx_4plus_bucket_keeps_genuine_4():
    spec = SearchSpec(woj="x", miasto="y", rooms=[4]).normalized()
    r = enrich(_row("Komfortowe 4-pokojowe mieszkanie", rooms="4 i więcej"))
    assert qualifies(r, spec)

def test_otodom_four_is_exact():
    r = {"src":"Otodom","text":"4 pokoje","price":900000,"area":70,"rooms":"FOUR",
         "district":"","market":"wtorny","floor":0,"year":None,"coords":None,"map":{}}
    r = enrich(r)
    assert qualifies(r, SearchSpec(woj="x",miasto="y",rooms=[4]).normalized())
    assert not qualifies(r, SearchSpec(woj="x",miasto="y",rooms=[5]).normalized())

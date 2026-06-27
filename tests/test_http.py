from pipeline import http

def test_olx_json_real():
    d = http._json(http.OLX_API + "?category_id=14&city_id=17871&limit=1")
    assert isinstance(d, dict)
    assert "data" in d

def test_strip_html():
    out = http.strip_html("<b>Hej</b>&nbsp;tam")
    assert "<" not in out and ">" not in out
    assert "Hej" in out and "tam" in out
    assert "\xa0" not in out  # &nbsp; normalized to space

def test_walk_finds_typename():
    sample = {"a": {"__typename": "Foo", "x": 1}, "b": [{"__typename": "Foo", "x": 2}]}
    found = list(http.walk(sample, "Foo"))
    assert len(found) == 2

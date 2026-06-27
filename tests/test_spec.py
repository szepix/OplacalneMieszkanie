import pytest
from pipeline.spec import SearchSpec, FEATURE_KEYS

def test_defaults_and_normalize():
    s = SearchSpec(woj="Mazowieckie", miasto="  Warszawa ", rooms=[4],
                   required_features=["Ogrod"], keywords=["Klimatyzacja", "winda"]).normalized()
    assert s.woj == "mazowieckie"
    assert s.miasto == "warszawa"
    assert s.required_features == ["ogrod"]
    assert s.keywords == ["klimatyzacja", "winda"]
    assert s.rynek == "any"

def test_invalid_feature_rejected():
    with pytest.raises(ValueError):
        SearchSpec(woj="x", miasto="y", rooms=[], required_features=["taras"]).normalized()

def test_invalid_rynek_rejected():
    with pytest.raises(ValueError):
        SearchSpec(woj="x", miasto="y", rooms=[], rynek="nowe").normalized()

def test_feature_keys():
    assert FEATURE_KEYS == ("ogrod", "parking", "klimatyzacja", "komorka")

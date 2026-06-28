def test_pipeline_default_cache_unchanged():
    from pipeline import valuation
    valuation.WYC.clear()
    valuation.cache_set("k1", {"value": 100})
    assert valuation.cache_get("k1") == {"value": 100}
    assert valuation.cache_get("missing") is valuation._MISS


def test_db_cache_stores_reads_and_expires(db):
    from datetime import datetime, timezone, timedelta
    from pipeline import valuation
    from db import cache
    from db.models import ValuationCache
    cache.db_valuation_set("50.0,19.9,60", {"value": 123, "median": 21000})
    assert cache.db_valuation_get("50.0,19.9,60") == {"value": 123, "median": 21000}
    assert cache.db_valuation_get("absent") is valuation._MISS
    row = db.get(ValuationCache, "50.0,19.9,60")
    row.ts = datetime.now(timezone.utc) - timedelta(hours=48)
    db.commit()
    assert cache.db_valuation_get("50.0,19.9,60") is valuation._MISS  # 24h TTL expired


def test_db_cache_stores_negative_result(db):
    from pipeline import valuation
    from db import cache
    cache.db_valuation_set("neg,key,1", None)
    assert cache.db_valuation_get("neg,key,1") is None  # cached miss != not-cached


def test_install_swaps_pipeline_hooks(db):
    from pipeline import valuation
    from db import cache
    try:
        cache.install_db_valuation_cache()
        valuation.cache_set("99.9,99.9,50", {"value": 777})
        assert valuation.cache_get("99.9,99.9,50") == {"value": 777}
    finally:
        cache.uninstall_db_valuation_cache()
    assert valuation.cache_get is valuation._default_get

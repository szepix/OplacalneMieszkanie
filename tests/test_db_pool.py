def test_engine_pool_sized_from_config():
    from db.session import engine
    from config import DB_POOL_SIZE, DB_MAX_OVERFLOW
    assert engine.pool.size() == DB_POOL_SIZE
    assert engine.pool._max_overflow == DB_MAX_OVERFLOW

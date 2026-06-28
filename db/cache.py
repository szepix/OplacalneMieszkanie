from datetime import datetime, timezone, timedelta
from sqlalchemy.dialects.postgresql import insert
from db.session import SessionLocal
from db.models import ValuationCache
from config import VALUATION_TTL_SECONDS
from pipeline import valuation


def db_valuation_get(key):
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=VALUATION_TTL_SECONDS)
    with SessionLocal() as s:
        row = s.get(ValuationCache, key)
        if row is None or row.ts < cutoff:
            return valuation._MISS
        return row.data


def db_valuation_set(key, value) -> None:
    now = datetime.now(timezone.utc)
    stmt = insert(ValuationCache).values(key=key, data=value, ts=now)
    stmt = stmt.on_conflict_do_update(
        index_elements=[ValuationCache.key], set_={"data": value, "ts": now})
    with SessionLocal() as s:
        s.execute(stmt)
        s.commit()


def install_db_valuation_cache() -> None:
    valuation.cache_get = db_valuation_get
    valuation.cache_set = db_valuation_set


def uninstall_db_valuation_cache() -> None:
    valuation.cache_get = valuation._default_get
    valuation.cache_set = valuation._default_set

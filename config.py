import os


def normalize_db_url(url: str) -> str:
    """Managed hosts (Render/Heroku) hand out driverless postgres URLs;
    pin them to psycopg v3, which is what we install."""
    for scheme in ("postgresql://", "postgres://"):
        if url.startswith(scheme):
            return "postgresql+psycopg://" + url[len(scheme):]
    return url


DATABASE_URL = normalize_db_url(
    os.environ.get("DATABASE_URL", "postgresql+psycopg://wf:wf@localhost:5432/wf"))
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SLICE_TTL_SECONDS = int(os.environ.get("SLICE_TTL_SECONDS", 6 * 3600))
VALUATION_TTL_SECONDS = int(os.environ.get("VALUATION_TTL_SECONDS", 24 * 3600))
RATE_ACTIVE_TTL = int(os.environ.get("RATE_ACTIVE_TTL", 300))
RATE_DAILY_LIMIT = int(os.environ.get("RATE_DAILY_LIMIT", 20))
MAX_PAGES = int(os.environ.get("MAX_PAGES", 2))

# Outbound politeness — req/sec per target domain, shared across all workers.
# Nominatim's usage policy is a hard 1 req/s; do not raise it without a mirror.
OLX_RATE = float(os.environ.get("OLX_RATE", 2.0))
OTODOM_RATE = float(os.environ.get("OTODOM_RATE", 1.0))
NOMINATIM_RATE = float(os.environ.get("NOMINATIM_RATE", 1.0))
DEWELOPERUCH_RATE = float(os.environ.get("DEWELOPERUCH_RATE", 2.0))
THROTTLE_BURST = float(os.environ.get("THROTTLE_BURST", 3.0))
THROTTLE_MAX_WAIT = float(os.environ.get("THROTTLE_MAX_WAIT", 30.0))

# Per-job fetch fan-out (OLX ‖ Otodom + pages). Outbound rate stays capped by
# the throttle regardless of this; it only bounds in-process fetch threads.
FETCH_CONCURRENCY = int(os.environ.get("FETCH_CONCURRENCY", 4))

# Web process count (consumed by the uvicorn launch command, not Python).
WEB_WORKERS = int(os.environ.get("WEB_WORKERS", 2))

# SQLAlchemy pool sized to total web + RQ-worker concurrency.
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", 10))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", 20))

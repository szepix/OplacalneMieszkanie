import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://wf:wf@localhost:5432/wf")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SLICE_TTL_SECONDS = int(os.environ.get("SLICE_TTL_SECONDS", 6 * 3600))
VALUATION_TTL_SECONDS = int(os.environ.get("VALUATION_TTL_SECONDS", 24 * 3600))
RATE_ACTIVE_TTL = int(os.environ.get("RATE_ACTIVE_TTL", 300))
RATE_DAILY_LIMIT = int(os.environ.get("RATE_DAILY_LIMIT", 20))
MAX_PAGES = int(os.environ.get("MAX_PAGES", 2))

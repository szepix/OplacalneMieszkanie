import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://wf:wf@localhost:5432/wf_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")


def _ensure_test_db():
    import psycopg
    from urllib.parse import urlparse
    u = urlparse(os.environ["DATABASE_URL"].replace("+psycopg", ""))
    dbname = u.path.lstrip("/")
    admin = f"postgresql://{u.username}:{u.password}@{u.hostname}:{u.port}/postgres"
    conn = psycopg.connect(admin, autocommit=True)
    try:
        row = conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,)).fetchone()
        if not row:
            conn.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        conn.close()


_ensure_test_db()

import pytest


@pytest.fixture
def db():
    from db.session import Base, engine, SessionLocal
    import db.models  # noqa: F401
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def redis_conn():
    import redis
    from config import REDIS_URL
    c = redis.Redis.from_url(REDIS_URL)
    c.flushdb()
    try:
        yield c
    finally:
        c.flushdb()

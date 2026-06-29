from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config import DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       pool_size=DB_POOL_SIZE, max_overflow=DB_MAX_OVERFLOW)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    import db.models  # noqa: F401  register mappers
    Base.metadata.create_all(engine)

def test_init_db_creates_tables_on_real_postgres(db):
    from sqlalchemy import text
    rows = db.execute(text(
        "select tablename from pg_tables where schemaname='public'"
    )).fetchall()
    names = {r[0] for r in rows}
    assert {"jobs", "job_results", "valuations_cache"} <= names

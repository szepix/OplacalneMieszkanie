def test_normalize_db_url_adds_psycopg_driver():
    from config import normalize_db_url
    # Render/Heroku hand out driverless schemes; app needs +psycopg (psycopg v3)
    assert normalize_db_url("postgres://u:p@h:5432/d") == "postgresql+psycopg://u:p@h:5432/d"
    assert normalize_db_url("postgresql://u:p@h/d") == "postgresql+psycopg://u:p@h/d"


def test_normalize_db_url_leaves_explicit_driver_and_others():
    from config import normalize_db_url
    assert normalize_db_url("postgresql+psycopg://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
    assert normalize_db_url("sqlite:///x.db") == "sqlite:///x.db"

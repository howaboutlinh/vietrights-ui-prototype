from app import create_app
from services.config import sqlalchemy_database_url


def test_database_url_selects_psycopg_driver():
    assert sqlalchemy_database_url("postgresql://user:pass@pooler.example/postgres") == (
        "postgresql+psycopg://user:pass@pooler.example/postgres"
    )


def test_app_factory_uses_small_resilient_pool(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler.example/postgres")
    monkeypatch.setenv("SUPABASE_URL", "ignored")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "ignored")
    flask_app = create_app()
    options = flask_app.config["SQLALCHEMY_ENGINE_OPTIONS"]
    assert flask_app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql+psycopg://")
    assert options["pool_pre_ping"] is True
    assert options["pool_recycle"] == 300
    assert options["pool_size"] == 3
    assert options["max_overflow"] == 2


def test_app_factory_starts_without_database_configuration(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    flask_app = create_app()
    assert "SQLALCHEMY_DATABASE_URI" not in flask_app.config
    assert flask_app.test_client().get("/").status_code == 200

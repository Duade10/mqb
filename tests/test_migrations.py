import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def _make_config() -> Config:
    cfg = Config(str(Path("alembic.ini")))
    cfg.set_main_option("script_location", "alembic")
    cfg.attributes["configure_logger"] = False
    return cfg


def test_migrations_sqlite(tmp_path):
    db_path = tmp_path / "migration.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    cfg = _make_config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")


def test_migrations_postgres_offline():
    os.environ["DATABASE_URL"] = "postgresql+psycopg://user:pass@localhost:5432/db"
    cfg = _make_config()
    command.upgrade(cfg, "head", sql=True)
    command.downgrade(cfg, "base", sql=True)

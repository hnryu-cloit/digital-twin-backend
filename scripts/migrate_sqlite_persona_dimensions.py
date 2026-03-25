"""
Add/backfill persona dimension columns in the local SQLite DB.

Run:
  python scripts/migrate_sqlite_persona_dimensions.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.db_migrations import ensure_sqlite_persona_dimensions


def main() -> None:
    database_url = settings.DATABASE_URL
    if not database_url.startswith("sqlite"):
        raise SystemExit(f"SQLite only migration script. Current DATABASE_URL={database_url}")

    sqlite_path = database_url.replace("sqlite+aiosqlite:///", "", 1).replace("sqlite:///", "", 1)
    changed = ensure_sqlite_persona_dimensions(sqlite_path)
    print(f"persona dimension migration complete: {sqlite_path} changed={changed}")


if __name__ == "__main__":
    main()

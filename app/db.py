from __future__ import annotations
from psycopg_pool import ConnectionPool
from app.config import settings

if not settings.database_url:
    raise RuntimeError("DATABASE_URL not set. Example: postgresql://user:pass@host:5432/dbname")

pool = ConnectionPool(conninfo=settings.database_url, min_size=1, max_size=5, num_workers=1)

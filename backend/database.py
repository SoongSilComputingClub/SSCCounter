import os

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

_db_pool: ConnectionPool | None = None


def open_database_pool() -> None:
    """애플리케이션 시작 시 PostgreSQL connection pool을 생성합니다."""
    global _db_pool

    if _db_pool is not None:
        return

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    _db_pool = ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=10,
        open=True,
    )


def close_database_pool() -> None:
    """애플리케이션 종료 시 PostgreSQL connection pool을 닫습니다."""
    global _db_pool

    if _db_pool is None:
        return

    _db_pool.close()
    _db_pool = None


def get_db_connection():
    """생성된 connection pool에서 DB connection을 반환합니다."""
    if _db_pool is None:
        raise RuntimeError("Database connection pool is not initialized")

    return _db_pool.connection()

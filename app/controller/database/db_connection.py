import os
from contextlib import contextmanager
import psycopg2
import psycopg2.pool

class DBConnection:
    __pool = None

    @staticmethod
    def init_pool():
        DBConnection.__pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=15,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            database=os.getenv("POSTGRES_DB", "postgres"),
            connect_timeout=5 
        )

        print(
            f"PostgreSQL pool initialized "
            f"({os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')})"
        )

    @staticmethod
    @contextmanager
    def get_conn():
        if DBConnection.__pool is None:
            DBConnection.init_pool()

        conn = DBConnection.__pool.getconn()
        try:
            yield conn
        finally:
            DBConnection.__pool.putconn(conn)
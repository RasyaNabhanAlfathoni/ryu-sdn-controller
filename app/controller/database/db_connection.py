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
            host="localhost",
            port="5432",
            user="admin",
            password="admin",
            database="sdn_controller",
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

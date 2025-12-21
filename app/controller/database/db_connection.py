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
            host="127.0.0.1",
            port=5432,
            user="admin",
            password="admin",
            database="sdn_controller"
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
from contextlib import contextmanager
from mysql.connector import pooling

class DBConnection:
    __pool = None

    @staticmethod
    def init_pool():
        DBConnection.__pool = pooling.MySQLConnectionPool(
            pool_name="sdn_pool",
            pool_size=15,
            host="127.0.0.1",
            user="admin",
            password="admin",
            database="sdn_controller",
            pool_reset_session=True
        )

    @staticmethod
    @contextmanager
    def get_conn():
        if DBConnection.__pool is None:
            DBConnection.init_pool()

        conn = DBConnection.__pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()